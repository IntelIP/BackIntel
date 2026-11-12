---
name: sqlite
description: "SQLite dialect notes for analytical queries: dates, division, nulls, text matching and ranking."
---

# SQLite for analysis

- Dates are text (ISO 8601, e.g. `2010-12-01 08:26:00`). Use `strftime('%Y-%m', col)` for
  months, `date(col)` for days, `julianday(a) - julianday(b)` for differences in days.
  Compare with text bounds: `col >= '2011-01-01' AND col < '2011-02-01'`.
- Integer division truncates: write `CAST(SUM(x) AS REAL) / COUNT(*)` or `1.0 * a / b`.
- `AVG`, `SUM` ignore NULLs; `COUNT(*)` counts rows, `COUNT(col)` counts non-null values,
  `COUNT(DISTINCT col)` distinct non-null values.
- `LIKE` is case-insensitive for ASCII; `=` is case-sensitive. Trim text with `TRIM()`.
- Booleans are 0/1; `SUM(condition)` counts matching rows.
- Rankings: `ORDER BY metric DESC LIMIT n`. Window functions are available
  (`ROW_NUMBER() OVER (PARTITION BY ... ORDER BY ...)`), as are CTEs (`WITH ... AS (...)`).
- Percentiles: SQLite has no `percentile` function; use `run_python` or a window function
  with `NTILE`/`ROW_NUMBER`.
- Results return at most 200 rows. Aggregate rather than paging through raw rows.
- Only `SELECT`/`WITH`/`EXPLAIN` statements run; the database is read-only.
