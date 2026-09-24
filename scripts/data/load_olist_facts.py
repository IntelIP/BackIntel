#!/usr/bin/env python3
"""Load the approved Olist v2 source snapshot into BackIntel's local PostgreSQL schema."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import subprocess
import sys
import uuid
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

ROOT = Path(__file__).resolve().parents[2]
PROFILE_PATH = ROOT / "data" / "profiles" / "olist-v2" / "source-manifest-profile.json"
MIGRATION_PATH = ROOT / "migrations" / "0001_olist_business_facts.sql"
DEFAULT_DATA_DIR = Path.home() / "Library" / "Application Support" / "BackIntel" / "Datasets" / "OlistV2"
DEFAULT_REPORT = Path.home() / "Library" / "Application Support" / "BackIntel" / "Evidence" / "BINT4" / "olist-business-facts.json"
DATASET_REF = "olistbr/brazilian-ecommerce"
LICENSE = "CC BY-NC-SA 4.0"
IMPORTED_FILES = (
    "olist_customers_dataset.csv",
    "olist_order_items_dataset.csv",
    "olist_order_payments_dataset.csv",
    "olist_order_reviews_dataset.csv",
    "olist_orders_dataset.csv",
    "olist_products_dataset.csv",
    "olist_sellers_dataset.csv",
    "product_category_name_translation.csv",
)
EXCLUDED_FILES = {"olist_geolocation_dataset.csv": "Not needed for the v0.1 seller/delivery facts; retained in the external source archive."}
FACT_LOAD_ORDER = (
    "olist_customers_dataset.csv",
    "olist_sellers_dataset.csv",
    "olist_products_dataset.csv",
    "olist_orders_dataset.csv",
    "product_category_name_translation.csv",
    "olist_order_items_dataset.csv",
    "olist_order_payments_dataset.csv",
    "olist_order_reviews_dataset.csv",
)
NAMESPACE = uuid.UUID("e742b018-f909-4e93-837e-dfa2283352a8")

# Source-file -> immutable source key fields. Keys are descriptive only; occurrence identity is batch + row ordinal.
SOURCE_KEY_FIELDS = {
    "olist_customers_dataset.csv": ("customer_id",),
    "olist_order_items_dataset.csv": ("order_id", "order_item_id"),
    "olist_order_payments_dataset.csv": ("order_id", "payment_sequential"),
    "olist_order_reviews_dataset.csv": ("review_id", "order_id"),
    "olist_orders_dataset.csv": ("order_id",),
    "olist_products_dataset.csv": ("product_id",),
    "olist_sellers_dataset.csv": ("seller_id",),
    "product_category_name_translation.csv": ("product_category_name",),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def row_hash(row: dict[str, str]) -> str:
    return hashlib.sha256(canonical_json(row).encode("utf-8")).hexdigest()


def batch_uuid(source_file: str, sha256: str) -> uuid.UUID:
    return uuid.uuid5(NAMESPACE, f"{DATASET_REF}:{source_file}:{sha256}")


def git_identity() -> dict[str, Any]:
    try:
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        changes = subprocess.check_output(
            ["git", "status", "--porcelain", "--untracked-files=all"], cwd=ROOT, text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return {"head_sha": None, "exact_candidate_sha": None, "working_tree_clean": False}
    return {
        "head_sha": head,
        "exact_candidate_sha": head if not changes else None,
        "working_tree_clean": not changes,
    }


def text(value: str | None) -> str | None:
    return value if value not in (None, "") else None


def integer(value: str | None, field: str) -> int | None:
    value = text(value)
    if value is None:
        return None
    try:
        return int(value)
    except ValueError as error:
        raise ValueError(f"Invalid integer in {field}: {value!r}") from error


def amount(value: str | None, field: str) -> Decimal:
    value = text(value)
    if value is None:
        raise ValueError(f"Missing monetary value in {field}")
    try:
        parsed = Decimal(value)
    except InvalidOperation as error:
        raise ValueError(f"Invalid monetary value in {field}: {value!r}") from error
    if not parsed.is_finite() or parsed.quantize(Decimal("0.01")) != parsed:
        raise ValueError(f"Monetary value cannot be represented exactly to cents in {field}: {value!r}")
    return parsed


def timestamp(value: str | None, field: str) -> datetime | None:
    value = text(value)
    if value is None:
        return None
    try:
        result = datetime.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"Invalid timestamp in {field}: {value!r}") from error
    if result.tzinfo is not None:
        raise ValueError(f"Timezone-bearing timestamp requires an explicit source policy in {field}: {value!r}")
    return result


def source_key(filename: str, row: dict[str, str]) -> str | None:
    values = [text(row.get(field)) for field in SOURCE_KEY_FIELDS[filename]]
    if any(value is None for value in values):
        return None
    return "|".join(value for value in values if value is not None)


def validated_inputs(data_dir: Path, profile_path: Path) -> tuple[dict[str, Any], dict[str, Path]]:
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    if profile.get("ref") != DATASET_REF or profile.get("license") != LICENSE:
        raise ValueError("Profile is not the approved Olist Kaggle source/license.")
    if "non-commercial local prototype/demo only" not in profile.get("approved_use", ""):
        raise ValueError("Profile does not carry the approved non-commercial local-use restriction.")
    if profile.get("kaggle_current_version_verified") != 2:
        raise ValueError("Only the profiled Kaggle Olist v2 source is accepted by this loader.")

    archive = data_dir / profile["archive"]["name"]
    if not archive.is_file() or sha256_file(archive) != profile["archive"]["sha256"]:
        raise ValueError("Olist archive is missing or its SHA-256 differs from the committed profile.")
    csv_dir = data_dir / "csv"
    paths: dict[str, Path] = {}
    for filename in IMPORTED_FILES:
        expected = profile["files"].get(filename)
        path = csv_dir / filename
        if not expected or not path.is_file():
            raise ValueError(f"Profile or extracted source file missing: {filename}")
        if path.stat().st_size != expected["bytes"] or sha256_file(path) != expected["sha256"]:
            raise ValueError(f"Source file differs from the approved profile: {filename}")
        with path.open("r", encoding="utf-8-sig", newline="") as source:
            headers = next(csv.reader(source), [])
        if headers != expected["headers"]:
            raise ValueError(f"CSV schema differs from the approved profile: {filename}")
        paths[filename] = path
    return profile, paths


def apply_migration(conn: psycopg.Connection, migration_path: Path = MIGRATION_PATH) -> None:
    migration = migration_path.read_text(encoding="utf-8")
    with conn.transaction():
        conn.execute(migration, prepare=False)
        version = conn.execute("SELECT version FROM backintel.schema_migrations WHERE version = 1").fetchone()
        if version is None:
            raise RuntimeError("Migration 0001 did not record its version.")


def _copy_source_records(conn: psycopg.Connection, filename: str, path: Path, profile: dict[str, Any], batch_id: uuid.UUID) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        with conn.cursor().copy(
            "COPY backintel.source_records (batch_id, source_row_number, source_business_key, payload_sha256, payload) FROM STDIN"
        ) as copy:
            for ordinal, row in enumerate(reader, start=1):
                copy.write_row((batch_id, ordinal, source_key(filename, row), row_hash(row), Jsonb(row)))
    count = ordinal if "ordinal" in locals() else 0
    if count != profile["files"][filename]["rows"]:
        raise ValueError(f"Source row count changed during load for {filename}: {count}")
    return count


def _copy_facts(conn: psycopg.Connection, filename: str, path: Path, batch_id: uuid.UUID) -> int:
    table_and_columns: dict[str, tuple[str, str, Any]] = {
        "olist_customers_dataset.csv": (
            "customers", "customer_id, customer_unique_id, zip_code_prefix, city, state_code, source_batch_id, source_row_number",
            lambda r, n: (r["customer_id"], text(r["customer_unique_id"]), text(r["customer_zip_code_prefix"]), text(r["customer_city"]), text(r["customer_state"]), batch_id, n)),
        "olist_sellers_dataset.csv": (
            "sellers", "seller_id, zip_code_prefix, city, state_code, source_batch_id, source_row_number",
            lambda r, n: (r["seller_id"], text(r["seller_zip_code_prefix"]), text(r["seller_city"]), text(r["seller_state"]), batch_id, n)),
        "olist_products_dataset.csv": (
            "products", "product_id, category_name, name_length, description_length, photos_quantity, weight_grams, length_cm, height_cm, width_cm, source_batch_id, source_row_number",
            lambda r, n: (r["product_id"], text(r["product_category_name"]), integer(r["product_name_lenght"], "product_name_lenght"), integer(r["product_description_lenght"], "product_description_lenght"), integer(r["product_photos_qty"], "product_photos_qty"), integer(r["product_weight_g"], "product_weight_g"), integer(r["product_length_cm"], "product_length_cm"), integer(r["product_height_cm"], "product_height_cm"), integer(r["product_width_cm"], "product_width_cm"), batch_id, n)),
        "olist_orders_dataset.csv": (
            "orders", "order_id, customer_id, status, purchased_at, approved_at, carrier_handoff_at, delivered_at, estimated_delivery_at, source_batch_id, source_row_number",
            lambda r, n: (r["order_id"], r["customer_id"], r["order_status"], timestamp(r["order_purchase_timestamp"], "order_purchase_timestamp"), timestamp(r["order_approved_at"], "order_approved_at"), timestamp(r["order_delivered_carrier_date"], "order_delivered_carrier_date"), timestamp(r["order_delivered_customer_date"], "order_delivered_customer_date"), timestamp(r["order_estimated_delivery_date"], "order_estimated_delivery_date"), batch_id, n)),
        "product_category_name_translation.csv": (
            "product_category_translations", "category_name, category_name_english, source_batch_id, source_row_number",
            lambda r, n: (r["product_category_name"], r["product_category_name_english"], batch_id, n)),
        "olist_order_items_dataset.csv": (
            "order_items", "order_id, order_item_id, product_id, seller_id, shipping_limit_at, price, freight_value, source_batch_id, source_row_number",
            lambda r, n: (r["order_id"], integer(r["order_item_id"], "order_item_id"), r["product_id"], r["seller_id"], timestamp(r["shipping_limit_date"], "shipping_limit_date"), amount(r["price"], "price"), amount(r["freight_value"], "freight_value"), batch_id, n)),
        "olist_order_payments_dataset.csv": (
            "payments", "order_id, payment_sequential, payment_type, payment_installments, payment_value, source_batch_id, source_row_number",
            lambda r, n: (r["order_id"], integer(r["payment_sequential"], "payment_sequential"), r["payment_type"], integer(r["payment_installments"], "payment_installments"), amount(r["payment_value"], "payment_value"), batch_id, n)),
        "olist_order_reviews_dataset.csv": (
            "reviews", "source_review_id, order_id, score, title, message, created_at, answered_at, source_batch_id, source_row_number",
            lambda r, n: (r["review_id"], r["order_id"], integer(r["review_score"], "review_score"), text(r["review_comment_title"]), text(r["review_comment_message"]), timestamp(r["review_creation_date"], "review_creation_date"), timestamp(r["review_answer_timestamp"], "review_answer_timestamp"), batch_id, n)),
    }
    table, columns, mapper = table_and_columns[filename]
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        with conn.cursor().copy(f"COPY backintel.{table} ({columns}) FROM STDIN") as copy:
            for ordinal, row in enumerate(reader, start=1):
                copy.write_row(mapper(row, ordinal))
    return ordinal if "ordinal" in locals() else 0


def _register_batches(conn: psycopg.Connection, profile: dict[str, Any], paths: dict[str, Path]) -> dict[str, uuid.UUID]:
    result: dict[str, uuid.UUID] = {}
    for filename in IMPORTED_FILES:
        item = profile["files"][filename]
        batch_id = batch_uuid(filename, item["sha256"])
        schema_sha256 = hashlib.sha256(canonical_json(item["headers"]).encode("utf-8")).hexdigest()
        conn.execute(
            """INSERT INTO backintel.source_batches
               (batch_id, dataset_ref, source_version, source_file, file_sha256, archive_sha256,
                schema_sha256, row_count, file_bytes, license, approved_use)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (batch_id, DATASET_REF, profile["kaggle_current_version_verified"], filename,
             item["sha256"], profile["archive"]["sha256"], schema_sha256,
             item["rows"], item["bytes"], profile["license"], profile["approved_use"]),
        )
        result[filename] = batch_id
    return result


