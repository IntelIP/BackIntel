from __future__ import annotations

import csv
import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

import psycopg
from psycopg.conninfo import conninfo_to_dict

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "data"))
from seller_review import build_report, render_html, next_month  # noqa: E402
from load_olist_facts import (  # noqa: E402
    DATASET_REF,
    EXCLUDED_FILES,
    IMPORTED_FILES,
    LICENSE,
    load,
)

CSV_ROWS = {
    "olist_customers_dataset.csv": (
        ["customer_id", "customer_unique_id", "customer_zip_code_prefix", "customer_city", "customer_state"],
        [
            {"customer_id": "c1", "customer_unique_id": "u1", "customer_zip_code_prefix": "00123", "customer_city": "A", "customer_state": "SP"},
            {"customer_id": "c2", "customer_unique_id": "u2", "customer_zip_code_prefix": "00456", "customer_city": "B", "customer_state": "RJ"},
        ],
    ),
    "olist_sellers_dataset.csv": (
        ["seller_id", "seller_zip_code_prefix", "seller_city", "seller_state"],
        [
            {"seller_id": "s1", "seller_zip_code_prefix": "01001", "seller_city": "A", "seller_state": "SP"},
            {"seller_id": "s2", "seller_zip_code_prefix": "02002", "seller_city": "B", "seller_state": "RJ"},
        ],
    ),
    "olist_products_dataset.csv": (
        ["product_id", "product_category_name", "product_name_lenght", "product_description_lenght", "product_photos_qty", "product_weight_g", "product_length_cm", "product_height_cm", "product_width_cm"],
        [
            {"product_id": "p1", "product_category_name": "cat-a", "product_name_lenght": "10", "product_description_lenght": "20", "product_photos_qty": "1", "product_weight_g": "300", "product_length_cm": "10", "product_height_cm": "5", "product_width_cm": "3"},
            {"product_id": "p2", "product_category_name": "cat-b", "product_name_lenght": "11", "product_description_lenght": "21", "product_photos_qty": "2", "product_weight_g": "400", "product_length_cm": "11", "product_height_cm": "6", "product_width_cm": "4"},
        ],
    ),
    "olist_orders_dataset.csv": (
        ["order_id", "customer_id", "order_status", "order_purchase_timestamp", "order_approved_at", "order_delivered_carrier_date", "order_delivered_customer_date", "order_estimated_delivery_date"],
        [
            {"order_id": "o1", "customer_id": "c1", "order_status": "delivered", "order_purchase_timestamp": "2017-01-01 10:00:00", "order_approved_at": "2017-01-01 10:05:00", "order_delivered_carrier_date": "2017-01-02 10:00:00", "order_delivered_customer_date": "2017-01-05 10:00:00", "order_estimated_delivery_date": "2017-01-04 10:00:00"},
            {"order_id": "o2", "customer_id": "c2", "order_status": "delivered", "order_purchase_timestamp": "2017-02-02 10:00:00", "order_approved_at": "2017-02-02 10:05:00", "order_delivered_carrier_date": "2017-02-03 10:00:00", "order_delivered_customer_date": "2017-02-06 10:00:00", "order_estimated_delivery_date": "2017-02-07 10:00:00"},
        ],
    ),
    "product_category_name_translation.csv": (
        ["product_category_name", "product_category_name_english"],
        [
            {"product_category_name": "cat-a", "product_category_name_english": "category a"},
            {"product_category_name": "cat-b", "product_category_name_english": "category b"},
        ],
    ),
    "olist_order_items_dataset.csv": (
        ["order_id", "order_item_id", "product_id", "seller_id", "shipping_limit_date", "price", "freight_value"],
        [
            {"order_id": "o1", "order_item_id": "1", "product_id": "p1", "seller_id": "s1", "shipping_limit_date": "2017-01-02 10:00:00", "price": "10.00", "freight_value": "2.00"},
            {"order_id": "o1", "order_item_id": "2", "product_id": "p2", "seller_id": "s2", "shipping_limit_date": "2017-01-02 10:00:00", "price": "20.00", "freight_value": "3.00"},
            {"order_id": "o2", "order_item_id": "1", "product_id": "p1", "seller_id": "s1", "shipping_limit_date": "2017-01-03 10:00:00", "price": "5.00", "freight_value": "1.00"},
        ],
    ),
    "olist_order_payments_dataset.csv": (
        ["order_id", "payment_sequential", "payment_type", "payment_installments", "payment_value"],
        [
            {"order_id": "o1", "payment_sequential": "1", "payment_type": "credit_card", "payment_installments": "1", "payment_value": "11.00"},
            {"order_id": "o1", "payment_sequential": "2", "payment_type": "voucher", "payment_installments": "0", "payment_value": "24.00"},
            {"order_id": "o2", "payment_sequential": "1", "payment_type": "credit_card", "payment_installments": "1", "payment_value": "6.00"},
        ],
    ),
    "olist_order_reviews_dataset.csv": (
        ["review_id", "order_id", "review_score", "review_comment_title", "review_comment_message", "review_creation_date", "review_answer_timestamp"],
        [
            {"review_id": "r1", "order_id": "o1", "review_score": "5", "review_comment_title": "good", "review_comment_message": "works", "review_creation_date": "2017-01-06 10:00:00", "review_answer_timestamp": "2017-01-06 11:00:00"},
            {"review_id": "r2", "order_id": "o1", "review_score": "3", "review_comment_title": "late", "review_comment_message": "late delivery", "review_creation_date": "2017-01-06 10:00:00", "review_answer_timestamp": "2017-01-06 11:00:00"},
            {"review_id": "r1", "order_id": "o2", "review_score": "4", "review_comment_title": "fine", "review_comment_message": "", "review_creation_date": "2017-01-07 10:00:00", "review_answer_timestamp": "2017-01-07 11:00:00"},
        ],
    ),
}


class OlistFactsIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.dsn = os.environ.get("BACKINTEL_TEST_DATABASE_URL")
        if not cls.dsn:
            raise RuntimeError("BACKINTEL_TEST_DATABASE_URL is required; facts integration tests must not silently skip.")
        database = conninfo_to_dict(cls.dsn).get("dbname", "")
        if not (database.endswith("_test") or database.startswith("test_")):
            raise RuntimeError("Refusing destructive integration setup: test database name must start test_ or end _test.")
        cls.temp = tempfile.TemporaryDirectory(prefix="BackIntelOlistFacts-")
        cls.root = Path(cls.temp.name)
        cls.data_dir = cls.root / "source"
        cls.csv_dir = cls.data_dir / "csv"
        cls.csv_dir.mkdir(parents=True)
        cls.profile_path = cls.root / "source-profile.json"
        cls.report = cls.root / "report.json"
        cls.profile = cls._write_fixture()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp.cleanup()

    @classmethod
    def _write_fixture(cls) -> dict:
        files = {}
        for name, (headers, rows) in CSV_ROWS.items():
            path = cls.csv_dir / name
            with path.open("w", encoding="utf-8", newline="") as output:
                writer = csv.DictWriter(output, fieldnames=headers)
                writer.writeheader()
                writer.writerows(rows)
            raw = path.read_bytes()
            duplicates = {}
            if name == "olist_order_reviews_dataset.csv":
                duplicates = {"review_id": 1}
            files[name] = {
                "rows": len(rows), "headers": headers, "bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "duplicate_extra_rows_by_candidate_key": duplicates,
            }
        archive = cls.data_dir / "fixture.zip"
        archive.write_bytes(b"synthetic-test-source-only")
        archive_sha = hashlib.sha256(archive.read_bytes()).hexdigest()
        profile = {
            "ref": DATASET_REF,
            "license": LICENSE,
            "approved_use": "non-commercial local prototype/demo only; synthetic test fixture",
            "kaggle_current_version_verified": 2,
            "archive": {"name": archive.name, "sha256": archive_sha},
            "files": files,
            "relationship_profile": {
                "order_items": {"orders_with_multiple_sellers": 1},
                "reviews": {"orders_with_multiple_review_rows": 1},
            },
        }
        cls.profile_path.write_text(json.dumps(profile, indent=2), encoding="utf-8")
        return profile

    def setUp(self) -> None:
        with psycopg.connect(self.dsn) as conn:
            conn.execute("DROP SCHEMA IF EXISTS backintel CASCADE")

    def test_load_preserves_grains_and_reconciles_without_join_inflation(self) -> None:
        report = load(self.data_dir, self.profile_path, self.dsn)
        self.assertEqual(report["status"], "passed", report["failures"])
        self.assertFalse(report["already_loaded"])
        self.assertEqual(report["source_occurrences"], 19)
        self.assertEqual(report["source_occurrence_counts"]["olist_order_reviews_dataset.csv"]["actual"], 3)
        self.assertEqual(report["fact_counts"]["orders"]["fact_rows"], 2)
        self.assertEqual(report["fact_counts"]["order_items"]["fact_rows"], 3)
        self.assertEqual(report["fact_counts"]["payments"]["fact_rows"], 3)
        self.assertEqual(report["fact_counts"]["reviews"]["fact_rows"], 3)
        self.assertEqual(report["multiplicity_preserved"]["orders_with_multiple_sellers"], 1)
        self.assertEqual(report["multiplicity_preserved"]["orders_with_multiple_review_rows"], 1)
        self.assertEqual(report["multiplicity_preserved"]["duplicate_review_id_extra_rows"], 1)
        self.assertEqual(report["monetary_reconciliation"]["item_value_total"]["canonical_fact_total"], "35.00")
        self.assertEqual(report["monetary_reconciliation"]["payment_total"]["canonical_fact_total"], "41.00")
        self.assertEqual(report["order_summary"]["rows"], 2)
        self.assertTrue(report["order_summary"]["one_row_per_order"])
        self.assertEqual(set(report["excluded_source_files"]), set(EXCLUDED_FILES))
        self.assertTrue(report["lineage_sample"]["business_key_redacted"])

        with psycopg.connect(self.dsn) as conn:
            naive = conn.execute(
                """SELECT sum(i.price), sum(p.payment_value)
                   FROM backintel.orders o
                   JOIN backintel.order_items i USING (order_id)
                   JOIN backintel.payments p USING (order_id)
                   JOIN backintel.reviews r USING (order_id)
                   WHERE o.order_id = 'o1'"""
            ).fetchone()
            correct = conn.execute(
                "SELECT item_value_total, payment_total FROM backintel.order_summary WHERE order_id = 'o1'"
            ).fetchone()
        self.assertEqual(correct, (30, 35))
        self.assertEqual(naive, (120, 140))

    def test_repeat_load_is_idempotent_and_does_not_duplicate_facts(self) -> None:
        first = load(self.data_dir, self.profile_path, self.dsn)
        second = load(self.data_dir, self.profile_path, self.dsn)
        self.assertEqual(first["status"], "passed")
        self.assertTrue(second["already_loaded"])
        self.assertEqual(second["fact_counts"], first["fact_counts"])

    def test_monthly_review_counts_once_and_keeps_multi_seller_out(self) -> None:
        load(self.data_dir, self.profile_path, self.dsn)
        contract = {
            "dataset_ref": DATASET_REF,
            "comparison_purchase_month": "2017-01",
            "report_purchase_month": "2017-02",
            "minimum_comparable_seller_orders": 1,
            "min_delivered_orders_per_month": 1,
            "license_boundary": "synthetic fixture",
        }
        with psycopg.connect(self.dsn) as conn:
            report = build_report(conn, contract)
        jan, feb = report["marketplace"]
        self.assertEqual((jan["delivered_orders"], jan["late_orders"], jan["review_rows"], jan["orders_with_review"]), (1, 1, 2, 1))
        self.assertEqual((feb["delivered_orders"], feb["late_orders"], feb["review_rows"]), (1, 0, 1))
        self.assertFalse([r for r in report["seller_metrics"] if r["purchase_month"] == "2017-01"])
        self.assertFalse([r for r in report["category_metrics"] if r["purchase_month"] == "2017-01"])
        self.assertEqual(len(report["findings"]), 0)
        self.assertIn("No sellers met", render_html(report))
        dangerous = {**report, "limitations": ["<script>alert(1)</script>"]}
        rendered = render_html(dangerous)
        self.assertIn("&lt;script&gt;", rendered)
        self.assertNotIn("<script>", rendered)
        report["semantic_review"] = {
            "signal_version": "review-signals-v2", "execution_mode": "recorded fixture; no inference",
            "interpretation": "Selected sample, not a population trend.",
            "comparison": {"findings": [{"entity_type": "marketplace", "entity_key": "*",
                "previous_review_count": 1, "current_review_count": 1,
                "mean_model_probability_delta_points": 20.8}]},
            "source_evidence": [{"review_record_id": 1, "order_id": "<script>alert(1)</script>",
                "source_file": "synthetic.csv", "source_row_number": 17, "file_sha256": "a" * 64,
                "model": "synthetic-fixture", "request_id": "fixture-1", "question_set_version": "review-text-v1"}],
        }
        integrated = render_html(report)
        self.assertIn("What changed in sampled review text?", integrated)
        self.assertIn("20.8 points", integrated)
        self.assertIn("synthetic.csv, row 17", integrated)
        self.assertNotIn("<script>", integrated)
        self.assertIn("Total cost remains blocked", integrated)
        self.assertEqual(next_month("2017-12").isoformat(), "2018-01-01")

    def test_source_records_cannot_be_updated_or_deleted(self) -> None:
        load(self.data_dir, self.profile_path, self.dsn)
        with psycopg.connect(self.dsn) as conn:
            with self.assertRaises(psycopg.errors.RaiseException):
                with conn.transaction():
                    conn.execute("UPDATE backintel.source_records SET payload = '{}'::jsonb")
            with self.assertRaises(psycopg.errors.RaiseException):
                with conn.transaction():
                    conn.execute("DELETE FROM backintel.source_batches")


if __name__ == "__main__":
    unittest.main()
