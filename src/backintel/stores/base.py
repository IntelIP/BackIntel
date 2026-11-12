"""What the analyst needs from any store: schema, read-only queries, and a dialect note.

Every store exposes the same three operations so the same scenarios run against SQLite,
PostgreSQL, a document store, a lake, ClickHouse or raw files. Query results are bounded and
JSON-serialisable so that they can be cited as evidence and re-executed by the verifier.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Protocol

MAX_ROWS = 200
MAX_CELL_CHARS = 200
MAX_RESULT_CHARS = 20_000


class QueryRefused(Exception):
    """The query is not read-only or is otherwise not allowed."""


@dataclass
class QueryResult:
    columns: list[str]
    rows: list[list[Any]]
    row_count: int  # rows returned (after the cap)
    truncated: bool
    elapsed_ms: int
    note: str | None = None

    def to_dict(self) -> dict:
        return {
            "columns": self.columns,
            "rows": self.rows,
            "row_count": self.row_count,
            "truncated": self.truncated,
            "elapsed_ms": self.elapsed_ms,
            **({"note": self.note} if self.note else {}),
        }


@dataclass
class ColumnInfo:
    name: str
    type: str
    nulls: int | None = None


@dataclass
class TableInfo:
    name: str
    row_count: int
    columns: list[ColumnInfo] = field(default_factory=list)
    sample: list[dict[str, Any]] = field(default_factory=list)


class Store(Protocol):
    """A connected data store the analyst may read from."""

    id: str  # e.g. "sqlite:online_retail_ii"
    kind: str  # e.g. "sqlite"
    query_language: str  # e.g. "SQL (SQLite dialect)"

    def list_tables(self) -> list[TableInfo]: ...

    def describe_table(self, name: str) -> TableInfo: ...

    def query(self, text: str, *, max_rows: int = MAX_ROWS) -> QueryResult: ...

    def python_environment(self) -> dict[str, str]:
        """Environment variables and a usage note telling sandboxed Python how to reach the data."""
        ...

    def python_mounts(self) -> dict[str, str]:
        """Host paths the sandbox needs, mounted read-only at the same path inside."""
        ...

    def sandbox_network(self) -> str | None:
        """Docker network the sandbox must join to reach the store, or None for no network."""
        ...

    def close(self) -> None: ...


def clip_cell(value: Any) -> Any:
    if isinstance(value, Decimal):  # PostgreSQL returns numeric/sum/avg as Decimal
        return float(value)
    if isinstance(value, bytes):
        return f"<{len(value)} bytes>"
    if isinstance(value, str) and len(value) > MAX_CELL_CHARS:
        return value[: MAX_CELL_CHARS - 1] + "…"
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value
