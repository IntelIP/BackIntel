"""Reproducible, task-specific checks on the benchmark's canonical business data.

These checks characterize the data; a missing value is not automatically a defect.
Reference checks use SQLite rather than the Polars oracle that created the answers.
"""

from __future__ import annotations

import json
import math
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import polars as pl

from backintel.bench.datasets import sha256_file
from backintel.bench.oracle import load_answers
from backintel.settings import Settings

KEYS = {
    "orders": ["order_id"],
    "customers": ["customer_id"],
    "order_items": ["order_id", "order_item_id"],
    "order_payments": ["order_id", "payment_sequential"],
    "products": ["product_id"],
    "sellers": ["seller_id"],
    "product_category_translation": ["product_category_name"],
}


def frame_profile(frame: pl.DataFrame, *, keys: list[str] | None = None) -> dict:
    """Include duplicate surplus (not every member of a duplicate group) and null counts."""
    frame = frame.drop("source_sheet") if "source_sheet" in frame.columns else frame
    result = {
        "rows": frame.height,
        "columns": {name: str(dtype) for name, dtype in frame.schema.items()},
        "nulls": frame.null_count().row(0, named=True),
        "exact_duplicate_surplus": frame.height - frame.unique().height,
    }
    if keys:
        result["key_columns"] = keys
        result["duplicate_key_surplus"] = frame.height - frame.select(keys).unique().height
    dates = [name for name, dtype in frame.schema.items() if dtype.is_temporal()]
    result["date_ranges"] = {
        name: {"min": str(frame[name].min()), "max": str(frame[name].max())} for name in dates
    }
    return result


def unmatched_rows(child: pl.DataFrame, parent: pl.DataFrame, key: str) -> int:
    """Count unmatched child rows while keeping intentional one-to-many child grain."""
    return child.join(parent.select(key).unique(), on=key, how="anti").height


def profile_dataset(dataset: str, settings: Settings) -> dict:
    directory = settings.canonical_dir / dataset
    manifest = json.loads((directory / "MANIFEST.json").read_text())
    paths = sorted(directory.glob("*.parquet"))
    frames = {path.stem: pl.read_parquet(path) for path in paths}
    result = {
        "dataset": dataset,
        "recorded_at": datetime.now(UTC).isoformat(),
        "source_url": manifest.get("source_url"),
        "archive_sha256": manifest["archive_sha256"],
        "canonical_sha256": {path.name: sha256_file(path) for path in paths},
        "tables": {name: frame_profile(f, keys=KEYS.get(name)) for name, f in frames.items()},
        "scope": "Canonical data and selected analytical risks; not a source-system audit.",
    }
    if dataset == "olist":
        orders, reviews, customers = (frames[name] for name in ("orders", "order_reviews", "customers"))
        eligible = orders.filter(
            (pl.col("order_status") == "delivered") & pl.col("order_delivered_customer_date").is_not_null()
        )
        result["relationships"] = {
            "orders_without_customer": unmatched_rows(orders, customers, "customer_id"),
            **{
                f"{name}_without_order": unmatched_rows(frames[name], orders, "order_id")
                for name in ("order_items", "order_payments", "order_reviews")
            },
            "items_without_product": unmatched_rows(frames["order_items"], frames["products"], "product_id"),
            "items_without_seller": unmatched_rows(frames["order_items"], frames["sellers"], "seller_id"),
        }
        result["analytical_risks"] = {
            "delivered_without_delivery_date": orders.filter(
                (pl.col("order_status") == "delivered") & pl.col("order_delivered_customer_date").is_null()
            ).height,
            "eligible_delivery_orders": eligible.height,
            "eligible_orders_without_review": unmatched_rows(eligible, reviews, "order_id"),
            "eligible_review_rows": reviews.join(eligible.select("order_id"), on="order_id").height,
            "review_id_duplicate_surplus": reviews.height - reviews["review_id"].n_unique(),
            "orders_with_multiple_review_rows": reviews.group_by("order_id")
            .len()
            .filter(pl.col("len") > 1)
            .height,
            "orders_with_multiple_payment_rows": frames["order_payments"]
            .group_by("order_id")
            .len()
            .filter(pl.col("len") > 1)
            .height,
            "customer_rows": customers.height,
            "distinct_people": customers["customer_unique_id"].n_unique(),
            "negative_delivery_durations": eligible.filter(
                pl.col("order_delivered_customer_date") < pl.col("order_purchase_timestamp")
            ).height,
            "products_missing_category": frames["products"]
            .filter(pl.col("product_category_name").is_null())
            .height,
            "cost_ledger_present": False,
            "causal_assignment_present": False,
        }
    elif dataset == "online_retail_ii":
        transactions = frames["transactions"]
        result["analytical_risks"] = {
            "missing_customer_id": transactions["customer_id"].null_count(),
            "negative_quantity_rows": transactions.filter(pl.col("quantity") < 0).height,
            "nonpositive_price_rows": transactions.filter(pl.col("price") <= 0).height,
            "cancellation_invoice_rows": transactions.filter(pl.col("invoice").str.starts_with("C")).height,
            "non_cancellation_negative_quantity_rows": transactions.filter(
                (pl.col("quantity") < 0) & ~pl.col("invoice").str.starts_with("C")
            ).height,
            "source_sheet_is_provenance_only": True,
            "cost_ledger_present": False,
            "acquisition_channel_present": False,
        }
    return result


