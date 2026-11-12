"""FerretDB 2.7 through MongoDB's wire protocol and aggregation pipeline (not PostgreSQL SQL)."""

from __future__ import annotations

import json
import re
import subprocess
import time
from pathlib import Path

import polars as pl
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from backintel.stores.base import MAX_ROWS, ColumnInfo, QueryRefused, QueryResult, TableInfo, clip_cell

PASSWORD = "backintel-local-analyst"
ALLOWED_STAGES = {
    "$match",
    "$group",
    "$project",
    "$sort",
    "$limit",
    "$skip",
    "$count",
    "$unwind",
    "$lookup",
    "$addFields",
    "$set",
    "$unset",
    "$replaceRoot",
    "$replaceWith",
    "$facet",
}
BLOCKED = {"$out", "$merge", "$function", "$accumulator", "$where"}


def screen_query(text: str) -> tuple[str, list[dict]]:
    try:
        request = json.loads(text)
        name, pipeline = request["collection"], request["pipeline"]
        if not re.fullmatch(r"[a-z0-9_]+", name) or not isinstance(pipeline, list):
            raise ValueError("invalid collection or pipeline")

        def check(value):
            if isinstance(value, dict):
                if BLOCKED.intersection(value):
                    raise ValueError("write and JavaScript operators are disabled")
                for nested in value.values():
                    check(nested)
            elif isinstance(value, list):
                for nested in value:
                    check(nested)

        check(pipeline)
        if any(
            not isinstance(stage, dict) or len(stage) != 1 or next(iter(stage)) not in ALLOWED_STAGES
            for stage in pipeline
        ):
            raise ValueError("unsupported or non-read-only aggregation stage")
        return name, pipeline
    except (ValueError, KeyError, TypeError) as error:
        raise QueryRefused(
            'Use JSON {"collection":"name", "pipeline":[{"$match":...}, ...]}. ' + str(error)
        ) from error


def client(*, loader: bool = False, host: str = "127.0.0.1", port: int = 27018) -> MongoClient:
    user, password = ("loader", "backintel-local-loader") if loader else ("analyst", PASSWORD)
    return MongoClient(
        host,
        port,
        username=user,
        password=password,
        authSource="admin",
        serverSelectionTimeoutMS=10000,
        socketTimeoutMS=65000,
    )


def set_readonly(enabled: bool) -> None:
    """FerretDB 2.7 does not enforce MongoDB read roles. Freeze its backend instead."""
    subprocess.run(
        [
            "docker",
            "exec",
            "-e",
            "PGOPTIONS=-c default_transaction_read_only=off",
            "backintel-v2-documentdb-1",
            "psql",
            "-U",
            "loader",
            "-d",
            "postgres",
            "-c",
            f"ALTER ROLE loader SET default_transaction_read_only={'on' if enabled else 'off'}",
        ],
        check=True,
        capture_output=True,
    )
    subprocess.run(["docker", "restart", "backintel-ferretdb"], check=True, capture_output=True)
    for _ in range(30):
        try:
            with client(loader=True) as conn:
                conn.admin.command("ping")
            return
        except PyMongoError:
            time.sleep(1)
    raise RuntimeError("FerretDB did not become ready after changing read-only mode")


def load_dataset(dataset: str, canonical_dir: Path, *, force: bool = False) -> None:
    # Loading and evaluation are distinct phases. Never build stores during an experiment.
    set_readonly(False)
    try:
        _load_dataset(dataset, canonical_dir, force=force)
    finally:
        set_readonly(True)


