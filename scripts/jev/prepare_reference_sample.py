#!/usr/bin/env python3
"""Export a small, stratified Olist review set for human adjudication (never Git)."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from runtime.ledger import dsn  # noqa: E402
import psycopg  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--per-score", type=int, default=4)
    parser.add_argument("--month", help="optional YYYY-MM source review month for a demo batch")
    args = parser.parse_args()
    output = args.out.expanduser().resolve()
    if output.is_relative_to(ROOT):
        parser.error("review text is licensed data; output must be outside the Git checkout")
    if not 1 <= args.per_score <= 20:
        parser.error("--per-score must be between 1 and 20")

    month_start = month_end = None
    if args.month:
        try:
            month_start = dt.date.fromisoformat(args.month + "-01")
        except ValueError:
            parser.error("--month must use YYYY-MM")
        month_end = (month_start.replace(day=28) + dt.timedelta(days=4)).replace(day=1)
    with psycopg.connect(dsn()) as conn:
        if month_start:
            rows = conn.execute("""
                SELECT r.review_record_id, r.score, r.message, sb.file_sha256, r.source_row_number, r.created_at
                  FROM backintel.reviews r
                  JOIN backintel.source_batches sb ON sb.batch_id=r.source_batch_id
                 WHERE r.message IS NOT NULL AND r.message ~ '[^[:space:]]' AND r.score BETWEEN 1 AND 5
                   AND r.created_at >= %s AND r.created_at < %s
                 ORDER BY r.score, md5(sb.file_sha256 || ':' || r.source_row_number::text)
            """, (month_start, month_end)).fetchall()
        else:
            rows = conn.execute("""
                SELECT r.review_record_id, r.score, r.message, sb.file_sha256, r.source_row_number, r.created_at
                  FROM backintel.reviews r
                  JOIN backintel.source_batches sb ON sb.batch_id=r.source_batch_id
                 WHERE r.message IS NOT NULL AND r.message ~ '[^[:space:]]' AND r.score BETWEEN 1 AND 5
                 ORDER BY r.score, md5(sb.file_sha256 || ':' || r.source_row_number::text)
            """).fetchall()
    chosen = []
    counts = {score: 0 for score in range(1, 6)}
    for row in rows:
        if counts[row[1]] < args.per_score:
            chosen.append(row)
            counts[row[1]] += 1
    records = []
    for review_id, score, message, file_hash, source_row, created_at in chosen:
        records.append({
            "review_month": created_at.strftime("%Y-%m"),
            "review_record_id": review_id,
            "source_file_sha256": file_hash.strip(),
            "source_row_number": source_row,
            "review_score": score,
            "source_language": "pt-BR-assumed-from-dataset; not independently detected",
            "text": message,
            "reference_labels": {
                "mentions_delivery_problem": None,
                "mentions_product_problem": None,
                "primary_expressed_theme": None,
                "reported_experience_severity": None,
                "rationale": None,
            },
            "annotation_status": "pending_human_review",
        })
    sample = {
        "schema": "backintel-jev-reference-sample/v1",
        "dataset": "olistbr/brazilian-ecommerce@2",
        "source_license": "CC BY-NC-SA 4.0; non-commercial local prototype/demo only",
        "selection": (f"deterministic hash-stratified sample from review month {args.month}, across available 1-5 star scores" if args.month else "deterministic hash-stratified sample across available 1-5 star scores"),
        "per_score_requested": args.per_score,
        "selected_count": len(records),
        "selected_by_score": {str(k): v for k, v in counts.items()},
        "question_set": "review-text-v1",
        "warning": "Unlabeled until a human annotator reviews the original Portuguese. Do not treat model output or assistant prelabels as gold labels.",
        "sample_sha256": hashlib.sha256(json.dumps(records, ensure_ascii=False, sort_keys=True).encode()).hexdigest(),
        "records": records,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(sample, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "prepared_unlabeled", "path": str(output), "records": len(records),
                      "by_score": sample["selected_by_score"], "sample_sha256": sample["sample_sha256"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
