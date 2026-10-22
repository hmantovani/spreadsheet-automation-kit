"""Read spreadsheet rows while retaining their original coordinates."""

import csv
from pathlib import Path
from zipfile import BadZipFile

from openpyxl import load_workbook


def discover_files(input_path: Path) -> list[Path]:
    if input_path.is_file():
        if input_path.suffix.lower() not in {".csv", ".xlsx"}:
            raise ValueError(f"Unsupported input file: {input_path.name}")
        return [input_path]
    if not input_path.is_dir():
        raise ValueError(f"Input path does not exist: {input_path}")
    files = sorted((p for p in input_path.iterdir() if p.is_file() and p.suffix.lower() in {".csv", ".xlsx"}), key=lambda p: p.name)
    if not files:
        raise ValueError(f"No CSV or XLSX files found in {input_path}")
    return files


def read_rows(path: Path):
    """Yield (one-based worksheet/file row number, cells), including empty data rows."""
    try:
        if path.suffix.lower() == ".csv":
            with path.open("r", encoding="utf-8-sig", newline="") as stream:
                reader = csv.reader(stream)
                yield from enumerate(reader, start=1)
        elif path.suffix.lower() == ".xlsx":
            workbook = load_workbook(path, read_only=True, data_only=True)
            try:
                sheet = workbook.active
                for number, row in enumerate(sheet.iter_rows(values_only=True), start=1):
                    yield number, list(row)
            finally:
                workbook.close()
        else:
            raise ValueError(f"Unsupported input file: {path.name}")
    except (OSError, ValueError, csv.Error, KeyError, BadZipFile) as exc:
        raise ValueError(f"Cannot read {path.name}: {exc}") from exc
