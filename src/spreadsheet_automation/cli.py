"""Command line entry point for the processing pipeline."""

import argparse
from pathlib import Path
import sys

from .config import load_config
from .ingest import discover_files
from .pipeline import process
from .report import write_outputs


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Clean CSV/XLSX exports and report exceptions")
    parser.add_argument("--input", type=Path, required=True, help="CSV/XLSX file or folder")
    parser.add_argument("--config", type=Path, required=True, help="JSON data contract")
    parser.add_argument("--output", type=Path, required=True, help="New or empty output folder")
    args = parser.parse_args(argv)
    try:
        config = load_config(args.config)
        files = discover_files(args.input)
        result = process(args.input, config)
        write_outputs(args.output, result, config, args.config, files)
    except (OSError, ValueError, KeyError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    counts = result["counts"]
    print(f"Input {counts['input']} | accepted {counts['accepted']} | rejected {counts['rejected']} | duplicates {counts['duplicates']} | output {counts['output']}")
    print(f"Report: {args.output / 'report.html'}")
    return 0
