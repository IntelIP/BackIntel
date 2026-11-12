import polars as pl
import pytest

from backintel.stores.base import QueryRefused
from backintel.stores.duckdb_lake import DuckDBLakeStore
from backintel.stores.duckdb_lake import screen_sql as duck_screen
from backintel.stores.files import FilesStore, export_csv_files
from backintel.stores.postgres import screen_sql as pg_screen


@pytest.fixture
def canonical(tmp_path):
    frame = pl.DataFrame(
        {"country": ["UK", "UK", "France"], "amount": [10.0, 5.5, 7.25], "customer_id": [1, None, 2]}
    )
    frame.write_parquet(tmp_path / "sales.parquet")
    pl.DataFrame({"a": [1]}).write_parquet(tmp_path / "geolocation.parquet")
    return tmp_path


def test_duckdb_lake_queries_parquet_read_only(canonical):
    store = DuckDBLakeStore(canonical, dataset="t")
    try:
        assert [t.name for t in store.list_tables()] == ["sales"]  # geolocation excluded
        info = store.describe_table("sales")
        assert {c.name: c.nulls for c in info.columns} == {"country": 0, "amount": 0, "customer_id": 1}
        result = store.query("SELECT country, SUM(amount) AS total FROM sales GROUP BY 1 ORDER BY 2 DESC")
        assert result.rows[0] == ["UK", 15.5]
        for bad in (
            "COPY sales TO 'x.csv'",
            "SELECT * FROM read_csv('/etc/passwd')",
            "SET memory_limit='1GB'",
            "CREATE TABLE x AS SELECT 1",
            "INSTALL httpfs",
        ):
            with pytest.raises(QueryRefused):
                store.query(bad)
    finally:
        store.close()


def test_screening_rules_for_duckdb_and_postgres():
    assert duck_screen("WITH x AS (SELECT 1) SELECT * FROM x")
    assert pg_screen("SELECT 1")
    for bad in ("DELETE FROM t", "SELECT 1; SELECT 2", "SET search_path TO x", "COPY t TO STDOUT"):
        with pytest.raises(QueryRefused):
            pg_screen(bad)
        with pytest.raises(QueryRefused):
            duck_screen(bad)


def test_files_store_lists_and_describes_but_has_no_query(canonical, tmp_path):
    out = export_csv_files("t", canonical, tmp_path / "files")
    store = FilesStore(out, dataset="t")
    tables = store.list_tables()
    assert [(t.name, t.row_count) for t in tables] == [("sales.csv", 3)]
    info = store.describe_table("sales.csv")
    assert {c.name: c.nulls for c in info.columns} == {"country": 0, "amount": 0, "customer_id": 1}
    with pytest.raises(NotImplementedError):
        store.query("SELECT 1")
    assert "BACKINTEL_FILES_DIR" in store.python_environment()
    assert store.python_mounts() == {str(out): str(out)}


def test_raw_json_uses_the_same_logical_rows(canonical, tmp_path):
    out = export_csv_files("t", canonical, tmp_path / "mixed", mixed=True)
    # File order is not a semantic requirement; explicitly exercise the JSON path.
    frame = pl.read_parquet(canonical / "sales.parquet")
    frame.write_ndjson(out / "sales.jsonl")
    (out / "sales.csv").unlink(missing_ok=True)
    store = FilesStore(out, dataset="t")
    assert store.describe_table("sales.jsonl").row_count == 3
    assert store._frame("sales.jsonl").select(pl.col("amount").sum()).collect().item() == 22.75
