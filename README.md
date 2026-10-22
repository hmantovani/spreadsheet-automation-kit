# Spreadsheet Cleanup & Reporting Automation Kit

A small Python command-line tool that turns recurring CSV and Excel exports into clean data, a review queue, and a reconciliation report. The included sales records are synthetic and exist solely to demonstrate the workflow.

## Set up and run

Use Python 3.10 or later. From this project root:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -e .
.venv\Scripts\spreadsheet-kit --input sample_data --config config/schema.json --output outputs/demo
```

The output folder must be new or empty. For another run, choose another folder, such as `outputs/demo-2`. The input can be one `.csv` or `.xlsx` file or a folder containing both formats. The first worksheet of each Excel file is read. Other file types in an input folder are ignored; passing one directly returns an error.

Run the tests with:

```powershell
.venv\Scripts\python -m unittest discover -s tests -v
```

## Output files

- `clean.csv`: validated canonical rows with source coordinates.
- `exceptions.csv`: rows requiring review, with reason codes and explanations.
- `manifest.json`: source row counts, file and configuration hashes, reconciliation totals, and duplicate policy.
- `report.html`: a self-contained report with a monthly amount chart, category and subcategory tables, channel and region breakdowns, top synthetic customers, exception reasons, and links to the other artifacts.

The files are deterministic for the same input bytes and configuration. The tool will not overwrite a populated output directory. It does not mutate source files.

## Configure for a recurring export

Edit `config/schema.json` to change fields, aliases, required flags, allowed values, category and subcategory pairs, minimum values, date formats, null tokens, or reason messages. See `docs/DATA_CONTRACT.md` for parsing rules and the duplicate policy. Changing a schema field requires a matching aliases entry. Include a nonempty duplicate key. Keep canonical field names stable when comparing runs.

## Demo walkthrough

1. Open `sample_data/english_orders.csv` and `sample_data/portuguese_orders.xlsx`. Their headers, date formats, and amount formats differ. Both files cover January through June 2026 and include three categories, nine subcategories, three channels, four regions, and 30 fictional customers.
2. Run the command above. The 360 source rows become 348 accepted and 12 rejected rows. One rejected row is a duplicate. The manifest confirms `360 = 348 + 12` and `output = 348`.
3. Open `outputs/demo/report.html`. The chart and tables show how accepted amount varies by month and segment. The review table points to the source file and row of every exception. Examples include an ambiguous date, missing fields, invalid values, a category and subcategory mismatch, and a duplicate ID.
4. Correct the source, then run into a fresh output folder. Compare the new manifest and exceptions to see the effect. A human decides the right correction; the tool does not guess it.

The amount is in synthetic units; no currency or business impact is claimed. The report totals use accepted rows only. Rejected rows remain in `exceptions.csv` for correction and are excluded from segment totals.

## Reproduce the sample inputs

The checked-in samples are deterministic. `scripts/generate_demo_workbook.mjs` regenerates the CSV, Excel workbook, and expected outcome file from fixed rules and anomaly locations. Regeneration requires the Codex spreadsheet authoring runtime through `ARTIFACT_TOOL_URL`; the Python CLI and tests need only the checked-in inputs and public Python dependencies. See `sample_data/README.md` for the generation rules and exception matrix.

## Data and scope

This repository contains only synthetic demo data. No credentials or customer data are required to run it. The checked-in workbook and CSV are sufficient; the maintainer-only fixture generator is optional.
