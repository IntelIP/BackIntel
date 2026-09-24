#!/usr/bin/env python3
"""Reproducibly profile the locally authorized Kaggle Olist v2 archive."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import zipfile
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = Path.home() / "Library" / "Application Support" / "BackIntel" / "Datasets" / "OlistV2"
DEFAULT_OUTPUT = ROOT / "data" / "profiles" / "olist-v2" / "source-manifest-profile.json"
ARCHIVE_NAME = "brazilian-ecommerce.zip"
ARCHIVE_SHA256 = "967e41e04fc306fe604e2a693f488995a8b41e5047418f8a5c8e4abd6deca784"
EXPECTED_BYTES = {
    "olist_customers_dataset.csv": 9_033_957,
    "olist_geolocation_dataset.csv": 61_273_883,
    "olist_order_items_dataset.csv": 15_438_671,
    "olist_order_payments_dataset.csv": 5_777_138,
    "olist_order_reviews_dataset.csv": 14_451_670,
    "olist_orders_dataset.csv": 17_654_914,
    "olist_products_dataset.csv": 2_379_446,
    "olist_sellers_dataset.csv": 174_703,
    "product_category_name_translation.csv": 2_613,
}
EXPECTED_SHA256 = {
    "olist_customers_dataset.csv": "983a422239e1712ded753b3bf9ecf47dc73f144d306029dcfa99e70a226883d2",
    "olist_geolocation_dataset.csv": "b514f6fc991b9566aeba02aa5d67e2c3630f034b60a0e05aa0d082a3b66d88d6",
    "olist_order_items_dataset.csv": "0bc4d068c4fe38cbb01bd90e8746e3c613fe7b4baef75fab7b0e329701c3e279",
    "olist_order_payments_dataset.csv": "4f713964f2815dbbaa40b9488268c55aac3627bfce5aa96cf58d1f3616de3cc0",
    "olist_order_reviews_dataset.csv": "012b61c7593e34f51fa614efdf802b9c7056ce6aae5307ddb93236e7cfc797d7",
    "olist_orders_dataset.csv": "8df58ef3d2d7e9944010f7beecd9b75367f5588ec6e3c91cec19ae3345ef9ecf",
    "olist_products_dataset.csv": "3e6569628a17fbc75fd206ee357b59e20364b9afa90f5b6cd5b4d624c58aa9cc",
    "olist_sellers_dataset.csv": "1f643d2b950373b85735e7794b20986f528d7a000432e7c6f9bcbb44d0846a0e",
    "product_category_name_translation.csv": "a81f0d1f27b27e7293f761bc79e3ce8f348ee39c4b3ed3e49bde38f478586278",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def extract_verified_archive(archive: Path, csv_dir: Path) -> None:
    if sha256_file(archive) != ARCHIVE_SHA256:
        raise ValueError("Archive SHA-256 does not match the approved Kaggle v2 source.")
    csv_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as source:
        entries = source.infolist()
        names = [entry.filename for entry in entries]
        if len(entries) != len(EXPECTED_BYTES) or set(names) != set(EXPECTED_BYTES):
            raise ValueError(f"Archive file inventory differs: {sorted(set(names) ^ set(EXPECTED_BYTES))}")
        for entry in entries:
            if Path(entry.filename).name != entry.filename or entry.file_size != EXPECTED_BYTES[entry.filename]:
                raise ValueError(f"Unsafe path or uncompressed-size mismatch: {entry.filename}")
        for name, expected_size in EXPECTED_BYTES.items():
            destination = csv_dir / name
            if destination.exists():
                if destination.stat().st_size != expected_size or sha256_file(destination) != EXPECTED_SHA256[name]:
                    raise ValueError(f"Existing extracted file differs from the approved source: {name}")
                continue
            temporary = destination.with_suffix(destination.suffix + ".partial")
            try:
                with source.open(name) as input_file, temporary.open("wb") as output_file:
                    for block in iter(lambda: input_file.read(1024 * 1024), b""):
                        output_file.write(block)
                if temporary.stat().st_size != expected_size or sha256_file(temporary) != EXPECTED_SHA256[name]:
                    raise ValueError(f"Extracted file failed size/hash verification: {name}")
                temporary.replace(destination)
            finally:
                temporary.unlink(missing_ok=True)


def csv_rows(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        yield from csv.DictReader(source)


def file_profile(name: str, csv_dir: Path) -> dict:
    path = csv_dir / name
    rows = 0
    empty = Counter()
    date_min: dict[str, datetime] = {}
    date_max: dict[str, datetime] = {}
    malformed_dates = Counter()
    value_counts: dict[str, Counter] = defaultdict(Counter)
    key_columns = {
        "olist_customers_dataset.csv": ["customer_id"],
        "olist_orders_dataset.csv": ["order_id"],
        "olist_sellers_dataset.csv": ["seller_id"],
        "olist_products_dataset.csv": ["product_id"],
        "olist_order_items_dataset.csv": ["order_id", "order_item_id"],
        "olist_order_payments_dataset.csv": ["order_id", "payment_sequential"],
        "olist_order_reviews_dataset.csv": ["review_id", "order_id"],
    }.get(name, [])
    key_seen = {key: set() for key in key_columns}
    key_extra_rows = Counter()
    composite_seen = set()
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        headers = reader.fieldnames or []
        for row in reader:
            rows += 1
            for column, value in row.items():
                if value is None or value == "":
                    empty[column] += 1
                if column.endswith(("_at", "_date", "_timestamp")) and value:
                    try:
                        value_dt = datetime.fromisoformat(value)
                    except ValueError:
                        malformed_dates[column] += 1
                    else:
                        date_min[column] = min(date_min.get(column, value_dt), value_dt)
                        date_max[column] = max(date_max.get(column, value_dt), value_dt)
            for column in ("order_status", "review_score"):
                if row.get(column):
                    value_counts[column][row[column]] += 1
            for column in key_columns:
                value = row.get(column, "")
                if value:
                    if value in key_seen[column]:
                        key_extra_rows[column] += 1
                    key_seen[column].add(value)
            if name == "olist_order_items_dataset.csv":
                composite_seen.add((row.get("order_id", ""), row.get("order_item_id", "")))
            elif name == "olist_order_payments_dataset.csv":
                composite_seen.add((row.get("order_id", ""), row.get("payment_sequential", "")))
    duplicate_extra = dict(key_extra_rows)
    if name in ("olist_order_items_dataset.csv", "olist_order_payments_dataset.csv"):
        candidate_key = "(order_id,order_item_id)" if "items" in name else "(order_id,payment_sequential)"
        duplicate_extra[candidate_key] = rows - len(composite_seen)
    return {
        "rows": rows,
        "headers": headers,
        "empty_cells_by_column": dict(empty),
        "timestamp_ranges": {
            column: [date_min[column].isoformat(sep=" "), date_max[column].isoformat(sep=" ")]
            for column in date_min
        },
        "malformed_timestamp_cells": dict(malformed_dates),
        "duplicate_extra_rows_by_candidate_key": duplicate_extra,
        "value_counts": {key: dict(counts) for key, counts in value_counts.items()},
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def collect_columns(csv_dir: Path, name: str, columns: list[str]) -> list[tuple[str, ...]]:
    return [tuple(row.get(column, "") for column in columns) for row in csv_rows(csv_dir / name)]


def parsed_date(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def relationship_profile(csv_dir: Path) -> dict:
    orders = collect_columns(csv_dir, "olist_orders_dataset.csv", [
        "order_id", "customer_id", "order_status", "order_purchase_timestamp", "order_approved_at",
        "order_delivered_carrier_date", "order_delivered_customer_date", "order_estimated_delivery_date",
    ])
    order_ids = {row[0] for row in orders if row[0]}
    customer_ids = {row[0] for row in collect_columns(csv_dir, "olist_customers_dataset.csv", ["customer_id"]) if row[0]}
    seller_ids = {row[0] for row in collect_columns(csv_dir, "olist_sellers_dataset.csv", ["seller_id"]) if row[0]}
    product_ids = {row[0] for row in collect_columns(csv_dir, "olist_products_dataset.csv", ["product_id"]) if row[0]}
    items = collect_columns(csv_dir, "olist_order_items_dataset.csv", ["order_id", "order_item_id", "seller_id", "product_id"])
    item_orders = {row[0] for row in items if row[0]}
    item_sellers: dict[str, set[str]] = defaultdict(set)
    for order_id, _, seller_id, _ in items:
        if order_id and seller_id:
            item_sellers[order_id].add(seller_id)
    payments = collect_columns(csv_dir, "olist_order_payments_dataset.csv", ["order_id", "payment_sequential"])
    payment_order_ids = {row[0] for row in payments if row[0]}
    payment_counts = Counter(row[0] for row in payments if row[0])
    reviews = collect_columns(csv_dir, "olist_order_reviews_dataset.csv", [
        "order_id", "review_id", "review_comment_message", "review_creation_date", "review_answer_timestamp",
    ])
    review_per_order = Counter(row[0] for row in reviews if row[0])
    review_id_per_order: dict[str, set[str]] = defaultdict(set)
    review_id_orders: dict[str, set[str]] = defaultdict(set)
    for order_id, review_id, *_ in reviews:
        if order_id and review_id:
            review_id_per_order[order_id].add(review_id)
            review_id_orders[review_id].add(order_id)

    orders_by_id = {row[0]: row for row in orders if row[0]}
    temporal = Counter()
    for row in orders:
        purchase, approved, carrier, delivered, estimated = map(parsed_date, row[3:8])
        if purchase and approved and approved < purchase:
            temporal["approval_before_purchase"] += 1
        if purchase and carrier and carrier < purchase:
            temporal["carrier_before_purchase"] += 1
        if purchase and delivered and delivered < purchase:
            temporal["delivery_before_purchase"] += 1
        if carrier and delivered and delivered < carrier:
            temporal["delivery_before_carrier"] += 1
        if purchase and estimated and estimated < purchase:
            temporal["estimated_delivery_before_purchase"] += 1
        if approved and estimated and estimated < approved:
            temporal["estimated_delivery_before_approval"] += 1
    for order_id, _, _, creation, answer in reviews:
        order = orders_by_id.get(order_id)
        creation_dt, answer_dt = parsed_date(creation), parsed_date(answer)
        if creation_dt and answer_dt and answer_dt < creation_dt:
            temporal["review_answer_before_creation"] += 1
        if order and creation_dt:
            purchase_dt = parsed_date(order[3])
            delivered_dt = parsed_date(order[6])
            if purchase_dt and creation_dt < purchase_dt:
                temporal["review_created_before_purchase"] += 1
            if delivered_dt and creation_dt < delivered_dt:
                temporal["review_created_before_delivery"] += 1

    delivered = [row for row in orders if row[2] == "delivered"]
    outcome_rows = [row for row in delivered if row[6] and row[7]]
    eligible = [row for row in outcome_rows if row[4]]
    sample = next(((ordinal, row) for ordinal, row in enumerate(orders, 1) if row[2] == "delivered" and row[4] and row[6] and row[7]), None)
    source_path = csv_dir / "olist_orders_dataset.csv"
    with source_path.open("r", encoding="utf-8-sig", newline="") as source:
        source_columns = next(csv.reader(source), [])
    sample_trace = None
    if sample:
        ordinal, row = sample
        sample_trace = {
            "source_file": source_path.name,
            "source_file_sha256": sha256_file(source_path),
            "data_row_ordinal_1_based": ordinal,
            "schema_columns": source_columns,
            "record_key_handling": "raw identifier omitted from the committed profile artifact",
            "observed_fields": {
                "purchase_timestamp": row[3],
                "approval_timestamp": row[4],
                "actual_delivery_timestamp": row[6],
                "estimated_delivery_timestamp": row[7],
            },
            "retrospective_late_label": parsed_date(row[6]) > parsed_date(row[7]),
            "label_is_feature": False,
            "availability_decision": "Approval-time prediction remains conditional; the static extract has no field-version history.",
        }
    late = 0
    malformed_outcome_dates = 0
    for row in eligible:
        actual, estimated = parsed_date(row[6]), parsed_date(row[7])
        if actual is None or estimated is None:
            malformed_outcome_dates += 1
        else:
            late += actual > estimated
    return {
        "orders": {
            "rows": len(orders), "unique_order_ids": len(order_ids),
            "orders_missing_customer_dimension": len({row[1] for row in orders if row[1]} - customer_ids),
            "orders_missing_approval_timestamp": sum(not row[4] for row in orders),
            "status_counts": dict(Counter(row[2] for row in orders)),
        },
        "order_items": {
            "rows": len(items), "orders_with_items": len(item_orders),
            "item_order_ids_not_in_orders": len(item_orders - order_ids),
            "item_seller_ids_not_in_sellers": len({row[2] for row in items if row[2]} - seller_ids),
            "item_product_ids_not_in_products": len({row[3] for row in items if row[3]} - product_ids),
            "orders_with_multiple_sellers": sum(len(values) > 1 for values in item_sellers.values()),
        },
        "payments": {
            "rows": len(payments),
            "payment_order_ids_not_in_orders": len(payment_order_ids - order_ids),
            "orders_with_multiple_payment_rows": sum(count > 1 for count in payment_counts.values()),
        },
        "reviews": {
            "rows": len(reviews), "distinct_order_ids": len(review_per_order),
            "review_order_ids_not_in_orders": len(set(review_per_order) - order_ids),
            "orders_with_multiple_review_rows": sum(count > 1 for count in review_per_order.values()),
            "orders_with_multiple_distinct_review_ids": sum(len(values) > 1 for values in review_id_per_order.values()),
            "rows_with_nonblank_review_comment": sum(bool(row[2].strip()) for row in reviews),
            "review_ids_associated_with_multiple_orders": sum(len(values) > 1 for values in review_id_orders.values()),
        },
        "timestamp_ordering_checks": dict(temporal),
        "source_row_trace": sample_trace,
        "delivery_target_candidate": {
            "decision": "candidate only; not an approved prediction target",
            "prediction_time": "order approval, conditional on a valid historical feature cutoff",
            "eligible_population": "delivered orders with approval, actual delivery, and estimated delivery timestamps",
            "delivered_orders": len(delivered),
            "delivered_with_actual_and_estimated_timestamps": len(outcome_rows),
            "delivered_with_approval_and_both_outcome_timestamps": len(eligible),
            "late_by_actual_after_estimated_in_eligible_subset": late,
            "late_rate_in_eligible_subset": late / len(eligible) if eligible else None,
            "malformed_timestamp_pairs": malformed_outcome_dates,
            "availability_caveat": "The static extract has no field-version history. It cannot prove exactly when estimated delivery dates or other fields became available.",
            "selection_caveat": "This retrospective label excludes undelivered, cancelled, and otherwise ineligible orders; it does not describe all orders.",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR, help="External local directory containing the approved Kaggle archive and optional extracted CSVs.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Profile JSON output path; raw source files are never copied here.")
    args = parser.parse_args()
    data_dir = args.data_dir.expanduser().resolve()
    archive = data_dir / ARCHIVE_NAME
    csv_dir = data_dir / "csv"
    if not archive.is_file():
        raise FileNotFoundError(f"Kaggle archive not found: {archive}")
    extract_verified_archive(archive, csv_dir)
    profiles = {name: file_profile(name, csv_dir) for name in sorted(EXPECTED_BYTES)}
    manifest = {
        "profile_version": "0.1.0",
        "profile_tool": {
            "path": "scripts/data/profile_olist.py",
            "sha256": sha256_file(Path(__file__).resolve()),
        },
        "source": "Kaggle Olist Brazilian E-Commerce Public Dataset",
        "ref": "olistbr/brazilian-ecommerce",
        "kaggle_current_version_verified": 2,
        "license": "CC BY-NC-SA 4.0",
        "approved_use": "non-commercial local prototype/demo only; approved 2026-09-23",
        "source_page": "https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce",
        "metadata_api": "https://www.kaggle.com/api/v1/datasets/view/olistbr/brazilian-ecommerce",
        "file_list_api": "https://www.kaggle.com/api/v1/datasets/list/olistbr/brazilian-ecommerce",
        "review_language": {
            "expected": "Portuguese (Brazil)",
            "observed_nonblank_comment_rows": 40_950,
            "language_detection_performed": False,
            "note": "Language is a source-context expectation, not a programmatically verified label. Jev suitability remains unproven.",
        },
        "archive": {"name": archive.name, "bytes": archive.stat().st_size, "sha256": sha256_file(archive)},
        "files": profiles,
        "relationship_profile": relationship_profile(csv_dir),
        "limitations": [
            "Historical static data, not a live feed.",
            "Reviews are post-purchase and unavailable for same-order approval-time prediction.",
            "Orders may contain multiple sellers; do not attribute a review to every seller on that order.",
            "The dataset lacks business intervention, seller-contact, and carrier-exception records.",
            "Shipping-limit timestamps extend beyond the order-purchase period and require investigation before use.",
            "Kaggle license is CC BY-NC-SA 4.0; approved use is non-commercial local prototype/demo only.",
        ],
    }
    output = args.output.expanduser()
    if not output.is_absolute():
        output = ROOT / output
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {output}")
    print(f"Archive SHA-256: {manifest['archive']['sha256']}")
    print(json.dumps(manifest["relationship_profile"], indent=2, ensure_ascii=False))
    for name, profile in profiles.items():
        print(f"{name}: {profile['rows']} rows, {profile['bytes']} bytes, sha256={profile['sha256']}")


if __name__ == "__main__":
    main()