def _existing_load(conn: psycopg.Connection, profile: dict[str, Any]) -> dict[str, Any] | None:
    rows = conn.execute(
        "SELECT source_file, file_sha256, row_count FROM backintel.source_batches WHERE dataset_ref = %s ORDER BY source_file",
        (DATASET_REF,),
    ).fetchall()
    if not rows:
        return None
    expected = {
        filename: (profile["files"][filename]["sha256"], profile["files"][filename]["rows"])
        for filename in IMPORTED_FILES
    }
    actual = {name: (sha, count) for name, sha, count in rows}
    if actual != expected:
        raise RuntimeError("Database contains a partial or different Olist source snapshot; refusing to overwrite it.")
    for filename, (sha, count) in expected.items():
        batch_id = batch_uuid(filename, sha)
        record_count = conn.execute("SELECT count(*) FROM backintel.source_records WHERE batch_id = %s", (batch_id,)).fetchone()[0]
        if record_count != count:
            raise RuntimeError(f"Loaded source occurrence ledger is incomplete for {filename}.")
    return reconcile(conn, profile, already_loaded=True)


def reconcile(conn: psycopg.Connection, profile: dict[str, Any], already_loaded: bool = False) -> dict[str, Any]:
    expected_facts = {
        "customers": "olist_customers_dataset.csv",
        "sellers": "olist_sellers_dataset.csv",
        "products": "olist_products_dataset.csv",
        "orders": "olist_orders_dataset.csv",
        "product_category_translations": "product_category_name_translation.csv",
        "order_items": "olist_order_items_dataset.csv",
        "payments": "olist_order_payments_dataset.csv",
        "reviews": "olist_order_reviews_dataset.csv",
    }
    counts: dict[str, dict[str, int]] = {}
    source_occurrence_counts: dict[str, dict[str, int]] = {}
    failures: list[str] = []
    for filename in IMPORTED_FILES:
        item = profile["files"][filename]
        batch_id = batch_uuid(filename, item["sha256"])
        actual = conn.execute(
            "SELECT count(*) FROM backintel.source_records WHERE batch_id = %s", (batch_id,)
        ).fetchone()[0]
        source_occurrence_counts[filename] = {"expected": item["rows"], "actual": actual}
        if actual != item["rows"]:
            failures.append(f"{filename}: expected {item['rows']} source occurrences, found {actual}")
    for table, filename in expected_facts.items():
        expected = profile["files"][filename]["rows"]
        actual = conn.execute(f"SELECT count(*) FROM backintel.{table}").fetchone()[0]
        counts[table] = {"expected_source_rows": expected, "fact_rows": actual}
        if actual != expected:
            failures.append(f"{table}: expected {expected} source rows, found {actual}")

    source_totals = {
        "item_value_total": ("olist_order_items_dataset.csv", "price"),
        "freight_total": ("olist_order_items_dataset.csv", "freight_value"),
        "payment_total": ("olist_order_payments_dataset.csv", "payment_value"),
    }
    monetary: dict[str, dict[str, str | bool]] = {}
    for name, (filename, field) in source_totals.items():
        source_total = conn.execute(
            """SELECT COALESCE(sum((r.payload ->> %s)::numeric), 0::numeric)
               FROM backintel.source_records AS r
               JOIN backintel.source_batches AS b USING (batch_id)
               WHERE b.source_file = %s""",
            (field, filename),
        ).fetchone()[0]
        fact_table = "order_items" if filename == "olist_order_items_dataset.csv" else "payments"
        fact_total = conn.execute(f"SELECT COALESCE(sum({field}), 0::numeric) FROM backintel.{fact_table}").fetchone()[0]
        matches = source_total == fact_total
        monetary[name] = {"source_ledger_total": str(source_total), "canonical_fact_total": str(fact_total), "matches": matches}
        if not matches:
            failures.append(f"{name}: source ledger and canonical fact totals differ")

    summary = conn.execute(
        """SELECT count(*),
                  COALESCE(sum(item_value_total), 0::numeric),
                  COALESCE(sum(freight_total), 0::numeric),
                  COALESCE(sum(payment_total), 0::numeric)
           FROM backintel.order_summary"""
    ).fetchone()
    order_count = conn.execute("SELECT count(*) FROM backintel.orders").fetchone()[0]
    if summary[0] != order_count:
        failures.append("order_summary view row count differs from the canonical orders grain")
    for col_index, total_name in ((1, "item_value_total"), (2, "freight_total"), (3, "payment_total")):
        if summary[col_index] != Decimal(monetary[total_name]["canonical_fact_total"]):
            failures.append(f"order_summary {total_name} differs from its canonical child table")

    multi_seller_orders = conn.execute(
        "SELECT count(*) FROM (SELECT order_id FROM backintel.order_items GROUP BY order_id HAVING count(DISTINCT seller_id) > 1) AS x"
    ).fetchone()[0]
    multi_review_orders = conn.execute(
        "SELECT count(*) FROM (SELECT order_id FROM backintel.reviews GROUP BY order_id HAVING count(*) > 1) AS x"
    ).fetchone()[0]
    duplicate_review_id_extra_rows = conn.execute(
        "SELECT count(*) - count(DISTINCT source_review_id) FROM backintel.reviews"
    ).fetchone()[0]
    profile_relationships = profile["relationship_profile"]
    expected_multi_seller = profile_relationships["order_items"]["orders_with_multiple_sellers"]
    expected_multi_review = profile_relationships["reviews"]["orders_with_multiple_review_rows"]
    if multi_seller_orders != expected_multi_seller:
        failures.append("multi-seller order count differs from the profiled source")
    if multi_review_orders != expected_multi_review:
        failures.append("multiple-review order count differs from the profiled source")
    expected_review_duplicates = profile["files"]["olist_order_reviews_dataset.csv"]["duplicate_extra_rows_by_candidate_key"].get("review_id", 0)
    if duplicate_review_id_extra_rows != expected_review_duplicates:
        failures.append("duplicate review-id occurrences differ from the profiled source")

    lineage = conn.execute(
        """SELECT b.source_file, b.file_sha256, r.source_row_number, r.payload_sha256
           FROM backintel.source_records AS r
           JOIN backintel.source_batches AS b USING (batch_id)
           JOIN backintel.orders AS o
             ON o.source_batch_id = r.batch_id
            AND o.source_row_number = r.source_row_number
           WHERE b.source_file = 'olist_orders_dataset.csv'
           ORDER BY r.source_row_number LIMIT 1"""
    ).fetchone()
    if lineage is None:
        failures.append("No order-to-source lineage sample could be resolved")
        lineage_sample = None
    else:
        lineage_sample = {
            "source_file": lineage[0], "source_file_sha256": lineage[1],
            "source_row_number": lineage[2], "payload_sha256": lineage[3],
            "business_key_redacted": True,
        }

    return {
        "status": "failed" if failures else "passed",
        "dataset_ref": DATASET_REF,
        "source_version": 2,
        "license": LICENSE,
        "approved_use": profile["approved_use"],
        "already_loaded": already_loaded,
        "provenance": {
            **git_identity(),
            "source_profile_canonical_sha256": hashlib.sha256(canonical_json(profile).encode("utf-8")).hexdigest(),
            "loader_sha256": sha256_file(Path(__file__).resolve()),
            "migration_sha256": sha256_file(MIGRATION_PATH),
        },
        "excluded_source_files": EXCLUDED_FILES,
        "source_occurrences": sum(item["actual"] for item in source_occurrence_counts.values()),
        "source_occurrence_counts": source_occurrence_counts,
        "fact_counts": counts,
        "monetary_reconciliation": monetary,
        "order_summary": {
            "rows": summary[0],
            "item_value_total": str(summary[1]),
            "freight_total": str(summary[2]),
            "payment_total": str(summary[3]),
            "one_row_per_order": summary[0] == order_count,
        },
        "multiplicity_preserved": {
            "orders_with_multiple_sellers": multi_seller_orders,
            "orders_with_multiple_review_rows": multi_review_orders,
            "duplicate_review_id_extra_rows": duplicate_review_id_extra_rows,
        },
        "lineage_sample": lineage_sample,
        "failures": failures,
    }


