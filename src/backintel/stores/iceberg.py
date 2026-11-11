"""Iceberg metadata/manifests and Parquet data on local Garage S3, queried by DuckDB."""

from __future__ import annotations

import json
import re
import subprocess

import duckdb
import polars as pl

from backintel.settings import Settings
from backintel.stores.duckdb_lake import DuckDBLakeStore

BUCKET = "backintel"


def garage(*args: str) -> str:
    return subprocess.run(
        ["docker", "exec", "backintel-garage", "/garage", *args], check=True, capture_output=True, text=True
    ).stdout


def initialize(settings: Settings) -> dict:
    path = settings.stores_dir / "garage" / "keys.json"
    if path.exists():
        return json.loads(path.read_text())
    node = garage("node", "id", "-q").strip().split("@")[0]
    garage("layout", "assign", "-z", "local", "-c", "1G", node)
    garage("layout", "apply", "--version", "1")
    garage("bucket", "create", BUCKET)
    keys = {}
    for role in ("loader", "analyst"):
        result = garage("key", "create", f"backintel-{role}")
        key = re.search(r"Key ID:\s*(\S+)", result).group(1)
        secret = re.search(r"Secret key:\s*(\S+)", result).group(1)
        keys[role] = {"key": key, "secret": secret}
        args = ["bucket", "allow", "--read"]
        if role == "loader":
            args += ["--write", "--owner"]
        garage(*args, BUCKET, "--key", key)
    path.write_text(json.dumps(keys))
    path.chmod(0o600)
    return keys


def load_dataset(dataset: str, settings: Settings, *, force: bool = False) -> None:
    from pyiceberg.catalog.sql import SqlCatalog

    keys = initialize(settings)
    root = settings.stores_dir / "iceberg"
    root.mkdir(parents=True, exist_ok=True)
    catalog = SqlCatalog(
        "backintel",
        uri=f"sqlite:///{root / 'catalog.db'}",
        warehouse=f"s3://{BUCKET}/warehouse",
        **{
            "s3.endpoint": "http://127.0.0.1:13900",
            "s3.access-key-id": keys["loader"]["key"],
            "s3.secret-access-key": keys["loader"]["secret"],
            "s3.region": "garage",
            "s3.force-virtual-addressing": "false",
        },
    )
    catalog.create_namespace_if_not_exists(dataset)
    tables = {}
    for path in sorted((settings.canonical_dir / dataset).glob("*.parquet")):
        if path.stem == "geolocation":
            continue
        name = (dataset, path.stem)
        if catalog.table_exists(name) and not force:
            table = catalog.load_table(name)
        else:
            if catalog.table_exists(name):
                catalog.drop_table(name)
            frame = pl.read_parquet(path)
            if "source_sheet" in frame.columns:
                frame = frame.drop("source_sheet")
            arrow = frame.to_arrow()
            table = catalog.create_table(name, schema=arrow.schema)
            table.append(arrow)
        tables[path.stem] = table.metadata_location
        print(
            f"lake-iceberg:{dataset}.{path.stem}: snapshot {table.current_snapshot().snapshot_id}", flush=True
        )
    manifest = root / f"{dataset}.json"
    manifest.write_text(json.dumps({"tables": tables, "credentials": keys["analyst"]}, indent=2))
    manifest.chmod(0o600)


def connection(tables: dict[str, str], credentials: dict, endpoint: str) -> duckdb.DuckDBPyConnection:
    conn = duckdb.connect()
    for extension in ("httpfs", "iceberg"):
        conn.execute(f"LOAD {extension}")  # installed once by the setup command / sandbox image
    conn.execute("SET threads=2")
    conn.execute("SET memory_limit='512MB'")
    # Credentials are read-only at Garage; neither SQL nor sandbox Python can overwrite objects.
    conn.execute(
        "CREATE SECRET garage (TYPE S3, KEY_ID ?, SECRET ?, REGION 'garage', "
        "ENDPOINT ?, USE_SSL false, URL_STYLE 'path')",
        [credentials["key"], credentials["secret"], endpoint],
    )
    for name, metadata in tables.items():
        conn.execute(f"CREATE VIEW \"{name}\" AS SELECT * FROM iceberg_scan('{metadata}')")
    conn.execute("SET allowed_directories=['s3://backintel/']")
    conn.execute("SET enable_external_access=false")
    conn.execute("SET lock_configuration=true")
    return conn


class IcebergStore(DuckDBLakeStore):
    kind = "lake-iceberg"
    query_language = "SQL (DuckDB 2.0 dialect) over Apache Iceberg on Garage S3"

    def __init__(self, dataset: str, settings: Settings):
        import threading

        manifest = json.loads((settings.stores_dir / "iceberg" / f"{dataset}.json").read_text())
        self.dataset, self.id, self.timeout_s = dataset, f"lake-iceberg:{dataset}", 60.0
        self.tables = manifest["tables"]
        self.credentials = manifest["credentials"]
        self._lock = threading.Lock()
        self.conn = connection(self.tables, self.credentials, "127.0.0.1:13900")

    def python_mounts(self) -> dict[str, str]:
        return {}

    def sandbox_network(self) -> str:
        return "backintel-net"

    def python_environment(self) -> dict[str, str]:
        return {
            "BACKINTEL_ICEBERG_TABLES": json.dumps(self.tables),
            "BACKINTEL_S3_KEY": self.credentials["key"],
            "BACKINTEL_S3_SECRET": self.credentials["secret"],
            "BACKINTEL_STORE_NOTE": "Use DuckDB to query the real Iceberg tables on Garage S3. "
            "Create duckdb.connect(), execute LOAD httpfs; LOAD iceberg. Then CREATE SECRET "
            "(TYPE S3, KEY_ID <BACKINTEL_S3_KEY>, SECRET <BACKINTEL_S3_SECRET>, REGION 'garage', "
            "ENDPOINT 'backintel-garage:3900', USE_SSL false, URL_STYLE 'path'). "
            "Metadata paths by table name are in json.loads(os.environ['BACKINTEL_ICEBERG_TABLES']); "
            "query SELECT * FROM iceberg_scan('<metadata path>'). No local Parquet files. "
            "The S3 key grants read-only access.",
        }
