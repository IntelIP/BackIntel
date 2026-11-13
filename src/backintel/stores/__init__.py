"""Store registry: open a store by id such as `sqlite:online_retail_ii`.

Kinds: `sqlite`, `lake-parquet` (DuckDB over Parquet), `files` (raw CSV, Python only),
`postgres` (local container). Each exposes the same protocol, so the same scenarios run on all.
"""

from __future__ import annotations

from backintel.settings import Settings
from backintel.stores.base import QueryRefused, QueryResult, Store, TableInfo

KINDS = (
    "sqlite",
    "lake-parquet",
    "files",
    "files-mixed",
    "package",
    "postgres",
    "multi",
    "clickhouse",
    "ferretdb",
    "lake-iceberg",
)


def open_store(store_id: str, settings: Settings) -> Store:
    kind, _, dataset = store_id.partition(":")
    if not dataset:
        raise ValueError("Store ids look like '<kind>:<dataset>', e.g. 'sqlite:online_retail_ii'.")
    if kind == "sqlite":
        from backintel.stores.sqlite import SQLiteStore

        return SQLiteStore(settings.stores_dir / "sqlite" / f"{dataset}.sqlite", dataset=dataset)
    if kind == "package":
        from backintel.stores.package import PackageStore, safe_name

        safe_name(dataset)
        return PackageStore(settings.stores_dir / "package" / dataset, dataset=dataset)
    if kind == "lake-parquet":
        from backintel.bench.build_stores import build_parquet
        from backintel.bench.datasets import SPLITS
        from backintel.stores.duckdb_lake import DuckDBLakeStore

        only = SPLITS[dataset][1] if dataset in SPLITS else None
        return DuckDBLakeStore(build_parquet(dataset, settings), dataset=dataset, only=only)
    if kind in ("files", "files-mixed"):
        from backintel.stores.files import FilesStore, export_csv_files

        directory = settings.stores_dir / kind / dataset
        if kind == "files-mixed":
            export_csv_files(dataset, settings.canonical_dir / dataset, directory, mixed=True)
        store = FilesStore(directory, dataset=dataset)
        store.id = f"{kind}:{dataset}"
        return store
    if kind == "postgres":
        from backintel.stores.postgres import PostgresStore

        return PostgresStore(dataset)
    if kind == "clickhouse":
        from backintel.stores.clickhouse import ClickHouseStore

        return ClickHouseStore(dataset)
    if kind == "ferretdb":
        from backintel.stores.ferretdb import FerretDBStore

        return FerretDBStore(dataset)
    if kind == "lake-iceberg":
        from backintel.stores.iceberg import IcebergStore

        return IcebergStore(dataset, settings)
    if kind == "multi":
        from backintel.stores.multi import MultiStore

        return MultiStore([open_store(part, settings) for part in dataset.split("+")], settings=settings)
    raise ValueError(f"Unknown store kind {kind!r}. Known: {', '.join(KINDS)}")


__all__ = ["KINDS", "QueryRefused", "QueryResult", "Store", "TableInfo", "open_store"]
