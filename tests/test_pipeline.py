import csv
import json
from pathlib import Path
import tempfile
import unittest

from spreadsheet_automation.config import load_config
from spreadsheet_automation.ingest import discover_files, read_rows
from spreadsheet_automation.normalize import map_headers, parse_date, parse_decimal
from spreadsheet_automation.pipeline import process
from spreadsheet_automation.report import summarize, write_outputs


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "schema.json"
SAMPLES = ROOT / "sample_data"


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.config = load_config(CONFIG)

    def test_demo_matches_expected_rows_reasons_and_counts(self):
        result = process(SAMPLES, self.config)
        expected = json.loads((SAMPLES / "expected.json").read_text(encoding="utf-8"))
        self.assertEqual(result["counts"], {key: expected[key] for key in ("input", "accepted", "rejected", "duplicates", "output")})
        self.assertEqual(sorted(row["record_id"] for row in result["accepted"]), sorted(expected["accepted_ids"]))
        reasons = {f"{row['source_file']}:{row['source_row']}": row["reason_codes"].split(";") for row in result["rejected"]}
        self.assertEqual(reasons, expected["exception_reasons"])
        self.assertEqual(sum(source["rows"] for source in result["sources"]), 360)
        self.assertEqual(len(result["sources"]), 2)

    def test_report_segments_reconcile_to_accepted_amount(self):
        result = process(SAMPLES, self.config)
        summary = summarize(result)
        self.assertEqual(len(summary["months"]), 6)
        self.assertEqual(len(summary["categories"]), 3)
        self.assertEqual(len(summary["subcategories"]), 9)
        self.assertEqual(len(summary["channels"]), 3)
        self.assertEqual(len(summary["regions"]), 4)
        for key in ("months", "categories", "subcategories", "channels", "regions", "customers"):
            self.assertEqual(sum(item["rows"] for item in summary[key].values()), result["counts"]["accepted"])
            self.assertEqual(sum(item["amount"] for item in summary[key].values()), summary["accepted_amount"])
        self.assertEqual(sum(summary["reasons"].values()), result["counts"]["rejected"])

    def test_repeat_run_is_deterministic(self):
        result = process(SAMPLES, self.config)
        with tempfile.TemporaryDirectory() as temp:
            first, second = Path(temp) / "first", Path(temp) / "second"
            files = discover_files(SAMPLES)
            write_outputs(first, result, self.config, CONFIG, files)
            write_outputs(second, process(SAMPLES, self.config), self.config, CONFIG, files)
            for name in ("clean.csv", "exceptions.csv", "manifest.json", "report.html"):
                self.assertEqual((first / name).read_bytes(), (second / name).read_bytes())
            with (first / "clean.csv").open(newline="", encoding="utf-8") as stream:
                rows = list(csv.DictReader(stream))
            self.assertTrue(all(row["source_file"] and row["source_row"] for row in rows))
            report = (first / "report.html").read_text(encoding="utf-8")
            for heading in ("Monthly accepted amount", "Categories", "Subcategories", "Sales channels", "Regions", "Top 10 synthetic customers", "Review reasons"):
                self.assertIn(heading, report)

    def test_normalization_boundaries(self):
        self.assertEqual(parse_date("09/14/2026", self.config["date_formats"]), "2026-09-14")
        self.assertIsNone(parse_date("03/04/2026", self.config["date_formats"]))
        self.assertEqual(parse_decimal("1.234,56"), "1234.56")
        self.assertEqual(parse_decimal("1,234.56"), "1234.56")
        self.assertIsNone(parse_decimal("1,234"))
        self.assertIsNone(parse_decimal("sem valor"))

    def test_bad_sources_and_ambiguous_headers_fail_clearly(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            unsupported = root / "readme.txt"
            unsupported.write_text("text", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Unsupported input file"):
                discover_files(unsupported)
            broken = root / "broken.xlsx"
            broken.write_text("not a workbook", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Cannot read broken.xlsx"):
                list(read_rows(broken))
        with self.assertRaisesRegex(ValueError, "Two columns map"):
            map_headers(["Customer", "Cliente"], self.config)

    def test_invalid_first_occurrence_does_not_claim_duplicate_key(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "orders.csv"
            path.write_text("Order ID,Order Date,Customer,Total,Type,Subcategory,Channel,Region\nX-1,03/04/2026,First,10.00,service,support,direct,north\nX-1,2026-09-01,Second,10.00,service,support,direct,north\n", encoding="utf-8")
            result = process(path, self.config)
            self.assertEqual(result["counts"], {"input": 2, "accepted": 1, "rejected": 1, "duplicates": 0, "output": 1})
            self.assertEqual(result["accepted"][0]["source_row"], 3)

    def test_category_subcategory_pair_is_validated(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "orders.csv"
            path.write_text("Order ID,Order Date,Customer,Total,Type,Subcategory,Channel,Region\nX-1,2026-09-01,First,10.00,hardware,support,direct,north\n", encoding="utf-8")
            result = process(path, self.config)
            self.assertEqual(result["rejected"][0]["reason_codes"], "CATEGORY_SUBCATEGORY_MISMATCH")

    def test_csv_export_escapes_spreadsheet_formula_text(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "orders.csv"
            source.write_text("Order ID,Order Date,Customer,Total,Type,Subcategory,Channel,Region\nX-1,2026-09-01,=HYPERLINK(\"https://example.test\"),10.00,service,support,direct,north\n", encoding="utf-8")
            result = process(source, self.config)
            self.assertEqual(result["counts"]["accepted"], 1)
            output = root / "output"
            write_outputs(output, result, self.config, CONFIG, [source])
            with (output / "clean.csv").open(newline="", encoding="utf-8") as stream:
                exported = next(csv.DictReader(stream))
            self.assertTrue(exported["customer_name"].startswith("'="))


if __name__ == "__main__":
    unittest.main()
