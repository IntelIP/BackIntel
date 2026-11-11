---
name: clickhouse
description: Query a ClickHouse column store through its native SQL interface.
---

Inspect tables and sample values first. Dates in this testbed are ISO strings; use
parseDateTimeBestEffortOrNull when date functions need timestamps. Nullable identifiers
and duplicate rows need the same care as relational stores. Set explicit ordering for
rankings and tie breaks. JOIN keys must have compatible types. Prefer aggregate queries
over downloading rows. For Python use the read-only clickhouse_connect client described
by run_python. Do not request external table functions or change query settings.
