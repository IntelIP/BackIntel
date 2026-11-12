"""Several stores behind one analyst: the cross-store level.

Table names are qualified as `<store id>.<table>` in listings. `query()` takes the store as a
leading directive `-- store: <id>` (the tools add it from their `store` argument), so a cited
query stays self-describing and re-executable. The sandbox receives the union of mounts and
environment variables and joins the one internal network any part needs.
"""

from __future__ import annotations

import re

from backintel.settings import Settings
from backintel.stores.base import MAX_ROWS, QueryRefused, QueryResult, Store, TableInfo

DIRECTIVE = re.compile(r"^\s*--\s*store:\s*(\S+)\s*\n", re.I)


class MultiStore:
    kind = "multi"

    def __init__(self, parts: list[Store], *, settings: Settings | None = None):
        if len(parts) < 2:
            raise ValueError("A multi store needs at least two parts.")
        self.parts: dict[str, Store] = {p.id: p for p in parts}
        self.id = "multi:" + "+".join(self.parts)
        self.query_language = "; ".join(f"{p.id}: {p.query_language}" for p in parts)

    def close(self) -> None:
        for part in self.parts.values():
            part.close()

    def resolve(self, store_id: str | None) -> Store:
        if store_id is None:
            raise QueryRefused(f"Name the store: one of {', '.join(self.parts)}.")
        if store_id not in self.parts:
            raise QueryRefused(f"Unknown store {store_id!r}; connected stores: {', '.join(self.parts)}.")
        return self.parts[store_id]

    def list_tables(self) -> list[TableInfo]:
        out = []
        for store_id, part in self.parts.items():
            for table in part.list_tables():
                table.name = f"{store_id}.{table.name}"
                out.append(table)
        return out

    def describe_table(self, name: str) -> TableInfo:
        store_id, _, table = name.rpartition(".")
        if not store_id:
            raise QueryRefused(f"Qualify the table as <store>.<table>; stores: {', '.join(self.parts)}.")
        info = self.resolve(store_id).describe_table(table)
        info.name = name
        return info

    def query(self, text: str, *, max_rows: int = MAX_ROWS) -> QueryResult:
        match = DIRECTIVE.match(text)
        if not match:
            raise QueryRefused(
                "Start the query with a directive line `-- store: <id>` naming the store it runs on; "
                f"stores: {', '.join(self.parts)}."
            )
        return self.resolve(match.group(1)).query(text[match.end() :], max_rows=max_rows)

    def python_mounts(self) -> dict[str, str]:
        mounts: dict[str, str] = {}
        for part in self.parts.values():
            mounts.update(part.python_mounts())
        return mounts

    def sandbox_network(self) -> str | None:
        networks = {part.sandbox_network() for part in self.parts.values()} - {None}
        if len(networks) > 1:
            raise ValueError("Parts need different sandbox networks; a sandbox can join only one.")
        return next(iter(networks), None)

    def python_environment(self) -> dict[str, str]:
        env: dict[str, str] = {}
        notes = []
        for store_id, part in self.parts.items():
            part_env = part.python_environment()
            notes.append(f"[{store_id}] " + part_env.pop("BACKINTEL_STORE_NOTE", ""))
            env.update(part_env)
        env["BACKINTEL_STORE_NOTE"] = "Several stores are connected; join across them in Python. " + " ".join(
            notes
        )
        return env
