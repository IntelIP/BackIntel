"""The analyst's tools, bound to one store and one sandbox.

Each tool is a contract between deterministic code and the model: the description says
exactly what comes back and what to do on failure. Results are JSON so they can be cited and
re-executed. Nothing here writes to the store.
"""

from __future__ import annotations

import json
from dataclasses import asdict

from langchain_core.tools import ToolException, tool

from backintel.sandbox import PythonSandbox
from backintel.stores.base import QueryRefused, Store
from backintel.stores.multi import MultiStore


def build_tools(store: Store, sandbox: PythonSandbox) -> list:
    env = store.python_environment()
    mounts = store.python_mounts()
    network = store.sandbox_network()

    @tool
    def list_tables() -> str:
        """List every table in the connected store with its row count and column names/types.

        Call this first. Returns JSON: {"store": id, "query_language": ..., "tables": [{"name",
        "row_count", "columns": [{"name", "type"}]}]}.
        """
        tables = [
            {
                "name": t.name,
                "row_count": t.row_count,
                "columns": [{"name": c.name, "type": c.type} for c in t.columns],
            }
            for t in store.list_tables()
        ]
        return json.dumps({"store": store.id, "query_language": store.query_language, "tables": tables})

    @tool
    def describe_table(table: str) -> str:
        """Describe one table: columns with types and null counts, row count, and 3 sample rows.

        Use it to learn value formats (dates, codes, casing) before writing a query. Pass the table
        name exactly as list_tables shows it (qualified as `<store id>.<table>` when several stores
        are connected). Returns JSON {"name", "row_count", "columns": [{"name","type","nulls"}],
        "sample": [...]} or an error naming the available tables.
        """
        try:
            info = store.describe_table(table)
        except QueryRefused as error:
            raise ToolException(str(error)) from error
        return json.dumps(asdict(info), default=str)

    def _run(sql: str, target: str | None) -> str:
        try:
            text = f"-- store: {target}\n{sql}" if isinstance(store, MultiStore) else sql
            result = store.query(text)
        except (QueryRefused, NotImplementedError) as error:
            raise ToolException(str(error)) from error
        return json.dumps(result.to_dict(), default=str)

    if isinstance(store, MultiStore):

        @tool
        def run_sql(sql: str, store_id: str) -> str:
            """Run one read-only SQL statement on one of the connected stores and return its rows.

            `store_id` is a store id from list_tables (e.g. `postgres:olist_orders`). Only
            SELECT/WITH/EXPLAIN are allowed; a statement cannot span stores, so to combine data from
            two stores either pull aggregated results from each and combine them, or use run_python
            which can read every store. At most 200 rows are returned. Returns JSON {"columns",
            "rows", "row_count", "truncated", "elapsed_ms"}. Cite every query you rely on in
            `evidence` with its `store` id.
            """
            return _run(sql, store_id)

    elif store.kind == "ferretdb":

        @tool
        def run_query(query: str) -> str:
            """Run a read-only MongoDB aggregation pipeline against FerretDB.

            Pass JSON {"collection":"name", "pipeline":[{"$match":...}, {"$group":...}]}.
            At most 200 documents are returned. Writes and JavaScript are disabled. Cite the
            exact JSON in evidence with kind='query'. On a compatibility error, correct the
            pipeline or use run_python with pymongo to read and combine documents.
            """
            return _run(query, None)

        run_sql = run_query

    else:

        @tool
        def run_sql(sql: str) -> str:
            """Run one read-only SQL statement against the connected store and return its rows.

            Dialect: see the store's query_language from list_tables. Only SELECT/WITH/EXPLAIN are
            allowed; writes are refused. At most 200 rows are returned (the result says if it was
            truncated), so aggregate in SQL rather than paging through raw rows. Returns JSON
            {"columns", "rows", "row_count", "truncated", "elapsed_ms"}. On an SQL error the message
            explains what to fix; correct the statement and call again. Every number in your final
            answer must come from a query you cite verbatim in `evidence`.
            """
            return _run(sql, None)

    @tool
    def run_python(code: str) -> str:
        """Run a Python program in a sandbox with read-only access to the connected store.

        Use it for statistics or transformations SQL cannot express well (percentiles,
        correlations, cohort logic). Available: Python 3.12, sqlite3, polars, pandas, numpy,
        scipy. No network. Read the store as the environment variable BACKINTEL_STORE_NOTE
        describes (also shown below). Print what you need; stdout is capped at 12k chars; the
        run stops after 120 seconds. Returns JSON {"stdout", "stderr", "exit_code",
        "elapsed_ms", "backend"}. Cite the exact program in `evidence` when its output feeds
        the answer.
        """
        result = sandbox.run(code, env=env, mounts=mounts, network=network)
        return json.dumps(result.to_dict())

    run_python.description += "\n\nStore access: " + env.get("BACKINTEL_STORE_NOTE", "")
    tools = [list_tables, describe_table, run_sql, run_python]
    for item in tools:
        item.handle_tool_error = True  # a refused query is a message the agent can act on, not a crash
    return tools
