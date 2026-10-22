"""Pure processing pipeline and row-level validation."""

from decimal import Decimal
from pathlib import Path

from .ingest import discover_files, read_rows
from .normalize import clean_text, map_headers, parse_date, parse_decimal


def process(input_path: Path, config: dict) -> dict:
    files = discover_files(input_path)
    accepted, rejected, seen = [], [], set()
    sources = []
    for path in files:
        rows = iter(read_rows(path))
        try:
            _, headers = next(rows)
        except StopIteration as exc:
            raise ValueError(f"Empty input file: {path.name}") from exc
        try:
            mapping = map_headers(headers, config)
        except ValueError as exc:
            raise ValueError(f"{path.name}: {exc}") from exc
        source_count = 0
        for number, cells in rows:
            if all(value is None or str(value).strip() == "" for value in cells):
                continue
            source_count += 1
            raw = {name: cells[index] if index < len(cells) else None for name, index in mapping.items()}
            canonical = {}
            issues = []
            for name, rule in config["fields"].items():
                value = raw.get(name)
                text = clean_text(value, config["null_tokens"])
                if not text:
                    canonical[name] = ""
                    if rule.get("required"):
                        issues.append(("MISSING_REQUIRED", name))
                    continue
                if rule["type"] == "date":
                    parsed = parse_date(value, config["date_formats"])
                    canonical[name] = parsed or text
                    if parsed is None:
                        issues.append(("INVALID_DATE", name))
                elif rule["type"] == "decimal":
                    parsed = parse_decimal(value)
                    canonical[name] = parsed or text
                    if parsed is None:
                        issues.append(("INVALID_DECIMAL", name))
                    elif "min" in rule and Decimal(parsed) < Decimal(rule["min"]):
                        issues.append(("BELOW_MINIMUM", name))
                else:
                    canonical[name] = text.casefold() if rule.get("case") == "lower" else text
                    if rule.get("allowed") and canonical[name] not in rule["allowed"]:
                        issues.append((f"INVALID_{name.upper()}", name))
            pairs = config.get("category_subcategories", {})
            category = canonical.get("category")
            subcategory = canonical.get("subcategory")
            if category in pairs and subcategory and subcategory in config["fields"]["subcategory"].get("allowed", []) and subcategory not in pairs[category]:
                issues.append(("CATEGORY_SUBCATEGORY_MISMATCH", "subcategory"))
            key = tuple(canonical[name] for name in config["duplicate_key"])
            if all(key) and key in seen:
                issues.append(("DUPLICATE_KEY", ",".join(config["duplicate_key"])))
            record = {**canonical, "source_file": path.name, "source_row": number}
            if issues:
                rejected.append({**record, "reason_codes": ";".join(code for code, _ in issues), "reason_messages": "; ".join(f"{name}: {config['reason_messages'][code]}" for code, name in issues)})
            else:
                accepted.append(record)
                seen.add(key)
        sources.append({"file": path.name, "rows": source_count})
    duplicates = sum("DUPLICATE_KEY" in row["reason_codes"].split(";") for row in rejected)
    counts = {"input": sum(source["rows"] for source in sources), "accepted": len(accepted), "rejected": len(rejected), "duplicates": duplicates, "output": len(accepted)}
    assert counts["input"] == counts["accepted"] + counts["rejected"]
    return {"accepted": accepted, "rejected": rejected, "sources": sources, "counts": counts}
