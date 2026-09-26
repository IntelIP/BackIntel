"""Publish a local review package from accepted facts and versioned observations."""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path

import psycopg

from runtime.costs import summary
from runtime.ledger import dsn
from runtime.signals import SIGNAL_VERSION
from scripts.data.seller_review import build_report, read_contract, render_html


def publish_review(comparison: dict, *, reuse_only: bool) -> dict:
    partitions = [comparison["previous_partition"], comparison["current_partition"]]
    with psycopg.connect(dsn()) as conn:
        report = build_report(conn, read_contract())
        report["generated_at"] = conn.execute(
            "SELECT max(updated_at) FROM backintel.partition_results WHERE partition_id=ANY(%s)",
            (partitions,)).fetchone()[0].isoformat()
        evidence = [dict(zip(("partition_id", "observation_id", "review_record_id", "order_id",
                             "source_file", "file_sha256", "source_row_number", "input_text_sha256",
                             "question_set_version", "model", "request_id"), row))
                    for row in conn.execute("""
            SELECT o.partition_id, o.observation_id::text, r.review_record_id, r.order_id,
                   s.source_file, s.file_sha256, r.source_row_number, o.input_text_sha256,
                   o.question_set_version, o.model, o.request_id
            FROM backintel.jev_observations o
            JOIN backintel.reviews r USING (review_record_id)
            JOIN backintel.source_batches s ON s.batch_id=r.source_batch_id
            WHERE o.partition_id = ANY(%s)
            ORDER BY o.partition_id, r.review_record_id
        """, (partitions,)).fetchall()]
    if not evidence or not comparison["findings"]:
        raise ValueError("Review requires a comparable accepted signal and source evidence")
    report["limitations"] = [s for s in report["limitations"] if not s.startswith("No Jev")]
    report["limitations"] += [
        "Semantic observations describe small selected review samples, not representative complaint rates or verified causes.",
        "Human reference labels, manager acceptance, human-time savings, and total cost remain unverified.",
    ]
    report["semantic_review"] = {
        "signal_version": SIGNAL_VERSION,
        "execution_mode": "reuse of recorded observations; no provider calls" if reuse_only else "live enrichment",
        "interpretation": "Change in mean Jev-assigned probability that sampled text mentions delivery problems. "
                          "Not a population trend, observed complaint rate, or seller responsibility. "
                          "Unknown categories and multi-seller orders remain outside category attribution.",
        "comparison": comparison,
        "source_evidence": evidence,
        "costs": [summary(partition) for partition in partitions],
    }
    # Container builds carry their candidate identity; the validation receipt must
    # separately bind the executed image/files to this commit.
    build_sha = os.environ.get("BACKINTEL_CANDIDATE_SHA", "")
    if report["candidate"]["head_sha"] is None and re.fullmatch(r"[a-f0-9]{40}", build_sha):
        report["candidate"] = {"head_sha": build_sha, "exact_candidate_sha": build_sha,
                               "working_tree_clean": None, "identity_source": "runtime build argument"}
    root = Path(os.environ.get("BACKINTEL_REPORT_DIR", str(
        Path.home() / "Library/Application Support/BackIntel/Evidence/PoCReports"))).expanduser().resolve()
    if root.is_relative_to(Path(__file__).resolve().parents[1]):
        raise ValueError("Dataset-derived reports must stay outside the Git checkout")
    root.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(report, indent=2, ensure_ascii=False) + "\n").encode()
    digest = hashlib.sha256(payload).hexdigest()
    artifacts = []
    for suffix, content, media_type in [("json", payload, "application/json"),
                                        ("html", render_html(report).encode(), "text/html")]:
        path = root / f"seller-review-{digest}.{suffix}"
        # A content-derived name and exclusive creation keep earlier reports intact.
        with tempfile.NamedTemporaryFile(dir=root, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            try:
                os.link(temporary, path)
            except FileExistsError:
                if path.read_bytes() != content:
                    raise ValueError("Published report conflicts with existing artifact")
        finally:
            temporary.unlink()
        artifacts.append({"path": str(path), "sha256": hashlib.sha256(content).hexdigest(),
                          "bytes": len(content), "media_type": media_type})
    return {"status": "candidate_for_review", "candidate": report["candidate"],
            "signal_version": SIGNAL_VERSION, "source_examples": len(evidence),
            "total_cost_status": "blocked_unpriced_local_compute_and_human_review",
            "artifacts": artifacts}
