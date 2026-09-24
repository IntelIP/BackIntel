#!/usr/bin/env python3
"""Check the committed Olist source-profile contract without Kaggle data access."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROFILE = ROOT / "data" / "profiles" / "olist-v2" / "source-manifest-profile.json"
ARCHIVE_SHA256 = "967e41e04fc306fe604e2a693f488995a8b41e5047418f8a5c8e4abd6deca784"
EXPECTED_FILES = {
    "olist_customers_dataset.csv",
    "olist_geolocation_dataset.csv",
    "olist_order_items_dataset.csv",
    "olist_order_payments_dataset.csv",
    "olist_order_reviews_dataset.csv",
    "olist_orders_dataset.csv",
    "olist_products_dataset.csv",
    "olist_sellers_dataset.csv",
    "product_category_name_translation.csv",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def main() -> None:
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    require(profile.get("ref") == "olistbr/brazilian-ecommerce", "Unexpected dataset identity")
    require(profile.get("license") == "CC BY-NC-SA 4.0", "Dataset license missing or changed")
    require("non-commercial local prototype/demo only" in profile.get("approved_use", ""), "Approved-use boundary missing")
    require(profile.get("archive", {}).get("sha256") == ARCHIVE_SHA256, "Approved archive fingerprint changed")
    require(set(profile.get("files", {})) == EXPECTED_FILES, "Dataset file inventory differs")
    for name, item in profile["files"].items():
        require(item.get("rows", 0) > 0, f"{name}: row count missing")
        require(item.get("bytes", 0) > 0, f"{name}: byte count missing")
        require(len(item.get("sha256", "")) == 64, f"{name}: SHA-256 missing")
        require(bool(item.get("headers")), f"{name}: schema headers missing")
        require("empty_cells_by_column" in item, f"{name}: null profile missing")
        require("duplicate_extra_rows_by_candidate_key" in item, f"{name}: candidate-key profile missing")
    tool = profile.get("profile_tool", {})
    script = ROOT / tool.get("path", "")
    require(script.is_file(), "Reproducible profile script is missing")
    require(hashlib.sha256(script.read_bytes()).hexdigest() == tool.get("sha256"), "Profile manifest is stale for the current profiler code")
    relationships = profile["relationship_profile"]
    require(relationships["orders"]["rows"] == relationships["orders"]["unique_order_ids"], "Order grain is not unique")
    require(relationships["order_items"]["item_order_ids_not_in_orders"] == 0, "Orphan order-item references exist")
    require(relationships["order_items"]["item_seller_ids_not_in_sellers"] == 0, "Unknown seller references exist")
    require(relationships["order_items"]["item_product_ids_not_in_products"] == 0, "Unknown product references exist")
    require(relationships["payments"]["payment_order_ids_not_in_orders"] == 0, "Orphan payment references exist")
    require(relationships["reviews"]["review_order_ids_not_in_orders"] == 0, "Orphan review references exist")
    require(relationships["order_items"]["orders_with_multiple_sellers"] > 0, "Multi-seller attribution risk not represented")
    require(relationships["reviews"]["orders_with_multiple_review_rows"] > 0, "Multi-review grain not represented")
    language = profile.get("review_language", {})
    require(language.get("expected") == "Portuguese (Brazil)" and language.get("language_detection_performed") is False, "Review-language uncertainty missing")
    require(language.get("observed_nonblank_comment_rows") == relationships["reviews"]["rows_with_nonblank_review_comment"], "Review-language coverage count is inconsistent")
    trace = relationships.get("source_row_trace")
    require(trace is not None, "A privacy-minimized source-row trace is missing")
    require(trace["source_file"] == "olist_orders_dataset.csv", "Sample trace points at an unexpected file")
    require(trace["source_file_sha256"] == profile["files"][trace["source_file"]]["sha256"], "Sample trace file hash does not match the profile")
    require(trace["schema_columns"] == profile["files"][trace["source_file"]]["headers"], "Sample trace schema does not match the measured file schema")
    require(trace["record_key_handling"] == "raw identifier omitted from the committed profile artifact", "Sample trace must not expose the raw record key")
    require(trace["label_is_feature"] is False, "Retrospective label is incorrectly marked as a feature")
    target = relationships["delivery_target_candidate"]
    require(target.get("decision", "").startswith("candidate only"), "Delivery target was incorrectly promoted")
    require("cannot prove exactly when" in target.get("availability_caveat", ""), "Historical availability caveat missing")
    require(target["late_by_actual_after_estimated_in_eligible_subset"] <= target["delivered_with_approval_and_both_outcome_timestamps"], "Target count exceeds eligible population")
    require(0 <= target["late_rate_in_eligible_subset"] <= 1, "Target rate is outside [0,1]")
    expected_rate = target["late_by_actual_after_estimated_in_eligible_subset"] / target["delivered_with_approval_and_both_outcome_timestamps"]
    require(abs(target["late_rate_in_eligible_subset"] - expected_rate) < 1e-12, "Target rate does not match counts")
    print(json.dumps({"status": "passed", "summary": "Olist source-profile contract is internally consistent.", "files": len(profile["files"]), "orders": relationships["orders"]["rows"], "archive_sha256": profile["archive"]["sha256"]}))


if __name__ == "__main__":
    try:
        main()
    except (KeyError, OSError, ValueError, json.JSONDecodeError) as error:
        print(json.dumps({"status": "failed", "summary": str(error)}))
        raise SystemExit(1)
