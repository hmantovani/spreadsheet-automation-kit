# Data contract

The demo uses synthetic sales transactions. Each source row represents one order. `record_id` is the duplicate key across all files in a run. The first valid occurrence is accepted; every later occurrence is sent to review with `DUPLICATE_KEY`. An invalid row does not reserve its identifier.

The editable rules live in `config/schema.json`. Fields are `record_id` (required text), `transaction_date` (required date), `customer_name` (required text), `description` (optional text), `amount` (required decimal, at least 0.01), `category` (required), `subcategory` (required), `sales_channel` (required), and `region` (required). Output adds `source_file` and `source_row`. These audit fields are never mapped from input.

The report depends on the canonical `record_id`, `transaction_date`, `customer_name`, and `amount` fields, so those four names cannot be removed. Output audit column names are reserved. Additional fields and aliases may be configured. Exported CSV text beginning with a spreadsheet formula character is prefixed with an apostrophe to prevent formula execution when opened in Excel.

Allowed categories are hardware, service, and software. Their subcategories are configured as follows: hardware has accessories, devices, and components; service has consulting, implementation, and support; software has licenses, subscriptions, and training. Allowed channels are direct, partner, and online. Allowed regions are north, south, east, and west. A valid subcategory under the wrong category is rejected with `CATEGORY_SUBCATEGORY_MISMATCH`.

Header matching ignores case, leading/trailing whitespace, repeated spaces, and accents. Unknown columns are ignored. A file with no recognizable header is rejected with a clear file error. Two headers mapping to the same canonical field are rejected as ambiguous.

Dates support ISO `YYYY-MM-DD`, Brazilian `DD/MM/YYYY`, and US `MM/DD/YYYY`. A slash date that parses as both regional formats to different days is flagged `INVALID_DATE`; the user must correct it to ISO. Numeric amounts support `1234.56`, `1,234.56`, and `1.234,56`. A single separator with exactly three following digits is considered ambiguous and flagged, unless the separator is a dot in an otherwise ungrouped decimal with more than three digits. The parser never guesses currency symbols or signs.

Blank strings and configured null tokens are empty. Text is trimmed and internal whitespace collapsed. Fields with `case: lower` are lowercased before allowed-value checks. Dates output as ISO strings and amounts as two-decimal strings. The reason codes in configuration are stable keys; messages are editable. Invalid allowed values receive `INVALID_<FIELD>` codes, such as `INVALID_SUBCATEGORY`.

Every input row ends in exactly one bucket: accepted or rejected. Duplicate rows are a subset of rejected rows. Thus `input = accepted + rejected`, `duplicates <= rejected`, and `output = accepted`. Rejected rows retain source coordinates and original field values for correction and rerun.

Completely blank data rows are treated as spreadsheet spacing rather than records. Nonblank rows are counted even if required fields are empty. When editing the configuration, retain a reason message for every code used by the pipeline.

The HTML report computes accepted amount with decimal arithmetic. Its monthly, category, subcategory, channel, region, and customer views each sum to the same accepted row count and accepted amount. Rejected rows are listed separately. A rejected row can carry more than one reason code, so reason counts may exceed rejected row count in a different dataset.
