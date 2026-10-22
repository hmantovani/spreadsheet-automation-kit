"""Deterministic CSV, JSON, and self-contained HTML run artifacts."""

from collections import Counter, defaultdict
import csv
from decimal import Decimal
from hashlib import sha256
from html import escape
import json
from pathlib import Path


def summarize(result: dict) -> dict:
    """Summarize accepted values and separately count review reasons."""
    months = defaultdict(lambda: {"rows": 0, "amount": Decimal("0.00")})
    categories = defaultdict(lambda: {"rows": 0, "amount": Decimal("0.00")})
    subcategories = defaultdict(lambda: {"rows": 0, "amount": Decimal("0.00")})
    channels = defaultdict(lambda: {"rows": 0, "amount": Decimal("0.00")})
    regions = defaultdict(lambda: {"rows": 0, "amount": Decimal("0.00")})
    customers = defaultdict(lambda: {"rows": 0, "amount": Decimal("0.00")})
    for row in result["accepted"]:
        amount = Decimal(row["amount"])
        keys = (
            (months, row["transaction_date"][:7]),
            (categories, row.get("category", "") or "Unspecified"),
            (subcategories, (row.get("category", "") or "Unspecified", row.get("subcategory", "") or "Unspecified")),
            (channels, row.get("sales_channel", "") or "Unspecified"),
            (regions, row.get("region", "") or "Unspecified"),
            (customers, row["customer_name"]),
        )
        for bucket, key in keys:
            bucket[key]["rows"] += 1
            bucket[key]["amount"] += amount
    reasons = Counter(code for row in result["rejected"] for code in row["reason_codes"].split(";") if code)
    return {
        "accepted_amount": sum((Decimal(row["amount"]) for row in result["accepted"]), Decimal("0.00")),
        "months": dict(sorted(months.items())),
        "categories": dict(sorted(categories.items())),
        "subcategories": dict(sorted(subcategories.items())),
        "channels": dict(sorted(channels.items())),
        "regions": dict(sorted(regions.items())),
        "customers": dict(sorted(customers.items(), key=lambda item: (-item[1]["amount"], item[0]))),
        "reasons": dict(sorted(reasons.items())),
    }


def _write_csv(path: Path, rows: list[dict], columns: list[str]) -> None:
    def safe_cell(value):
        if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
            return "'" + value
        return value

    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows({name: safe_cell(row[name]) for name in columns} for row in rows)


def _metric_table(rows: list[tuple[str, dict]], label: str) -> str:
    body = "".join(f"<tr><td>{escape(str(name))}</td><td>{data['rows']:,}</td><td>{data['amount']:,.2f}</td></tr>" for name, data in rows)
    return f'<table><thead><tr><th>{escape(label)}</th><th>Accepted rows</th><th>Amount (synthetic units)</th></tr></thead><tbody>{body}</tbody></table>'


def _month_chart(months: dict) -> str:
    if not months:
        return "<p>No accepted dates to chart.</p>"
    maximum = max((item["amount"] for item in months.values()), default=Decimal("0"))
    width, height = 720, 260
    chart_bottom, chart_top = 205, 25
    bar_width = min(65, 600 / len(months) - 20)
    bars = []
    for index, (month, data) in enumerate(months.items()):
        x = 70 + index * 600 / len(months)
        bar_height = float(data["amount"] / maximum) * (chart_bottom - chart_top) if maximum else 0
        y = chart_bottom - bar_height
        bars.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width:.1f}" height="{bar_height:.1f}" rx="4" fill="#16839B"><title>{escape(month)}: {data["rows"]} rows, {data["amount"]:,.2f} units</title></rect>')
        bars.append(f'<text x="{x + bar_width / 2:.1f}" y="{chart_bottom + 22}" text-anchor="middle">{escape(month[5:])}</text>')
        bars.append(f'<text x="{x + bar_width / 2:.1f}" y="{max(y - 7, 16):.1f}" text-anchor="middle" class="chart-value">{data["amount"]:,.0f}</text>')
    return f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="Accepted amount by month, January through June 2026" class="month-chart"><line x1="55" y1="{chart_bottom}" x2="680" y2="{chart_bottom}" stroke="#B8C5D1"/>{"".join(bars)}</svg>'


