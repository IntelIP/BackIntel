"""Lake store: Parquet files queried in place with DuckDB.

This is the first increment of the planned lake (Parquet in Apache Iceberg on Garage, read by
DuckDB). It queries the canonical Parquet directory directly, with no catalog and no object
store, and is labelled `lake-parquet` so results are never mistaken for Iceberg coverage.
"""

from __future__ import annotations

import re
import threading
import time
from pathlib import Path

import duckdb

from backintel.stores.base import (
    MAX_ROWS,
    ColumnInfo,
    QueryRefused,
    QueryResult,
    TableInfo,
    clip_cell,
)

READ_ONLY_PREFIXES = ("select", "with", "explain", "describe", "show", "summarize", "from")
FORBIDDEN = re.compile(
    r"\b(attach|detach|insert|update|delete|drop|alter|create|replace|copy|export|import|install|load|"
    r"set|reset|pragma|call|vacuum|checkpoint)\b",
    re.I,
)


def screen_sql(text: str) -> str:
    cleaned = re.sub(r"--[^\n]*", "", text)
    cleaned = re.sub(r"/\*.*?\*/", "", cleaned, flags=re.S).strip().rstrip(";").strip()
    if not cleaned:
        raise QueryRefused("Empty query.")
    if ";" in cleaned:
        raise QueryRefused("Send one statement at a time.")
    if not cleaned.lower().startswith(READ_ONLY_PREFIXES):
        raise QueryRefused(
            "Only SELECT / WITH / EXPLAIN / DESCRIBE statements are allowed; the lake is read-only."
        )
    if FORBIDDEN.search(cleaned):
        raise QueryRefused(
            "The statement contains a write, DDL or configuration keyword; the lake is read-only."
        )
    if re.search(r"read_(csv|json|text|blob)|glob\(|'(/|~)", cleaned, re.I):
        raise QueryRefused("Query the registered tables; direct file paths are not allowed.")
    return cleaned


class DuckDBLakeStore:
    kind = "lake-parquet"
    query_language = "SQL (DuckDB dialect) over Parquet tables"

    def __init__(
        self,
        parquet_dir: Path,
        *,
        dataset: str,
        exclude: tuple[str, ...] = ("geolocation",),
        only: tuple[str, ...] | None = None,
        timeout_s: float = 60.0,
    ):
        self.dir = Path(parquet_dir)
        if not self.dir.exists():
            raise FileNotFoundError(f"Parquet directory not found: {self.dir}")
        self.dataset = dataset
        self.id = f"lake-parquet:{dataset}"
        self.timeout_s = timeout_s
        self._lock = threading.Lock()
        # Only this directory may ever be read, and nothing can be reconfigured afterwards.
        self.conn = duckdb.connect(database=":memory:")
        self.conn.execute("SET allowed_directories = [?]", [str(self.dir)])
        self.conn.execute("SET enable_external_access = false")
        self.tables: dict[str, Path] = {}
        for path in sorted(self.dir.glob("*.parquet")):
            if path.stem in exclude or (only is not None and path.stem not in only):
                continue
            # The sheet label exists only for the oracle; no real export carries it (see build_stores).
            described = self.conn.execute(f"DESCRIBE SELECT * FROM read_parquet('{path}')").fetchall()
            select = "* EXCLUDE (source_sheet)" if any(r[0] == "source_sheet" for r in described) else "*"
            self.conn.execute(f"CREATE VIEW \"{path.stem}\" AS SELECT {select} FROM read_parquet('{path}')")
            self.tables[path.stem] = path
        self.conn.execute("SET lock_configuration = true")

    def close(self) -> None:
        self.conn.close()

    def _columns(self, name: str) -> list[tuple[str, str]]:
        rows = self.conn.execute(f'DESCRIBE "{name}"').fetchall()
        return [(r[0], r[1]) for r in rows]

    def list_tables(self) -> list[TableInfo]:
        with self._lock:
            out = []
            for name in self.tables:
                count = self.conn.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
                cols = [ColumnInfo(name=c, type=t) for c, t in self._columns(name)]
                out.append(TableInfo(name=name, row_count=count, columns=cols))
            return out

    def describe_table(self, name: str) -> TableInfo:
        if name not in self.tables:
            raise QueryRefused(f"No table named {name!r}. Tables: {', '.join(self.tables)}")
        with self._lock:
            count = self.conn.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
            cols = self._columns(name)
            null_expr = ", ".join(f'COUNT(*) - COUNT("{c}")' for c, _ in cols)
            nulls = self.conn.execute(f'SELECT {null_expr} FROM "{name}"').fetchone()
            columns = [
                ColumnInfo(name=c, type=t, nulls=int(n)) for (c, t), n in zip(cols, nulls, strict=True)
            ]
            cur = self.conn.execute(f'SELECT * FROM "{name}" LIMIT 3')
            names = [d[0] for d in cur.description]
            sample = [dict(zip(names, (clip_cell(v) for v in row), strict=True)) for row in cur.fetchall()]
        return TableInfo(name=name, row_count=count, columns=columns, sample=sample)

    def query(self, text: str, *, max_rows: int = MAX_ROWS) -> QueryResult:
        sql = screen_sql(text)
        started = time.monotonic()
        with self._lock:
            timer = threading.Timer(self.timeout_s, self.conn.interrupt)
            timer.start()
            try:
                cur = self.conn.execute(sql)
                rows = cur.fetchmany(max_rows + 1)
                columns = [d[0] for d in cur.description] if cur.description else []
            except duckdb.InterruptException as error:
                raise QueryRefused(f"Query exceeded {self.timeout_s:.0f}s and was stopped.") from error
            except duckdb.Error as error:
                raise QueryRefused(f"DuckDB error: {str(error)[:600]}") from error
            finally:
                timer.cancel()
        truncated = len(rows) > max_rows
        rows = rows[:max_rows]
        return QueryResult(
            columns=columns,
            rows=[[clip_cell(v) for v in row] for row in rows],
            row_count=len(rows),
            truncated=truncated,
            elapsed_ms=int((time.monotonic() - started) * 1000),
            note=f"Only the first {max_rows} rows are shown; aggregate or add LIMIT/OFFSET."
            if truncated
            else None,
        )

    def python_mounts(self) -> dict[str, str]:
        return {str(self.dir): str(self.dir)}

    def sandbox_network(self) -> str | None:
        return None

    def python_environment(self) -> dict[str, str]:
        files = ", ".join(f"{name}.parquet" for name in self.tables)
        return {
            "BACKINTEL_PARQUET_DIR": str(self.dir),
            "BACKINTEL_STORE_NOTE": (
                f"Parquet files are in the directory BACKINTEL_PARQUET_DIR ({files}). Read them with "
                "polars.read_parquet(path) or duckdb.sql(\"SELECT ... FROM read_parquet('<path>')\")."
            ),
        }
