"""Native ClickHouse HTTP queries with a SELECT-only role; no Parquet fallback."""

from __future__ import annotations

import re
import time
from pathlib import Path

import httpx
import polars as pl

from backintel.stores.base import MAX_ROWS, ColumnInfo, QueryRefused, QueryResult, TableInfo, clip_cell
from backintel.stores.postgres import screen_sql as screen_postgres

URL = "http://127.0.0.1:18123"
PASSWORD = "backintel-local-analyst"


def screen_sql(text: str) -> str:
    sql = screen_postgres(text)
    if re.search(r"\b(url|remote|remoteSecure|s3|file|mysql|postgresql|executable|input)\s*\(", sql, re.I):
        raise QueryRefused("External table functions are disabled; query the loaded tables.")
    if re.search(r"\b(format|into\s+outfile|settings)\b", sql, re.I):
        raise QueryRefused("Result format and settings are controlled by the runner.")
    return sql


def request(sql: str, dataset: str = "default", *, loader: bool = False, data: bytes | None = None):
    response = httpx.post(
        URL,
        params={"database": dataset, "query": sql},
        content=data,
        auth=("loader", "backintel-local-loader") if loader else ("analyst", PASSWORD),
        timeout=120,
    )
    response.raise_for_status()
    return response


def load_dataset(dataset: str, canonical_dir: Path, *, force: bool = False) -> None:
    request(f"CREATE DATABASE IF NOT EXISTS `{dataset}`", loader=True)
    for path in sorted(canonical_dir.glob("*.parquet")):
        if path.stem == "geolocation":
            continue
        if not force and request(f"EXISTS TABLE `{path.stem}`", dataset, loader=True).text.strip() == "1":
            continue
        frame = pl.read_parquet(path)
        if "source_sheet" in frame.columns:
            frame = frame.drop("source_sheet")
        columns = []
        for name, dtype in frame.schema.items():
            kind = "Float64" if dtype.is_float() else "Int64" if dtype.is_integer() else "String"
            if dtype.is_temporal():
                frame = frame.with_columns(pl.col(name).dt.strftime("%Y-%m-%d %H:%M:%S"))
            columns.append(f"`{name}` Nullable({kind})")
        if force:
            request(f"DROP TABLE IF EXISTS `{path.stem}`", dataset, loader=True)
        request(
            f"CREATE TABLE `{path.stem}` ({', '.join(columns)}) ENGINE=MergeTree ORDER BY tuple()",
            dataset,
            loader=True,
        )
        request(
            f"INSERT INTO `{path.stem}` FORMAT CSV",
            dataset,
            loader=True,
            data=frame.write_csv(include_header=False, null_value="\\N").encode(),
        )
    request(f"CREATE USER IF NOT EXISTS analyst IDENTIFIED BY '{PASSWORD}'", loader=True)
    request(f"GRANT SELECT ON `{dataset}`.* TO analyst", loader=True)
    request(
        "ALTER USER analyst SETTINGS readonly=1, max_threads=2, max_execution_time=60, "
        "max_memory_usage=700000000, output_format_json_quote_64bit_integers=0",
        loader=True,
    )


class ClickHouseStore:
    kind = "clickhouse"
    query_language = "SQL (ClickHouse 25.8 dialect; date fields are ISO strings)"

    def __init__(self, dataset: str):
        if not re.fullmatch(r"[a-z0-9_]+", dataset):
            raise ValueError("Invalid dataset name")
        self.dataset, self.id = dataset, f"clickhouse:{dataset}"

    def query(self, text: str, *, max_rows: int = MAX_ROWS) -> QueryResult:
        sql = screen_sql(text)
        started = time.monotonic()
        try:
            result = request(f"SELECT * FROM ({sql}) LIMIT {max_rows + 1} FORMAT JSON", self.dataset).json()
        except (httpx.HTTPError, ValueError) as error:
            detail = error.response.text[:600] if isinstance(error, httpx.HTTPStatusError) else str(error)
            raise QueryRefused(f"ClickHouse error: {detail}") from error
        columns = [c["name"] for c in result["meta"]]
        data = result["data"]
        return QueryResult(
            columns,
            [[clip_cell(row[c]) for c in columns] for row in data[:max_rows]],
            min(len(data), max_rows),
            len(data) > max_rows,
            int((time.monotonic() - started) * 1000),
        )

    def list_tables(self) -> list[TableInfo]:
        names = self.query(f"SELECT name FROM system.tables WHERE database='{self.dataset}' ORDER BY name")
        return [self.describe_table(row[0]) for row in names.rows]

    def describe_table(self, name: str) -> TableInfo:
        if not re.fullmatch(r"[a-z0-9_]+", name):
            raise QueryRefused("Invalid table name")
        meta = self.query(
            f"SELECT name, type FROM system.columns WHERE database='{self.dataset}' AND table='{name}' "
            "ORDER BY position"
        )
        if not meta.rows:
            raise QueryRefused(f"Unknown table {name}")
        count = int(self.query(f"SELECT count() FROM `{name}`").rows[0][0])
        sample = self.query(f"SELECT * FROM `{name}` LIMIT 3")
        return TableInfo(
            name,
            count,
            [ColumnInfo(*r) for r in meta.rows],
            [dict(zip(sample.columns, row, strict=True)) for row in sample.rows],
        )

    def python_environment(self) -> dict[str, str]:
        return {
            "BACKINTEL_CH_URL": f"http://backintel-clickhouse:8123/?database={self.dataset}",
            "BACKINTEL_CH_USER": "analyst",
            "BACKINTEL_CH_PASSWORD": PASSWORD,
            "BACKINTEL_STORE_NOTE": "Use clickhouse_connect.get_client(host='backintel-clickhouse', "
            f"port=8123, username='analyst', password='{PASSWORD}', database='{self.dataset}'). "
            "Use query(sql).result_rows; only SELECT is granted. Data is in ClickHouse, not local files.",
        }

    def python_mounts(self) -> dict[str, str]:
        return {}

    def sandbox_network(self) -> str:
        return "backintel-net"

    def close(self) -> None:
        pass
