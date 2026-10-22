# Initial Outline

## Product goal

Turn recurring, inconsistent spreadsheet files into a standardized dataset and a shareable report while making every correction, rejection, and reconciliation visible for human review.

## First release scope

Build a command-line tool that processes CSV and `.xlsx` inputs from a single folder and produces a timestamped run folder containing:

- a cleaned, standardized dataset;
- an exception workbook or CSV for rows needing review;
- a concise HTML or Excel summary report; and
- a machine-readable run manifest with counts, rules applied, and source-file details.

## Intended user flow

1. A user places one or more recurring source files in an input folder.
2. The tool identifies the source type and maps known alternate column names to a canonical schema.
3. It normalizes dates, text, numeric values, and empty fields.
4. It validates required values, formats, ranges, and duplicate records.
5. It separates accepted rows from rows needing review; it never silently discards data.
6. It writes the cleaned data, exceptions, reconciliation summary, and report to a dated output folder.

## Canonical data model

The implemented configurable schema uses:

- `record_id` — unique business or source identifier;
- `transaction_date` — normalized ISO date;
- `customer_name` — trimmed, normalized text;
- `description` — optional normalized text;
- `amount` — numeric decimal value;
- `category` — required controlled category;
- `subcategory` — controlled value that must belong to its category;
- `sales_channel` and `region` — controlled reporting dimensions;
- `source_file` and `source_row` — audit fields added by the tool.

The first version should keep column aliases and validation rules in a human-editable configuration file rather than embedding them only in code.

## Validation and exception policy

- Required-field, type, format, and range checks identify invalid data.
- Duplicate detection uses a documented composite key or a supplied identifier.
- Ambiguous values are flagged rather than guessed.
- Every exception includes a reason code, clear message, source file, and source row.
- Rows that pass validation are retained; rejected rows remain available for correction and rerun.

## Architecture

Use a small Python package with separate modules for file ingestion, schema mapping, normalization, validation, reporting, and command-line orchestration. Keep business rules configurable and write deterministic run artifacts so the same input and configuration produce the same outcome.

## Suggested repository structure

```text
src/spreadsheet_automation/
  cli.py
  ingest.py
  mapping.py
  normalize.py
  validate.py
  report.py
  models.py
config/
  schema.yml
  column_aliases.yml
sample_data/
tests/
docs/
```

## Demonstration data and narrative

Prepare two or three intentionally messy sample files that vary column names, date formats, missing required fields, duplicate rows, and number formatting. The walkthrough should show the raw inputs, the resulting cleaned output, the exception list, and a reconciliation table with input, accepted, rejected, duplicate, and output counts.

## Acceptance criteria for the first demo

- One command processes the included sample files from a clean checkout.
- The output names each source and preserves row-level provenance.
- Validation errors are readable without inspecting code.
- Reconciliation counts balance: input = accepted + rejected (with duplicates explicitly categorized).
- A reviewer can correct an exception in the input and rerun the tool successfully.

## Build sequence

1. Define the canonical schema, aliases, and validation rule catalog.
2. Create messy sample inputs and expected output fixtures.
3. Implement CSV/XLSX ingestion and normalization.
4. Add validation, duplicate handling, and exception artifacts.
5. Generate the reconciliation summary and shareable report.
6. Add automated tests and a before/after walkthrough.
7. Optionally add a lightweight upload interface once the CLI workflow is solid.
