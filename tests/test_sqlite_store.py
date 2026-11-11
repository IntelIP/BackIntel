import sqlite3

import pytest

from backintel.bench.scoring import evidence_reproduces
from backintel.contracts import AnalystAnswer, Evidence, Scenario, Tolerance
from backintel.sandbox import PythonSandbox
from backintel.stores.base import QueryRefused
from backintel.stores.sqlite import SQLiteStore, screen_sql


@pytest.fixture
def store(tmp_path):
    path = tmp_path / "t.sqlite"
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE sales (country TEXT, amount REAL, customer_id INTEGER)")
    conn.executemany(
        "INSERT INTO sales VALUES (?, ?, ?)", [("UK", 10.0, 1), ("UK", 5.5, None), ("France", 7.25, 2)]
    )
    conn.commit()
    conn.close()
    s = SQLiteStore(path, dataset="t")
    yield s
    s.close()


def test_screen_allows_reads_and_refuses_writes():
    assert screen_sql("  SELECT 1; ").startswith("SELECT")
    assert screen_sql("WITH x AS (SELECT 1) SELECT * FROM x")
    for bad in ("DELETE FROM sales", "SELECT 1; SELECT 2", "ATTACH 'a' AS b", "PRAGMA writable_schema=1", ""):
        with pytest.raises(QueryRefused):
            screen_sql(bad)


def test_store_is_read_only_even_if_screening_is_bypassed(store):
    with pytest.raises(sqlite3.OperationalError):
        store.conn.execute("DELETE FROM sales")


def test_describe_and_query(store):
    tables = store.list_tables()
    assert [(t.name, t.row_count) for t in tables] == [("sales", 3)]
    info = store.describe_table("sales")
    assert {c.name: c.nulls for c in info.columns} == {"country": 0, "amount": 0, "customer_id": 1}
    result = store.query("SELECT country, SUM(amount) total FROM sales GROUP BY 1 ORDER BY 2 DESC")
    assert result.columns == ["country", "total"] and result.rows[0] == ["UK", 15.5]
    with pytest.raises(QueryRefused):
        store.describe_table("nope")


def test_evidence_reproduces_checks_cited_queries(store):
    scenario = Scenario(
        id="s",
        dataset="t",
        level=1,
        question="q",
        answer_type="number",
        expected=15.5,
        tolerance=Tolerance(rel=0.001),
    )
    good = AnalystAnswer(
        status="answered",
        answer_type="number",
        value=15.5,
        method="m",
        evidence=[Evidence(kind="sql", code="SELECT SUM(amount) FROM sales WHERE country='UK'")],
    )
    bad = AnalystAnswer(
        status="answered",
        answer_type="number",
        value=15.5,
        method="m",
        evidence=[Evidence(kind="sql", code="SELECT SUM(amount) FROM sales WHERE country='France'")],
    )
    sandbox = PythonSandbox("subprocess")
    assert evidence_reproduces(scenario, good, store, sandbox)["score"] == 1.0
    assert evidence_reproduces(scenario, bad, store, sandbox)["score"] == 0.0
    declined = AnalystAnswer(status="cannot_answer", method="m", reason="r")
    assert evidence_reproduces(scenario, declined, store, sandbox)["score"] is None


def test_clip_cell_converts_decimals_and_dates():
    from datetime import datetime
    from decimal import Decimal

    from backintel.stores.base import clip_cell

    assert clip_cell(Decimal("12.50")) == 12.5
    assert clip_cell(datetime(2018, 5, 1, 12, 0)) == "2018-05-01T12:00:00"
    assert clip_cell("x" * 300).endswith("…") and len(clip_cell("x" * 300)) == 200
