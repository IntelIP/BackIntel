---
name: postgres
description: "PostgreSQL dialect notes for analytical SQL: dates, division, nulls, text matching, ranking, percentiles."
---

# PostgreSQL for analysis

- Timestamps are TIMESTAMP columns. Use `date_trunc('month', col)`, `to_char(col, 'YYYY-MM')`,
  `extract(year FROM col)`, and `extract(epoch FROM (a - b)) / 86400` for fractional days.
- Integer division truncates: write `a::numeric / b` or `1.0 * a / b`. `COUNT(*)` counts rows,
  `COUNT(col)` non-nulls, `COUNT(DISTINCT col)` distinct non-nulls.
- `ILIKE` is case-insensitive; `=` and `LIKE` are case-sensitive. `col ~ '\d'` tests for a digit.
- Percentiles: `percentile_cont(0.5) WITHIN GROUP (ORDER BY col)`. Window functions, CTEs and
  `FILTER (WHERE ...)` on aggregates are available.
- Statements time out after 60 seconds; aggregate in SQL and avoid cross joins.
- Results return at most 200 rows. Only SELECT/WITH/EXPLAIN run; the role is read-only.
