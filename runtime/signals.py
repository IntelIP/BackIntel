"""Aggregate accepted Jev observations into source-attributed, versioned signals."""
from __future__ import annotations

import json
import statistics
import uuid
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from runtime.ledger import dsn

SIGNAL_VERSION = "review-signals-v2"


def _mean(values: list[float]) -> float | None:
    return round(statistics.fmean(values), 6) if values else None


def _metrics(rows: list[tuple]) -> dict[str, Any]:
    delivery, product, severity = [], [], []
    themes: dict[str, int] = {}
    for answers, *_ in rows:
        answers = answers if isinstance(answers, dict) else json.loads(answers)
        d = answers.get("mentions_delivery_problem", {})
        p = answers.get("mentions_product_problem", {})
        s = answers.get("reported_experience_severity", {})
        theme = answers.get("primary_expressed_theme", {})
        if d.get("noul") is not None: delivery.append(float(d["noul"]))
        if p.get("noul") is not None: product.append(float(p["noul"]))
        if s.get("score") is not None: severity.append(float(s["score"]))
        if theme.get("choice"):
            key = str(theme["choice"])
            themes[key] = themes.get(key, 0) + 1
    return {
        "delivery_mention_mean_probability": _mean(delivery),
        "product_problem_mention_mean_probability": _mean(product),
        "reported_experience_mean_score": _mean(severity),
        "primary_expressed_theme_counts": dict(sorted(themes.items())),
        "meaning_note": "Aggregates Jev judgments about review text; not verified events, seller responsibility, or calibrated operational probabilities.",
    }


async def build_signal_snapshot(partition_id: str) -> dict:
    async with await psycopg.AsyncConnection.connect(dsn()) as conn:
        part = await (await conn.execute(
            "SELECT disposition FROM backintel.partition_results WHERE partition_id=%s", (partition_id,))).fetchone()
        if not part or part[0] != "accepted":
            raise ValueError("Signal snapshot requires an accepted review partition")
        versions = await (await conn.execute(
            "SELECT DISTINCT question_set_version FROM backintel.jev_observations WHERE partition_id=%s",
            (partition_id,))).fetchall()
        if len(versions) != 1:
            raise ValueError("Partition must contain observations from exactly one question-set version")
        version = versions[0][0]
        rows = await (await conn.execute("""
            WITH sellers AS (
              SELECT order_id,
                     CASE WHEN bool_and(seller_id IS NOT NULL)
                          THEN count(DISTINCT seller_id)::int ELSE 0 END AS n,
                     min(seller_id) AS entity_key
                FROM backintel.order_items GROUP BY order_id
            ), categories AS (
              SELECT i.order_id,
                     CASE WHEN bool_and(p.category_name IS NOT NULL)
                          THEN count(DISTINCT p.category_name)::int ELSE 0 END AS n,
                     min(p.category_name) AS entity_key
                FROM backintel.order_items i LEFT JOIN backintel.products p USING (product_id)
               GROUP BY i.order_id
            )
            SELECT o.answers, r.order_id, s.n AS seller_n, s.entity_key AS seller_key,
                   c.n AS category_n, c.entity_key AS category_key
              FROM backintel.jev_observations o
              JOIN backintel.reviews r USING (review_record_id)
              LEFT JOIN sellers s USING (order_id)
              LEFT JOIN categories c USING (order_id)
             WHERE o.partition_id=%s AND o.question_set_version=%s
             ORDER BY o.review_record_id
        """, (partition_id, version))).fetchall()

    if not rows:
        raise ValueError("Accepted partition has no observations")
    groups: dict[tuple[str, str], list[tuple]] = {("marketplace", "*"): rows}
    for row in rows:
        if row[2] == 1 and row[3] is not None:
            groups.setdefault(("seller", str(row[3])), []).append(row)
        if row[2] == 1 and row[4] == 1 and row[5] is not None:
            groups.setdefault(("category", str(row[5])), []).append(row)

    snapshots = []
    for (entity_type, entity_key), members in sorted(groups.items()):
        metrics = _metrics(members)
        async with await psycopg.AsyncConnection.connect(dsn()) as conn:
            await conn.execute("""
                INSERT INTO backintel.semantic_signal_snapshots
                  (snapshot_id, partition_id, question_set_version, signal_version, entity_type, entity_key, review_count, metrics)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (partition_id, question_set_version, signal_version, entity_type, entity_key) DO NOTHING
            """, (uuid.uuid4(), partition_id, version, SIGNAL_VERSION, entity_type, entity_key, len(members), Jsonb(metrics)))
            stored = await (await conn.execute("""
                SELECT review_count, metrics FROM backintel.semantic_signal_snapshots
                WHERE partition_id=%s AND question_set_version=%s AND signal_version=%s
                  AND entity_type=%s AND entity_key=%s
            """, (partition_id, version, SIGNAL_VERSION, entity_type, entity_key))).fetchone()
            stored_metrics = stored[1] if isinstance(stored[1], dict) else json.loads(stored[1])
            if stored[0] != len(members) or stored_metrics != metrics:
                raise ValueError("Immutable signal snapshot conflicts with recomputed partition result")
        snapshots.append({"entity_type": entity_type, "entity_key": entity_key,
                          "review_count": len(members), "metrics": metrics})
    return {"partition_id": partition_id, "question_set_version": version, "signal_version": SIGNAL_VERSION,
            "snapshot_count": len(snapshots), "snapshots": snapshots}


