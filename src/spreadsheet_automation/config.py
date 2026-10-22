"""Load and validate the editable data contract."""

import json
from pathlib import Path


def load_config(path: Path) -> dict:
    config = json.loads(path.read_text(encoding="utf-8"))
    fields = config.get("fields", {})
    aliases = config.get("aliases", {})
    if not fields or set(fields) != set(aliases):
        raise ValueError("Configuration fields and aliases must contain the same nonempty keys")
    if not {"record_id", "transaction_date", "customer_name", "amount"}.issubset(fields):
        raise ValueError("Configuration must retain record_id, transaction_date, customer_name, and amount")
    if {"source_file", "source_row", "reason_codes", "reason_messages"} & set(fields):
        raise ValueError("Configuration cannot redefine output audit fields")
    if any(field not in fields for field in config.get("duplicate_key", [])):
        raise ValueError("Duplicate key names an unknown field")
    if not config.get("duplicate_key"):
        raise ValueError("Configuration must define a duplicate key")
    for name, rule in fields.items():
        if rule.get("type") not in {"text", "date", "decimal"}:
            raise ValueError(f"Unsupported type for {name}")
        if not aliases[name]:
            raise ValueError(f"Missing aliases for {name}")
        if rule.get("case") not in {None, "lower"}:
            raise ValueError(f"Unsupported text case for {name}")
    pairs = config.get("category_subcategories", {})
    if pairs:
        if "category" not in fields or "subcategory" not in fields:
            raise ValueError("Category pairing needs category and subcategory fields")
        if set(pairs) != set(fields["category"].get("allowed", [])):
            raise ValueError("Category pairing must cover every allowed category")
        allowed = set(fields["subcategory"].get("allowed", []))
        if any(not values or set(values) - allowed for values in pairs.values()):
            raise ValueError("Category pairing contains an unknown or empty subcategory")
    return config
