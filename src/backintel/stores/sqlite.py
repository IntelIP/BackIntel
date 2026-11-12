"""SQLite store: a read-only connection, bounded results, and statement screening."""

from __future__ import annotations

import re
import sqlite3
import threading
import time
from pathlib import Path

from backintel.stores.base import (
    MAX_ROWS,
    ColumnInfo,
    QueryRefused,
    QueryResult,
    TableInfo,
    clip_cell,
)

READ_ONLY_PREFIXES = ("select", "with", "explain", "pragma table_info", "pragma table_list")
FORBIDDEN = re.compile(
    r"\b(attach|detach|insert|update|delete|drop|alter|create|replace|vacuum|reindex)\b", re.I
)


def screen_sql(text: str) -> str:
    """Allow one read-only statement. The connection is read-only too; this gives a clear error."""
    cleaned = re.sub(r"--[^\n]*", "", text)
    cleaned = re.sub(r"/\*.*?\*/", "", cleaned, flags=re.S).strip().rstrip(";").strip()
    if not cleaned:
        raise QueryRefused("Empty query.")
    if ";" in cleaned:
        raise QueryRefused("Send one statement at a time.")
    if not cleaned.lower().startswith(READ_ONLY_PREFIXES):
        raise QueryRefused("Only SELECT / WITH / EXPLAIN statements are allowed; the store is read-only.")
    if FORBIDDEN.search(cleaned):
        raise QueryRefused("The statement contains a write or schema keyword; the store is read-only.")
    return cleaned


class SQLiteStore:
    kind = "sqlite"
    query_language = "SQL (SQLite dialect)"

    def __init__(self, path: Path, *, dataset: str, timeout_s: float = 60.0):
        self.path = Path(path)
        if not self.path.exists():
            raise FileNotFoundError(f"SQLite database not found: {self.path}")
        self.dataset = dataset
        self.id = f"sqlite:{dataset}"
        self.timeout_s = timeout_s
        self._local = threading.local()  # one read-only connection per thread; no shared lock
        self._lock = threading.Lock()  # kept for the few schema reads that touch shared state
        self.conn  # noqa: B018 - open the main thread's connection eagerly to fail fast

    @property
    def conn(self) -> sqlite3.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(f"file:{self.path}?mode=ro&immutable=1", uri=True)
            conn.execute("PRAGMA query_only = 1")
            self._local.deadline = 0.0
            conn.set_progress_handler(self._check_deadline, 100_000)
            self._local.conn = conn
        return conn

    @property
    def _deadline(self) -> float:
        return getattr(self._local, "deadline", 0.0)

    @_deadline.setter
    def _deadline(self, value: float) -> None:
        self._local.deadline = value

    def _check_deadline(self) -> int:
        return 1 if time.monotonic() > self._deadline else 0

    def _run(self, sql: str):
        """Execute internal SQL with the same time budget as agent queries."""
        self._deadline = time.monotonic() + self.timeout_s
        return self.conn.execute(sql)

    def close(self) -> None:
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            conn.close()
            self._local.conn = None

    def _table_names(self) -> list[str]:
        rows = self._run(
            "SELECT name FROM sqlite_master WHERE type IN ('table','view') "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
        return [r[0] for r in rows]

    def list_tables(self) -> list[TableInfo]:
        return self._list_tables_locked()

    def _list_tables_locked(self) -> list[TableInfo]:
        out = []
        for name in self._table_names():
            count = self._run(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
            cols = [
                ColumnInfo(name=r[1], type=r[2] or "ANY") for r in self._run(f'PRAGMA table_info("{name}")')
            ]
            out.append(TableInfo(name=name, row_count=count, columns=cols))
        return out

    def describe_table(self, name: str) -> TableInfo:
        return self._describe_locked(name)

    def _describe_locked(self, name: str) -> TableInfo:
        if name not in self._table_names():
            raise QueryRefused(f"No table named {name!r}. Tables: {', '.join(self._table_names())}")
        count = self._run(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
        cols = [(r[1], r[2] or "ANY") for r in self._run(f'PRAGMA table_info("{name}")')]
        null_expr = ", ".join(f'SUM("{c}" IS NULL)' for c, _ in cols)
        nulls = self._run(f'SELECT {null_expr} FROM "{name}"').fetchone() if cols else ()
        columns = [
            ColumnInfo(name=c, type=t, nulls=int(n or 0)) for (c, t), n in zip(cols, nulls, strict=True)
        ]
        cur = self._run(f'SELECT * FROM "{name}" LIMIT 3')
        names = [d[0] for d in cur.description]
        sample = [dict(zip(names, (clip_cell(v) for v in row), strict=True)) for row in cur.fetchall()]
        return TableInfo(name=name, row_count=count, columns=columns, sample=sample)

    def query(self, text: str, *, max_rows: int = MAX_ROWS) -> QueryResult:
        sql = screen_sql(text)
        return self._query_locked(sql, max_rows)

    def _query_locked(self, sql: str, max_rows: int) -> QueryResult:
        self._deadline = time.monotonic() + self.timeout_s
        started = time.monotonic()
        try:
            cur = self.conn.execute(sql)
            rows = cur.fetchmany(max_rows + 1)
        except sqlite3.OperationalError as error:
            if "interrupted" in str(error):
                raise QueryRefused(f"Query exceeded {self.timeout_s:.0f}s and was stopped.") from error
            raise QueryRefused(f"SQLite error: {error}") from error
        elapsed = int((time.monotonic() - started) * 1000)
        columns = [d[0] for d in cur.description] if cur.description else []
        truncated = len(rows) > max_rows
        rows = rows[:max_rows]
        return QueryResult(
            columns=columns,
            rows=[[clip_cell(v) for v in row] for row in rows],
            row_count=len(rows),
            truncated=truncated,
            elapsed_ms=elapsed,
            note=f"Only the first {max_rows} rows are shown; aggregate or add LIMIT/OFFSET."
            if truncated
            else None,
        )

    def python_mounts(self) -> dict[str, str]:
        return {str(self.path): str(self.path)}

    def sandbox_network(self) -> str | None:
        return None

    def python_environment(self) -> dict[str, str]:
        return {
            "BACKINTEL_SQLITE_PATH": str(self.path),
            "BACKINTEL_STORE_NOTE": (
                "A read-only SQLite database is at the path in BACKINTEL_SQLITE_PATH. Open it "
                "with sqlite3.connect(f'file:{path}?mode=ro', uri=True) or "
                "polars.read_database_uri(query, f'sqlite://{path}')."
            ),
        }