def load(data_dir: Path, profile_path: Path, dsn: str) -> dict[str, Any]:
    profile, paths = validated_inputs(data_dir.expanduser().resolve(), profile_path.resolve())
    with psycopg.connect(dsn) as conn:
        if not conn.info.dbname.startswith("backintel_"):
            raise ValueError("Refusing to modify a database not explicitly named with the backintel_ prefix.")
        apply_migration(conn)
        with conn.transaction():
            existing = _existing_load(conn, profile)
            if existing is not None:
                if existing["status"] != "passed":
                    raise RuntimeError("Existing Olist load fails reconciliation; refusing to modify it.")
                return existing
            batches = _register_batches(conn, profile, paths)
            for filename in IMPORTED_FILES:
                loaded = _copy_source_records(conn, filename, paths[filename], profile, batches[filename])
                if loaded != profile["files"][filename]["rows"]:
                    raise ValueError(f"Source occurrence count mismatch for {filename}")
            for filename in FACT_LOAD_ORDER:
                loaded = _copy_facts(conn, filename, paths[filename], batches[filename])
                if loaded != profile["files"][filename]["rows"]:
                    raise ValueError(f"Canonical fact count mismatch for {filename}")
            report = reconcile(conn, profile)
            if report["status"] != "passed":
                raise RuntimeError("Olist facts failed reconciliation: " + "; ".join(report["failures"]))
            return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR, help="External OlistV2 directory; source data stays outside Git.")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT, help="Durable JSON report path; defaults outside the repository.")
    args = parser.parse_args()
    dsn = os.environ.get("BACKINTEL_DATABASE_URL")
    if not dsn:
        print("BACKINTEL_DATABASE_URL is required; use a dedicated BackIntel application database.", file=sys.stderr)
        return 2
    try:
        report = load(args.data_dir, PROFILE_PATH, dsn)
        output = args.report.expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0 if report["status"] == "passed" else 1
    except (OSError, ValueError, KeyError, psycopg.Error, RuntimeError, json.JSONDecodeError) as error:
        print(json.dumps({"status": "failed", "summary": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
