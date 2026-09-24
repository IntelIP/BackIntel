#!/usr/bin/env python3
"""Independently recompute monthly report totals from approved raw CSV rows."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA = Path.home() / "Library" / "Application Support" / "BackIntel" / "Datasets" / "OlistV2" / "csv"
DEFAULT_REPORT = Path.home() / "Library" / "Application Support" / "BackIntel" / "Evidence" / "BINT5" / "seller-review.json"


def rows(path: Path):
    with path.open(encoding="utf-8-sig", newline="") as source:
        yield from csv.DictReader(source)


def check(report_path: Path, data: Path) -> dict:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    profile = json.loads((ROOT / "data/profiles/olist-v2/source-manifest-profile.json").read_text(encoding="utf-8"))
    months = (report["contract"]["comparison_purchase_month"], report["contract"]["report_purchase_month"])
    if hashlib.sha256((ROOT / "data/profiles/olist-v2/source-manifest-profile.json").read_bytes()).hexdigest() != report["contract"]["profile_sha256"]:
        raise ValueError("Report and source-profile fingerprint differ")
    wanted_files = {"olist_orders_dataset.csv", "olist_order_items_dataset.csv", "olist_products_dataset.csv", "olist_order_reviews_dataset.csv"}
    for name in wanted_files:
        digest = hashlib.sha256((data / name).read_bytes()).hexdigest()
        if digest != profile["files"][name]["sha256"]:
            raise ValueError(f"Raw CSV fingerprint differs: {name}")
    orders = {
        r["order_id"]: r for r in rows(data / "olist_orders_dataset.csv")
        if r["order_status"] == "delivered" and r["order_purchase_timestamp"][:7] in months
    }
    sellers = defaultdict(set)
    categories = defaultdict(set)
    products = {r["product_id"]: r["product_category_name"] for r in rows(data / "olist_products_dataset.csv")}
    for item in rows(data / "olist_order_items_dataset.csv"):
        key = item["order_id"]
        if key in orders:
            sellers[key].add(item["seller_id"])
            categories[key].add(products[item["product_id"]] or "<missing>")
    review_rows = defaultdict(list)
    for review in rows(data / "olist_order_reviews_dataset.csv"):
        if review["order_id"] in orders:
            review_rows[review["order_id"]].append(review)

    actual = defaultdict(Counter)
    for key, order in orders.items():
        month = order["order_purchase_timestamp"][:7]
        scopes = [("marketplace", "all")]
        if len(sellers[key]) == 1:
            scopes.append(("seller", next(iter(sellers[key]))))
            if len(categories[key]) == 1 and "<missing>" not in categories[key]:
                scopes.append(("category", next(iter(categories[key]))))
        reviews = review_rows[key]
        for scope, entity in scopes:
            counts = actual[(scope, entity, month)]
            counts["delivered_orders"] += 1
            if order["order_delivered_customer_date"] and order["order_estimated_delivery_date"]:
                counts["dated_orders"] += 1
                counts["late_orders"] += datetime.fromisoformat(order["order_delivered_customer_date"]) > datetime.fromisoformat(order["order_estimated_delivery_date"])
            counts["orders_with_review"] += bool(reviews)
            counts["review_rows"] += len(reviews)
            counts["rated_review_rows"] += sum(bool(r["review_score"]) for r in reviews)
            counts["nonblank_text_rows"] += sum(bool(r["review_comment_message"].strip()) for r in reviews)

    findings = report["findings"]
    # Compare all marketplace totals plus every highlighted seller's two periods and top categories.
    selected = {(m["scope"], m["entity_id"], m["purchase_month"]): m for m in report["marketplace"]}
    for finding in findings:
        for metric in (finding["previous"], finding["current"]):
            selected[(metric["scope"], metric["entity_id"], metric["purchase_month"])] = metric
    top_categories = sorted(
        (r for r in report["category_metrics"] if r["purchase_month"] == months[1]),
        key=lambda r: (-r["delivered_orders"], r["entity_id"]),
    )[:10]
    for metric in top_categories:
        selected[(metric["scope"], metric["entity_id"], metric["purchase_month"])] = metric
    fields = ("delivered_orders", "dated_orders", "late_orders", "orders_with_review", "review_rows", "rated_review_rows", "nonblank_text_rows")
    for key, metric in selected.items():
        for field in fields:
            if actual[key][field] != metric[field]:
                raise ValueError(f"Independent raw-data mismatch for {key} / {field}: {actual[key][field]} vs {metric[field]}")
    # Verify each sampled source link against the hashed raw order file and its review occurrence.
    order_ordinal = {r["order_id"]: i for i, r in enumerate(rows(data / "olist_orders_dataset.csv"), 1)}
    review_ordinal = {i: r for i, r in enumerate(rows(data / "olist_order_reviews_dataset.csv"), 1)}
    examples = 0
    for finding in findings:
        for e in finding["source_examples"]:
            key = e["order_id"]
            if e["order_row_number"] != order_ordinal[key] or e["source_file_sha256"] != profile["files"]["olist_orders_dataset.csv"]["sha256"]:
                raise ValueError("Evidence order-to-source link differs from raw source")
            if e["review_row_number"] is not None:
                review = review_ordinal[e["review_row_number"]]
                if review["order_id"] != key or review["review_comment_message"] != (e["review_text"] or ""):
                    raise ValueError("Evidence review-to-source link differs from raw source")
            examples += 1
    return {"status": "passed", "verified_metric_rows": len(selected), "verified_source_examples": examples,
            "report_profile_sha256": report["contract"]["profile_sha256"], "report_candidate": report["candidate"]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA)
    args = parser.parse_args()
    print(json.dumps(check(args.report, args.data_dir), indent=2))


if __name__ == "__main__":
    main()