def _render_html(result: dict, summary: dict) -> str:
    counts = result["counts"]
    sources = "".join(f"<tr><td>{escape(item['file'])}</td><td>{item['rows']:,}</td></tr>" for item in result["sources"])
    issues = "".join(
        f"<tr><td>{escape(row['source_file'])}:{row['source_row']}</td><td>{escape(row['record_id'])}</td><td>{escape(row['reason_codes'])}</td><td>{escape(row['reason_messages'])}</td></tr>"
        for row in result["rejected"]
    ) or '<tr><td colspan="4">No exceptions</td></tr>'
    reason_rows = "".join(f"<tr><td>{escape(code)}</td><td>{count}</td></tr>" for code, count in summary["reasons"].items())
    category_rows = "".join(f'<tr><td>{escape(name)}</td><td>{data["rows"]:,}</td><td>{data["amount"]:,.2f}</td></tr>' for name, data in summary["categories"].items())
    subcategory_rows = [(f"{category} / {subcategory}", data) for (category, subcategory), data in summary["subcategories"].items()]
    top_customers = list(summary["customers"].items())[:10]
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Spreadsheet run report</title>
<style>
:root{{color-scheme:light}}body{{font:15px/1.5 Arial,sans-serif;max-width:1100px;margin:36px auto;padding:0 22px;color:#243B53;background:#fff}}h1{{font-size:29px;margin-bottom:4px}}h2{{font-size:21px;margin-top:34px;border-bottom:1px solid #D9E2EC;padding-bottom:7px}}p{{max-width:78ch}}.subtle{{color:#627D98;margin-top:0}}.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(145px,1fr));gap:12px;margin:25px 0}}.card{{background:#F0F4F8;border-radius:8px;padding:14px}}.card strong{{display:block;font-size:25px;color:#102A43}}.card span{{font-size:13px;color:#52697D}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:26px}}table{{border-collapse:collapse;width:100%;margin:12px 0 22px}}th,td{{text-align:left;border-bottom:1px solid #D9E2EC;padding:8px 9px;vertical-align:top}}th{{background:#243B53;color:#fff;font-weight:600}}td:nth-child(n+2){{font-variant-numeric:tabular-nums}}.scroll{{overflow-x:auto}}.month-chart{{width:100%;height:auto;background:#F7FAFC;border-radius:8px}}.month-chart text{{font:13px Arial,sans-serif;fill:#334E68}}.month-chart .chart-value{{font-size:11px}}a{{color:#1769AA}}.review{{border-left:4px solid #D9822B;background:#FFF8EC;padding:10px 16px}}@media(max-width:760px){{.grid{{grid-template-columns:1fr}}}}
</style></head><body>
<h1>Spreadsheet run report</h1><p class="subtle">Synthetic sales demo. Accepted amount is shown in synthetic units; no real customers or financial results are represented.</p>
<div class="cards"><div class="card"><strong>{counts['input']:,}</strong><span>Input rows</span></div><div class="card"><strong>{counts['accepted']:,}</strong><span>Accepted rows</span></div><div class="card"><strong>{counts['rejected']:,}</strong><span>Rows for review</span></div><div class="card"><strong>{counts['duplicates']:,}</strong><span>Duplicate rows</span></div><div class="card"><strong>{summary['accepted_amount']:,.2f}</strong><span>Accepted amount</span></div></div>
<p>Reconciliation: {counts['input']:,} input = {counts['accepted']:,} accepted + {counts['rejected']:,} rejected. Output rows = accepted rows ({counts['output']:,}). Duplicate rows are included in rejected rows.</p>
<h2>Monthly accepted amount</h2>{_month_chart(summary['months'])}{_metric_table(list(summary['months'].items()), 'Month')}
<div class="grid"><section><h2>Categories</h2><div class="scroll"><table><thead><tr><th>Category</th><th>Accepted rows</th><th>Amount</th></tr></thead><tbody>{category_rows}</tbody></table></div></section><section><h2>Subcategories</h2><div class="scroll">{_metric_table(subcategory_rows, 'Category / subcategory')}</div></section></div>
<div class="grid"><section><h2>Sales channels</h2><div class="scroll">{_metric_table(list(summary['channels'].items()), 'Channel')}</div></section><section><h2>Regions</h2><div class="scroll">{_metric_table(list(summary['regions'].items()), 'Region')}</div></section></div>
<h2>Top 10 synthetic customers</h2><div class="scroll">{_metric_table(top_customers, 'Customer')}</div>
<div class="grid"><section><h2>Source files</h2><table><thead><tr><th>File</th><th>Input rows</th></tr></thead><tbody>{sources}</tbody></table></section><section><h2>Review reasons</h2><table><thead><tr><th>Reason code</th><th>Rows</th></tr></thead><tbody>{reason_rows}</tbody></table><p class="subtle">A row can have more than one reason.</p></section></div>
<h2>Rows for review</h2><div class="review"><p>Correct the source row, then run the tool into a new output folder. Resolve duplicate IDs with the source owner. Convert ambiguous dates to ISO format before rerunning.</p></div><div class="scroll"><table><thead><tr><th>Source row</th><th>Record ID</th><th>Reason</th><th>Action detail</th></tr></thead><tbody>{issues}</tbody></table></div>
<p>Download <a href="clean.csv">clean data</a>, <a href="exceptions.csv">exceptions</a>, or <a href="manifest.json">run manifest</a>.</p></body></html>
"""


def write_outputs(output_dir: Path, result: dict, config: dict, config_path: Path, input_files: list[Path]) -> None:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError(f"Output directory must be empty: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    columns = [*config["fields"], "source_file", "source_row"]
    _write_csv(output_dir / "clean.csv", result["accepted"], columns)
    _write_csv(output_dir / "exceptions.csv", result["rejected"], [*columns, "reason_codes", "reason_messages"])
    file_hashes = {path.name: sha256(path.read_bytes()).hexdigest() for path in input_files}
    summary = summarize(result)
    manifest = {
        "schema_version": config["version"],
        "config_file": config_path.name,
        "config_sha256": sha256(config_path.read_bytes()).hexdigest(),
        "inputs": [{"file": item["file"], "rows": item["rows"], "sha256": file_hashes[item["file"]]} for item in result["sources"]],
        "counts": result["counts"],
        "accepted_amount": str(summary["accepted_amount"]),
        "duplicate_policy": "First valid occurrence accepted; later occurrences rejected for review",
        "reconciliation": {"input_equals_accepted_plus_rejected": result["counts"]["input"] == result["counts"]["accepted"] + result["counts"]["rejected"], "output_equals_accepted": result["counts"]["output"] == result["counts"]["accepted"]},
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (output_dir / "report.html").write_text(_render_html(result, summary), encoding="utf-8")
