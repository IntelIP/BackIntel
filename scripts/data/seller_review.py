#!/usr/bin/env python3
"""Retrospective monthly seller/category review from reconciled Olist facts."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import psycopg

if __package__:
    from .load_olist_facts import git_identity
else:
    from load_olist_facts import git_identity

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config" / "seller-review-slice.json"
PROFILE = ROOT / "data" / "profiles" / "olist-v2" / "source-manifest-profile.json"
DEFAULT_OUTPUT = Path.home() / "Library" / "Application Support" / "BackIntel" / "Evidence" / "BINT5" / "seller-review.json"

# Aggregate each one-to-many child BEFORE joining to the one-order grain.
BASE = """
WITH item_context AS (
  SELECT i.order_id, count(DISTINCT i.seller_id) AS seller_count,
         min(i.seller_id) AS seller_id,
         count(DISTINCT coalesce(p.category_name, '<missing>')) AS category_count,
         min(p.category_name) AS category_name
  FROM backintel.order_items i JOIN backintel.products p USING (product_id)
  GROUP BY i.order_id
), review_context AS (
  SELECT order_id, count(*) AS review_rows,
         count(score) AS rated_rows,
         count(*) FILTER (WHERE nullif(btrim(message), '') IS NOT NULL) AS text_rows
  FROM backintel.reviews GROUP BY order_id
), eligible AS (
  SELECT o.order_id, o.purchased_at, o.delivered_at, o.estimated_delivery_at,
         o.source_batch_id, o.source_row_number,
         CASE WHEN i.seller_count = 1 THEN i.seller_id END AS seller_id,
         CASE WHEN i.seller_count = 1 AND i.category_count = 1
              THEN i.category_name END AS category_name,
         coalesce(r.review_rows, 0) AS review_rows,
         coalesce(r.rated_rows, 0) AS rated_rows,
         coalesce(r.text_rows, 0) AS text_rows
  FROM backintel.orders o
  LEFT JOIN item_context i USING (order_id)
  LEFT JOIN review_context r USING (order_id)
  WHERE o.status = 'delivered' AND o.purchased_at >= %(begin)s
    AND o.purchased_at < %(end)s
)
"""

METRICS = BASE + """
, scoped AS (
  SELECT 'marketplace' AS scope, 'all' AS entity_id, e.* FROM eligible e
  UNION ALL
  SELECT 'seller', seller_id, e.* FROM eligible e WHERE seller_id IS NOT NULL
  UNION ALL
  SELECT 'category', category_name, e.* FROM eligible e WHERE category_name IS NOT NULL
)
SELECT scope, entity_id, to_char(purchased_at, 'YYYY-MM') AS purchase_month,
       count(*) AS delivered_orders,
       count(*) FILTER (WHERE delivered_at IS NOT NULL AND estimated_delivery_at IS NOT NULL) AS dated_orders,
       count(*) FILTER (WHERE delivered_at > estimated_delivery_at AND delivered_at IS NOT NULL
                           AND estimated_delivery_at IS NOT NULL) AS late_orders,
       count(*) FILTER (WHERE review_rows > 0) AS orders_with_review,
       sum(review_rows) AS review_rows, sum(rated_rows) AS rated_review_rows,
       sum(text_rows) AS nonblank_text_rows
FROM scoped
GROUP BY scope, entity_id, purchase_month
ORDER BY scope, entity_id, purchase_month
"""

EVIDENCE = BASE + """
SELECT e.order_id, b.source_file, b.file_sha256, e.source_row_number,
       r.source_row_number AS review_row_number, r.score,
       r.message