def _load_dataset(dataset: str, canonical_dir: Path, *, force: bool = False) -> None:
    with client(loader=True) as conn:
        db = conn[dataset]
        for path in sorted(canonical_dir.glob("*.parquet")):
            if path.stem == "geolocation":
                continue
            frame = pl.read_parquet(path)
            if path.stem in db.list_collection_names():
                if not force and db[path.stem].count_documents({}) == frame.height:
                    continue
                db.drop_collection(path.stem)
            if "source_sheet" in frame.columns:
                frame = frame.drop("source_sheet")
            for name, dtype in frame.schema.items():
                if dtype.is_temporal():
                    frame = frame.with_columns(pl.col(name).dt.strftime("%Y-%m-%d %H:%M:%S"))
            for batch in frame.iter_slices(2000):
                db[path.stem].insert_many(batch.to_dicts(), ordered=False)
            if db[path.stem].count_documents({}) != frame.height:
                raise RuntimeError(f"Incomplete load of {dataset}.{path.stem}")
            for name in frame.columns:
                if name.endswith("_id") or name in ("invoice", "stock_code"):
                    db[path.stem].create_index(name)
            print(f"ferretdb:{dataset}.{path.stem}: {frame.height}", flush=True)
        # FerretDB 2.7 accepts role declarations but does not enforce the MongoDB read role.
        # The backend is frozen by load_dataset() before these credentials reach the analyst.
        roles = [
            {"role": "read", "db": name}
            for name in conn.list_database_names()
            if name not in ("admin", "config", "local")
        ]
        existing = conn.admin.command("usersInfo", "analyst")
        if not existing.get("users"):
            conn.admin.command("createUser", "analyst", pwd=PASSWORD, roles=roles)


class FerretDBStore:
    kind = "ferretdb"
    query_language = (
        "MongoDB aggregation JSON via FerretDB 2.7. Use run_query with "
        '{"collection":"name","pipeline":[...]} (no SQL). Dates are ISO strings.'
    )

    def __init__(self, dataset: str):
        self.dataset, self.id = dataset, f"ferretdb:{dataset}"
        self.client = client()
        self.db = self.client[dataset]

    def query(self, text: str, *, max_rows: int = MAX_ROWS) -> QueryResult:
        name, pipeline = screen_query(text)
        started = time.monotonic()
        try:
            docs = list(self.db[name].aggregate([*pipeline, {"$limit": max_rows + 1}], maxTimeMS=60000))
        except PyMongoError as error:
            raise QueryRefused(f"FerretDB error: {str(error)[:600]}") from error
        columns = list(dict.fromkeys(k for doc in docs for k in doc))
        return QueryResult(
            columns,
            [[clip_cell(doc.get(k)) for k in columns] for doc in docs[:max_rows]],
            min(len(docs), max_rows),
            len(docs) > max_rows,
            int((time.monotonic() - started) * 1000),
        )

    def list_tables(self) -> list[TableInfo]:
        return [self.describe_table(name) for name in sorted(self.db.list_collection_names())]

    def describe_table(self, name: str) -> TableInfo:
        if name not in self.db.list_collection_names():
            raise QueryRefused(f"Unknown collection {name}")
        sample = list(self.db[name].find({}, {"_id": 0}).limit(3))
        columns = {key: type(value).__name__ for doc in sample for key, value in doc.items()}
        return TableInfo(
            name, self.db[name].count_documents({}), [ColumnInfo(k, v) for k, v in columns.items()], sample
        )

    def python_environment(self) -> dict[str, str]:
        uri = f"mongodb://analyst:{PASSWORD}@backintel-ferretdb:27017/?authSource=admin"
        return {
            "BACKINTEL_MONGO_URI": uri,
            "BACKINTEL_MONGO_DB": self.dataset,
            "BACKINTEL_STORE_NOTE": "Use pymongo.MongoClient(os.environ['BACKINTEL_MONGO_URI'])"
            "[os.environ['BACKINTEL_MONGO_DB']]. Collections support find() and aggregate(). "
            "The PostgreSQL backend is in read-only mode. For joins or statistics, fetch required fields "
            "through the MongoDB wire protocol and combine in polars/pandas. No local data files.",
        }

    def python_mounts(self) -> dict[str, str]:
        return {}

    def sandbox_network(self) -> str:
        return "backintel-net"

    def close(self) -> None:
        self.client.close()
