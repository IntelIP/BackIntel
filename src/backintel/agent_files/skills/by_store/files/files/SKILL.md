---
name: files
description: "Working with a folder of raw CSV and JSON files in sandboxed Python: typing, dates, joins, and reproducible output."
---

# Raw CSV and JSON files

- There is no query engine: `run_sql` is unavailable. Use `run_python` with polars (fast) or
  pandas. The directory is in the environment variable `BACKINTEL_FILES_DIR`.
- Read .jsonl with `pl.read_ndjson(path)`; .csv and .jsonl files can hold different tables
  in the same folder. Never concatenate files representing different tables.
- Read CSV with explicit types where they matter:
  `pl.read_csv(path, try_parse_dates=True)` or `pl.read_csv(path, schema_overrides={...})`.
  Dates are text until parsed; ids may be read as numbers (leading zeros lost) unless typed.
- Several files may cover overlapping periods or be exports of the same table; check for
  duplicated rows before aggregating (`df.unique()`, `df.is_duplicated().sum()`).
- Joins: `left.join(right, on="key", how="inner")`. Aggregations: `group_by(...).agg(...)`.
- Print the final numbers with full precision (`print(repr(value))`) and keep the program
  self-contained: the exact program is your evidence and will be re-run.
- One program per question is ideal; print intermediate checks only when they inform the
  answer.
