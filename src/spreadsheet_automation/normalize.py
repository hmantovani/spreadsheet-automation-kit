"""Canonical header matching and conservative value parsing."""

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import re
import unicodedata


def normalize_header(value) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return " ".join(text.casefold().split())


def map_headers(headers, config: dict) -> dict[str, int]:
    aliases = {}
    for name, choices in config["aliases"].items():
        for alias in choices:
            normalized = normalize_header(alias)
            if normalized in aliases and aliases[normalized] != name:
                raise ValueError(f"Alias {alias!r} maps to multiple fields")
            aliases[normalized] = name
    mapped = {}
    for index, header in enumerate(headers):
        name = aliases.get(normalize_header(header))
        if name in mapped:
            raise ValueError(f"Two columns map to {name}")
        if name:
            mapped[name] = index
    if not mapped:
        raise ValueError("No configured columns found in header row")
    return mapped


def clean_text(value, null_tokens: list[str]) -> str:
    text = " ".join(str(value).split()) if value is not None else ""
    return "" if text.casefold() in {str(token).casefold() for token in null_tokens} else text


def parse_date(value, formats: list[str]) -> str | None:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    matches = set()
    for fmt in formats:
        try:
            matches.add(datetime.strptime(str(value), fmt).date().isoformat())
        except ValueError:
            pass
    return next(iter(matches)) if len(matches) == 1 else None


def parse_decimal(value) -> str | None:
    if isinstance(value, bool):
        return None
    text = str(value).strip().replace(" ", "")
    if not re.fullmatch(r"[+-]?[\d.,]+", text):
        return None
    if "," in text and "." in text:
        decimal_sep = "," if text.rfind(",") > text.rfind(".") else "."
        group_sep = "." if decimal_sep == "," else ","
        integer, fraction = text.rsplit(decimal_sep, 1)
        groups = integer.lstrip("+-").split(group_sep)
        if len(groups) < 2 or not groups[0].isdigit() or not all(len(group) == 3 and group.isdigit() for group in groups[1:]) or not fraction.isdigit():
            return None
        text = integer.replace(group_sep, "") + "." + fraction
    elif "," in text:
        if text.count(",") != 1:
            return None
        left, right = text.split(",")
        if len(right) == 3:
            return None
        text = left + "." + right
    elif "." in text:
        if text.count(".") != 1 or len(text.split(".")[1]) == 3:
            return None
    try:
        amount = Decimal(text)
        if not amount.is_finite() or amount.as_tuple().exponent < -2:
            return None
        return f"{amount:.2f}"
    except InvalidOperation:
        return None
