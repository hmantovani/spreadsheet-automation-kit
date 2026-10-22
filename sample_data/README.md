# Synthetic demo inputs

These transactions are invented for this portfolio demonstration. No customer or financial record is real. The CSV uses English labels and US formatted values; the workbook uses Portuguese labels and Brazilian formatted values. Both contain 180 rows spread across January through June 2026, for 360 input rows total.

The generator uses fixed formulas rather than random draws. It cycles through 30 fictional customers, three categories with three subcategories each, three channels, and four regions. Accepted amounts increase modestly by month to give the report a visible trend. These patterns are illustrative and should not be interpreted as realistic market behavior.

Expected result for the supplied configuration: 360 input rows, 348 accepted rows, 12 rejected rows, 1 duplicate, and 348 output rows. The 12 exceptions cover missing values, ambiguous date, invalid amount, invalid category or subcategory, a category and subcategory mismatch, invalid channel or region, and a duplicate ID. `expected.json` lists every accepted ID and each exception's exact source coordinate and reason.

The source generator is `scripts/generate_demo_workbook.mjs`. It writes both inputs and `expected.json`. The workbook is built with the Codex artifact authoring runtime. The Python CLI does not require that runtime; it reads the checked-in workbook using `openpyxl`.