async def compare_signal_snapshots(previous_partition: str, current_partition: str) -> dict:
    if previous_partition == current_partition:
        raise ValueError("Comparison requires two different partition IDs")
    async with await psycopg.AsyncConnection.connect(dsn()) as conn:
        previous = await (await conn.execute("""
            SELECT entity_type, entity_key, review_count, metrics, question_set_version
              FROM backintel.semantic_signal_snapshots WHERE partition_id=%s AND signal_version=%s
        """, (previous_partition, SIGNAL_VERSION))).fetchall()
        current = await (await conn.execute("""
            SELECT entity_type, entity_key, review_count, metrics, question_set_version
              FROM backintel.semantic_signal_snapshots WHERE partition_id=%s AND signal_version=%s
        """, (current_partition, SIGNAL_VERSION))).fetchall()
    if not previous or not current:
        raise ValueError("Both partitions require accepted snapshots at the current signal version")
    old = {(r[0], r[1]): r for r in previous}
    new = {(r[0], r[1]): r for r in current}
    shared = sorted(set(old) & set(new), key=lambda key: ({"marketplace": 0, "seller": 1, "category": 2}[key[0]], key[1]))
    findings = []
    for entity_type, entity_key in shared:
        before, after = old[(entity_type, entity_key)], new[(entity_type, entity_key)]
        if before[4] != after[4]:
            raise ValueError("Cannot compare different question-set versions")
        before_metrics = before[3] if isinstance(before[3], dict) else json.loads(before[3])
        after_metrics = after[3] if isinstance(after[3], dict) else json.loads(after[3])
        b = before_metrics.get("delivery_mention_mean_probability")
        a = after_metrics.get("delivery_mention_mean_probability")
        findings.append({"entity_type": entity_type, "entity_key": entity_key,
                         "previous_review_count": before[2], "current_review_count": after[2],
                         "previous_mean_probability": b, "current_mean_probability": a,
                         "mean_model_probability_delta": round(a-b, 6) if a is not None and b is not None else None,
                         "mean_model_probability_delta_points": round((a-b)*100, 3) if a is not None and b is not None else None,
                         "previous_theme_counts": before_metrics.get("primary_expressed_theme_counts", {}),
                         "current_theme_counts": after_metrics.get("primary_expressed_theme_counts", {}),
                         "interpretation": "Difference in mean Jev-assigned probability that sampled text mentions delivery problems; not an observed complaint rate, verified delivery event, seller responsibility, or operational outcome probability."})
    return {"previous_partition": previous_partition, "current_partition": current_partition,
            "signal_version": SIGNAL_VERSION,
            "shared_entities_compared": len(findings), "findings": findings}