FROM eligible e
JOIN backintel.source_batches b ON b.batch_id = e.source_batch_id
LEFT JOIN LATERAL (
  SELECT source_row_number, score, message FROM backintel.reviews
  WHERE order_id = e.order_id ORDER BY source_row_number LIMIT 1
) r ON true
WHERE e.seller_id = %(seller)s AND e.delivered_at > e.estimated_delivery_at
ORDER BY e.purchased_at, e.order_id LIMIT 2
"""


def next_month(month: str) -> date:
    first = date.fromisoformat(month + "-01")
    return date(first.year + (first.month == 12), first.month % 12 + 1, 1)


def read_contract() -> dict:
    contract = json.loads(CONFIG.read_text(encoding="utf-8"))
    actual = hashlib.sha256(PROFILE.read_bytes()).hexdigest()
    if actual != contract["profile_sha256"] or contract["dataset_ref"] != "olistbr/brazilian-ecommerce":
        raise ValueError("Frozen source-profile fingerprint differs from the approved report slice")
    earlier = contract["comparison_purchase_month"]
    later = contract["report_purchase_month"]
    if next_month(earlier).isoformat()[:7] != later:
        raise ValueError("Report months must be adjacent calendar months")
    return contract


def row_to_metric(row: tuple) -> dict:
    scope, entity, month, orders, dated, late, reviewed_orders, reviews, rated, text = row
    orders, dated, late, reviewed_orders, reviews, rated, text = map(
        int, (orders, dated, late, reviewed_orders, reviews, rated, text)
    )
    return {
        "scope": scope, "entity_id": entity, "purchase_month": month,
        "delivered_orders": orders, "dated_orders": dated, "late_orders": late,
        "late_delivery_rate": late / dated if dated else None,
        "orders_with_review": reviewed_orders,
        "review_rows": reviews, "rated_review_rows": rated, "nonblank_text_rows": text,
    }


def build_report(conn: psycopg.Connection, contract: dict) -> dict:
    begin = date.fromisoformat(contract["comparison_purchase_month"] + "-01")
    end = next_month(contract["report_purchase_month"])
    params = {"begin": begin, "end": end}
    with conn.transaction():
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        rows = [row_to_metric(r) for r in conn.execute(METRICS, params).fetchall()]
        by_key = {(r["scope"], r["entity_id"], r["purchase_month"]): r for r in rows}
        months = (contract["comparison_purchase_month"], contract["report_purchase_month"])
        marketplace = [by_key.get(("marketplace", "all", m)) for m in months]
        if not all(marketplace) or any(r["delivered_orders"] < contract["min_delivered_orders_per_month"] for r in marketplace):
            raise ValueError("Frozen period has insufficient delivered orders; do not pick a different period by findings")
        findings = []
        for r in rows:
            if r["scope"] != "seller" or r["purchase_month"] != months[1]:
                continue
            prior = by_key.get(("seller", r["entity_id"], months[0]))
            threshold = contract["minimum_comparable_seller_orders"]
            if not prior or min(prior["dated_orders"], r["dated_orders"]) < threshold:
                continue
            delta = r["late_delivery_rate"] - prior["late_delivery_rate"]
            if delta > 0:
                findings.append({"seller_id": r["entity_id"], "previous": prior,
                                 "current": r, "rate_change_percentage_points": round(delta * 100, 4)})
        findings.sort(key=lambda r: (-r["rate_change_percentage_points"], r["seller_id"]))
        findings = findings[:5]
        for finding in findings:
            samples = conn.execute(EVIDENCE, {**params, "seller": finding["seller_id"]}).fetchall()
            finding["source_examples"] = [
                {"order_id": order, "source_file": filename, "source_file_sha256": sha,
                 "order_row_number": ordinal, "review_row_number": review_ordinal,
                 "rating": score, "review_text": text}
                for order, filename, sha, ordinal, review_ordinal, score, text in samples
            ]
        batches = [dict(zip(("source_file", "file_sha256", "row_count"), r)) for r in conn.execute(
            "SELECT source_file, file_sha256, row_count FROM backintel.source_batches ORDER BY source_file"
        )]
    return {
        "status": "candidate_for_review",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "candidate": git_identity(),
        "dataset_ref": contract["dataset_ref"],
        "license_boundary": contract["license_boundary"],
        "contract": contract,
        "source_batches": batches,
        "metric_definitions": {
            "period": "Purchase-month cohort; retrospectively observed delivered orders in static Olist extract, not an as-of-month-end snapshot",
            "late_rate": "Delivered orders with actual customer delivery after estimated delivery / delivered orders with both timestamps",
            "seller_attribution": "Only orders with exactly one distinct seller; no causal assignment",
            "category_attribution": "Only orders with exactly one seller and one non-null product category; no causal assignment",
            "feedback": "Review coverage counts unique orders with >=1 review; rating and nonblank comment counts count review ROWS; missing text is unknown, not negative feedback",
            "finding": f"Up to five seller associations sorted by increase in late-rate percentage points with >={contract['minimum_comparable_seller_orders']} dated orders in BOTH months; no causal or predictive claim",
        },
        "marketplace": marketplace,
        "seller_metrics": [r for r in rows if r["scope"] == "seller"],
        "category_metrics": [r for r in rows if r["scope"] == "category"],
        "findings": findings,
        "limitations": [
            "Static historical export cannot establish what was known at each calendar month end.",
            "A single seller on an order does not prove that seller caused delivery lateness.",
            "No Jev review themes, model predictions, human-time measurements, or live operational actions in this report.",
        ],
    }


def render_html(report: dict) -> str:
    def esc(value: object) -> str:
        return html.escape(str(value), quote=True)

    def pct(n: int, d: int) -> str:
        return f"{100 * n / d:.2f}%" if d else "unknown"

    months = report["marketplace"]
    marketplace_rows = "".join(
        f"<tr><th>{esc(m['purchase_month'])}</th><td>{m['delivered_orders']:,}</td>"
        f"<td>{m['late_orders']:,} / {m['dated_orders']:,} ({pct(m['late_orders'], m['dated_orders'])})</td>"
        f"<td>{m['orders_with_review']:,} / {m['delivered_orders']:,}</td>"
        f"<td>{m['rated_review_rows']:,} / {m['review_rows']:,} review rows</td>"
        f"<td>{m['nonblank_text_rows']:,} / {m['review_rows']:,} review rows</td></tr>"
        for m in months
    )
    findings = report["findings"]
    findings_rows = "".join(
        f"<tr><td>{esc(f['seller_id'])}</td>"
        f"<td>{f['previous']['late_orders']} / {f['previous']['dated_orders']}</td>"
        f"<td>{f['current']['late_orders']} / {f['current']['dated_orders']}</td>"
        f"<td>+{f['rate_change_percentage_points']:.2f} pp</td>"
        f"<td><a href='#evidence-{i}'>Source examples</a></td></tr>"
        for i, f in enumerate(findings, 1)
    ) or "<tr><td colspan='5'>No sellers met the predeclared worsening rule.</td></tr>"
    evidence = "".join(
        f"<section id='evidence-{i}'><h3>Seller {esc(f['seller_id'])}</h3>"
        + "".join(
            f"<p>Order {esc(e['order_id'])}: {esc(e['source_file'])}, SHA-256 "
            f"{esc(e['source_file_sha256'])}, data-row ordinal {e['order_row_number']}"
            + (f"; review row {e['review_row_number']}, rating {esc(e['rating'])}, "
               f"text: {esc(e['review_text'] or '(no comment)')}" if e['review_row_number'] else "; no review row")
            + "</p>" for e in f["source_examples"]
        ) + "</section>" for i, f in enumerate(findings, 1)
    )
    category_prior = {
        r['entity_id']: r for r in report['category_metrics']
        if r['purchase_month'] == months[0]['purchase_month']
    }
    categories = sorted(
        (r for r in report["category_metrics"] if r["purchase_month"] == months[1]["purchase_month"]),
        key=lambda r: (-r["delivered_orders"], r["entity_id"]),
    )[:10]
    def prior_category_rate(entity: str) -> str:
        previous = category_prior.get(entity)
        return f"{previous['late_orders']} / {previous['dated_orders']}" if previous else "no prior data"

    category_rows = "".join(
        f"<tr><td>{esc(r['entity_id'])}</td><td>{r['delivered_orders']:,}</td>"
        f"<td>{esc(prior_category_rate(r['entity_id']))}</td>"
        f"<td>{r['late_orders']} / {r['dated_orders']}</td><td>{r['orders_with_review']} orders</td></tr>"
        for r in categories
    )
    caveats = "".join(f"<li>{esc(s)}</li>" for s in report["limitations"])
    semantic_html = ""
    if report.get("semantic_review"):
        semantic = report["semantic_review"]
        changes = "".join(
            f"<tr><th>{esc(f['entity_type'])}: {esc(f['entity_key'])}</th>"
            f"<td>{f['previous_review_count']} / {f['current_review_count']}</td>"
            f"<td>{esc(f['mean_model_probability_delta_points'])} points</td></tr>"
            for f in semantic["comparison"]["findings"]
        )
        sources = "".join(
            f"<li>Review {e['review_record_id']}; order {esc(e['order_id'])}; "
            f"{esc(e['source_file'])}, row {e['source_row_number']}, SHA-256 {esc(e['file_sha256'])}; "
            f"model {esc(e['model'])}; request {esc(e['request_id'])}; "
            f"question set {esc(e['question_set_version'])}</li>"
            for e in semantic["source_evidence"]
        )
        semantic_html = (
            "<section id='semantic-review'><h2>What changed in sampled review text?</h2>"
            f"<p>{esc(semantic['interpretation'])}</p>"
            f"<p>Attribution definition: {esc(semantic['signal_version'])}. "
            f"Execution: {esc(semantic['execution_mode'])}.</p>"
            "<div class='table-scroll'><table><thead><tr><th>Scope</th><th>Previous / current reviews</th>"
            f"<th>Change in mean model probability</th></tr></thead><tbody>{changes}</tbody></table></div>"
            "<details><summary>Review source evidence</summary><ul>" + sources + "</ul></details>"
            "<h3>Cost status</h3><p>Measured provider charges and unpriced local work are separate. "
            "Total cost remains blocked until local compute and human review are priced.</p></section>"
        )
    c = report["contract"]
    return ("<!doctype html><html lang='en'><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            "<title>BackIntel | Seller review candidate</title>"
            "<style>body{font:16px/1.5 system-ui;max-width:76rem;margin:auto;padding:2rem;color:#172338}"
            "table{border-collapse:collapse;width:100%;margin:1rem 0 2rem}th,td{padding:.6rem;border:1px solid #aab3c2;text-align:left}"
            "thead{background:#e5ebf4}section{scroll-margin-top:1rem}small{color:#35435e}"
            "main{overflow-wrap:anywhere}.table-scroll{overflow-x:auto}"
            "@media(max-width:600px){body{padding:.75rem}table{display:block;overflow-x:auto}"
            "th,td{padding:.4rem;min-width:6rem}td{white-space:nowrap}}</style>"
            "<main><h1>Monthly seller-performance review — candidate</h1>"
            f"<p><strong>Purchase cohorts:</strong> {esc(c['comparison_purchase_month'])} vs "
            f"{esc(c['report_purchase_month'])}. Retrospective final extract, not a live or month-end snapshot.</p>"
            f"{semantic_html}"
            "<h2>Marketplace overview</h2><table><thead><tr><th>Month</th><th>Delivered orders</th>"
            "<th>Late / dated orders</th><th>Orders with reviews</th><th>Rated reviews</th><th>Nonblank comments</th></tr></thead><tbody>"
            f"{marketplace_rows}</tbody></table><h2>Seller changes for investigation</h2>"
            "<p>Associations, not evidence of seller causation. Only single-seller orders; at least "
            f"{c['minimum_comparable_seller_orders']} dated orders per seller in each month. "
            "Ordered by increase in retrospective late-delivery rate; up to five shown.</p>"
            "<table><thead><tr><th>Seller</th><th>Previous late / dated</th><th>Current late / dated</th>"
            f"<th>Change</th><th>Trace</th></tr></thead><tbody>{findings_rows}</tbody></table>"
            f"<h2>Top categories by current delivered-order count</h2><table><thead><tr>"
            "<th>Category</th><th>Current delivered</th><th>Previous late / dated</th><th>Current late / dated</th><th>Review coverage</th>"
            f"</tr></thead><tbody>{category_rows}</tbody></table><h2>Source examples</h2>{evidence}"
            f"<h2>Limits and handling</h2><ul>{caveats}</ul>"
            "<p>Missing reviews are not negative feedback; order-level reviews are never assigned to "
            "each seller of a multi-seller order. Full seller/category aggregates, definitions, and "
            "batch hashes are in the companion JSON. No predictions or causal conclusions are inferred.</p>"
            f"<small>Non-commercial local Olist v2 demo (CC BY-NC-SA 4.0). "
            f"Candidate commit: {esc(report['candidate']['exact_candidate_sha'] or 'uncommitted')}.</small></main></html>\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Restricted local JSON output; never commit dataset-derived rows")
    args = parser.parse_args()
    dsn = os.getenv("BACKINTEL_DATABASE_URL")
    if not dsn:
        print("BACKINTEL_DATABASE_URL is required", file=sys.stderr)
        return 2
    try:
        contract = read_contract()
        with psycopg.connect(dsn) as conn:
            if not conn.info.dbname.startswith("backintel_"):
                raise ValueError("Refusing to read a database outside the backintel_ namespace")
            report = build_report(conn, contract)
        output = args.output.expanduser().resolve()
        if output.is_relative_to(ROOT):
            raise ValueError("Dataset-derived reports must be written outside the Git checkout")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        html_path = output.with_suffix(".html")
        html_path.write_text(render_html(report), encoding="utf-8")
        print(f"Wrote review candidate: {output}, {html_path}; findings: {len(report['findings'])}")
        return 0
    except (OSError, KeyError, ValueError, psycopg.Error) as error:
        print(f"Report blocked: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
