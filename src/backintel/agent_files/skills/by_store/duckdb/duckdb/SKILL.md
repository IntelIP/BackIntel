---
name: duckdb
description: "DuckDB dialect notes for analytical SQL over Parquet tables: dates, division, nulls, ranking, percentiles."
---

# DuckDB for analysis

- Tables are views over Parquet files; timestamps are real TIMESTAMP columns. Use
  `date_trunc('month', col)`, `strftime(col, '%Y-%m')`, `date_diff('day', a, b)`,
  `extract(year FROM col)`. Compare with `col >= TIMESTAMP '2011-01-01'`.
- Integer division: `a / b` on integers returns a double in DuckDB, but cast explicitly
  (`a::DOUBLE / b`) to be safe. `COUNT(*)` counts rows, `COUNT(col)` non-nulls.
- `ILIKE` is case-insensitive; `LIKE` and `=` are case-sensitive. `regexp_matches(col, '\d')`
  tests for a digit.
- Percentiles: `quantile_cont(col, 0.5)`; also `median(col)`. Window functions and CTEs work.
- `SUMMARIZE table` and `DESCRIBE table` are available for profiling.
- Results return at most 200 rows. Only SELECT/WITH/EXPLAIN/DESCRIBE run; file paths and
  configuration statements are refused.