REFERENCE_SQL = {
    "olist": {
        "olist-l1-01": "SELECT COUNT(*) FROM orders WHERE order_status='delivered'",
        "olist-l1-02": "SELECT COUNT(DISTINCT customer_unique_id) FROM customers",
        "olist-l2-02": (
            "SELECT "
            "AVG(julianday(order_delivered_customer_date)-julianday(order_purchase_timestamp)) "
            "FROM orders WHERE order_status='delivered' AND order_delivered_customer_date IS NOT "
            "NULL"
        ),
        "olist-l2-04": (
            "SELECT AVG(r.review_score) FROM orders o JOIN order_reviews r ON "
            "o.order_id=r.order_id WHERE o.order_status='delivered' AND "
            "o.order_delivered_customer_date>o.order_estimated_delivery_date"
        ),
        "olist-l2-07": (
            "SELECT AVG(CASE WHEN n>1 THEN 1.0 ELSE 0 END) FROM (SELECT "
            "c.customer_unique_id, COUNT(*) n FROM orders o JOIN customers c ON "
            "o.customer_id=c.customer_id GROUP BY c.customer_unique_id)"
        ),
        "olist-l3-01": (
            "SELECT COUNT(*) FROM orders WHERE order_status='delivered' AND "
            "order_delivered_customer_date IS NULL"
        ),
        "olist-l3-04": "SELECT COUNT(*)-COUNT(DISTINCT review_id) FROM order_reviews",
    },
    "online_retail_ii": {
        "orii-l1-01": "SELECT COUNT(*) FROM transactions",
        "orii-l1-02": (
            "SELECT SUM(quantity*price) FROM transactions WHERE "
            "invoice_date>='2011-03-01' AND invoice_date<'2011-04-01' AND invoice NOT LIKE 'C%'"
        ),
        "orii-l3-01": (
            "SELECT (SELECT COUNT(*) FROM transactions)-COUNT(*) FROM (SELECT "
            "DISTINCT invoice, stock_code, description, quantity, invoice_date, price, "
            "customer_id, country FROM transactions)"
        ),
        "orii-l3-03": (
            "SELECT SUM(quantity*price) FROM transactions WHERE "
            "invoice_date>='2011-01-01' AND invoice_date<'2011-12-10'"
        ),
        "orii-l3-05": (
            "SELECT AVG(CASE WHEN customer_id IS NULL THEN 1.0 ELSE 0 END) FROM "
            "transactions WHERE invoice_date>='2011-01-01' AND invoice_date<'2011-12-10'"
        ),
    },
}


def verify_references(settings: Settings) -> list[dict]:
    results = []
    for dataset, queries in REFERENCE_SQL.items():
        answers = {s.id: s for s in load_answers(dataset)}
        path = settings.stores_dir / "sqlite" / f"{dataset}.sqlite"
        with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as connection:
            for scenario_id, sql in queries.items():
                actual = connection.execute(sql).fetchone()[0]
                expected = answers[scenario_id].expected
                results.append(
                    {
                        "scenario_id": scenario_id,
                        "sql": sql,
                        "actual": actual,
                        "expected": expected,
                        "matches": math.isclose(actual, expected, rel_tol=1e-9, abs_tol=1e-6),
                        "independence": (
                            "SQLite SQL on store copy versus existing Polars reference; shared "
                            "source parsing is not independently verified."
                        ),
                    }
                )
    return results


def write_quality_report(settings: Settings, output: Path) -> dict:
    report = {
        "datasets": [profile_dataset(name, settings) for name in ("olist", "online_retail_ii")],
        "reference_checks": verify_references(settings),
        "human_review": "pending; automated checks are not human calibration",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    return report
