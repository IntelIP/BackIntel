"""Level 7, scale: TPC-H data generated with DuckDB's `tpch` extension and queried as a Parquet lake.

TPC-H is synthetic and freely generatable, which avoids the licence problems of the large public
event datasets (REES46 on Kaggle carries no open licence). Scale factor 1 is about 8.7 million rows
(6 million line items); larger factors are meant for the Windows desktop, not this laptop. Results
are labelled with their scale factor.
"""

from __future__ import annotations

from pathlib import Path

import polars as pl

from backintel.bench.oracle import EXACT, MONEY, RATIO, Frames, Spec

TABLES = ("lineitem", "orders", "customer", "part", "supplier", "partsupp", "nation", "region")


def generate(out_dir: Path, *, scale_factor: float) -> dict[str, int]:
    """Generate TPC-H at `scale_factor` into Parquet files (one per table) with DuckDB."""
    import duckdb

    out_dir.mkdir(parents=True, exist_ok=True)
    # Generate on disk with a bounded memory budget: this laptop is memory-constrained.
    db_path = out_dir / "_generate.duckdb"
    conn = duckdb.connect(database=str(db_path))
    conn.execute("SET memory_limit = '1GB'; SET threads = 2; INSTALL tpch; LOAD tpch;")
    conn.execute(f"CALL dbgen(sf = {scale_factor})")
    counts = {}
    for table in TABLES:
        conn.execute(f"COPY {table} TO '{out_dir / (table + '.parquet')}' (FORMAT parquet)")
        counts[table] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    conn.close()
    db_path.unlink(missing_ok=True)
    for leftover in out_dir.glob("_generate.duckdb.*"):
        leftover.unlink()
    return counts


def _lazy(f: Frames, name: str) -> pl.LazyFrame:
    frame = f[name]
    return frame.lazy() if isinstance(frame, pl.DataFrame) else frame


def revenue_1995(f):
    return float(
        _lazy(f, "lineitem")
        .filter((pl.col("l_shipdate") >= pl.date(1995, 1, 1)) & (pl.col("l_shipdate") < pl.date(1996, 1, 1)))
        .select((pl.col("l_extendedprice") * (1 - pl.col("l_discount"))).sum())
        .collect()
        .item()
    )


def top5_nations_1996(f):
    frame = (
        _lazy(f, "orders")
        .filter(
            (pl.col("o_orderdate") >= pl.date(1996, 1, 1)) & (pl.col("o_orderdate") < pl.date(1997, 1, 1))
        )
        .join(
            _lazy(f, "lineitem").select("l_orderkey", "l_extendedprice", "l_discount"),
            left_on="o_orderkey",
            right_on="l_orderkey",
        )
        .join(
            _lazy(f, "customer").select("c_custkey", "c_nationkey"), left_on="o_custkey", right_on="c_custkey"
        )
        .join(
            _lazy(f, "nation").select("n_nationkey", "n_name"), left_on="c_nationkey", right_on="n_nationkey"
        )
        .group_by("n_name")
        .agg((pl.col("l_extendedprice") * (1 - pl.col("l_discount"))).sum().alias("revenue"))
        .sort(["revenue", "n_name"], descending=[True, False])
        .collect()
    )
    return [str(x).strip() for x in frame["n_name"].head(5).to_list()]


def customers_1997(f):
    return float(
        _lazy(f, "orders")
        .filter(
            (pl.col("o_orderdate") >= pl.date(1997, 1, 1)) & (pl.col("o_orderdate") < pl.date(1998, 1, 1))
        )
        .select(pl.col("o_custkey").n_unique())
        .collect()
        .item()
    )


def avg_order_by_segment_1994(f):
    return (
        _lazy(f, "orders")
        .filter(
            (pl.col("o_orderdate") >= pl.date(1994, 1, 1)) & (pl.col("o_orderdate") < pl.date(1995, 1, 1))
        )
        .join(
            _lazy(f, "customer").select("c_custkey", "c_mktsegment"),
            left_on="o_custkey",
            right_on="c_custkey",
        )
        .group_by("c_mktsegment")
        .agg(pl.col("o_totalprice").mean().alias("avg_totalprice"))
        .sort("c_mktsegment")
        .collect()
        .with_columns(pl.col("c_mktsegment").cast(pl.Utf8).str.strip_chars())
    )


def top3_brands_q1_1995(f):
    frame = (
        _lazy(f, "lineitem")
        .filter((pl.col("l_shipdate") >= pl.date(1995, 1, 1)) & (pl.col("l_shipdate") < pl.date(1995, 4, 1)))
        .join(_lazy(f, "part").select("p_partkey", "p_brand"), left_on="l_partkey", right_on="p_partkey")
        .group_by("p_brand")
        .agg(pl.col("l_quantity").sum().alias("qty"))
        .sort(["qty", "p_brand"], descending=[True, False])
        .collect()
    )
    return [str(x).strip() for x in frame["p_brand"].head(3).to_list()]


def return_share_1994(f):
    # TPC-H marks returns only for items received before its fixed "current date" (1995-06-17),
    # so a later year would give a degenerate zero; 1994 is fully inside the returns window.
    frame = (
        _lazy(f, "lineitem")
        .filter((pl.col("l_shipdate") >= pl.date(1994, 1, 1)) & (pl.col("l_shipdate") < pl.date(1995, 1, 1)))
        .select((pl.col("l_returnflag") == "R").mean())
        .collect()
    )
    return float(frame.item())


SCENARIOS: list[Spec] = [
    Spec(
        "tpch-l7-01",
        7,
        "What was total revenue for line items shipped in calendar year 1995, where line "
        "revenue is extended price times (1 minus discount)?",
        "number",
        revenue_1995,
        MONEY,
        "currency units",
        ["scale", "sum", "date-filter"],
    ),
    Spec(
        "tpch-l7-02",
        7,
        "List the top 5 customer nations by revenue (extended price times 1 minus discount, "
        "summed over line items) for orders placed in 1996, highest first. Break ties alphabetically.",
        "ranked_list",
        top5_nations_1996,
        EXACT,
        None,
        ["scale", "join-3", "ranking"],
    ),
    Spec(
        "tpch-l7-03",
        7,
        "How many distinct customers placed at least one order in 1997?",
        "number",
        customers_1997,
        EXACT,
        "customers",
        ["scale", "count-distinct"],
    ),
    Spec(
        "tpch-l7-04",
        7,
        "For orders placed in 1994, what was the average order total price by customer market "
        "segment? Return a table with columns `c_mktsegment` and `avg_totalprice`.",
        "table",
        avg_order_by_segment_1994,
        RATIO,
        None,
        ["scale", "join", "table"],
    ),
    Spec(
        "tpch-l7-05",
        7,
        "Which 3 part brands had the largest total quantity shipped in the first quarter of "
        "1995 (ship dates from 1 January to 31 March 1995)? Highest first; break ties alphabetically.",
        "ranked_list",
        top3_brands_q1_1995,
        EXACT,
        None,
        ["scale", "join", "ranking"],
    ),
    Spec(
        "tpch-l7-06",
        7,
        "What share of line items shipped in 1994 have return flag 'R'? Answer as a fraction "
        "between 0 and 1.",
        "number",
        return_share_1994,
        RATIO,
        "share",
        ["scale", "ratio"],
    ),
]
