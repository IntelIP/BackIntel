"""Append-only economics observations; unknown costs never become zero."""
from __future__ import annotations

import json
import uuid
from decimal import Decimal

import psycopg

from runtime.ledger import dsn


async def record_usage(*, partition_id: str, stage: str, provider: str, outcome: str,
                       record_count: int, wall_ms: int, model: str | None = None,
                       request_id: str | None = None, input_tokens: int | None = None,
                       output_tokens: int | None = None, charge_status: str = "unknown",
                       charge_usd: Decimal | None = None, price_ref: str | None = None,
                       event_id: uuid.UUID | None = None) -> uuid.UUID:
    """The caller records each real attempt, including retries and failed calls."""
    identifier = event_id or uuid.uuid4()
    async with await psycopg.AsyncConnection.connect(dsn()) as conn:
        inserted = await (await conn.execute("""
            INSERT INTO backintel.usage_events
              (event_id, partition_id, stage, provider, model, request_id, outcome,
               record_count, wall_ms, input_tokens, output_tokens,
               charge_status, charge_usd, price_ref)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (event_id) DO NOTHING RETURNING event_id
        """, (identifier, partition_id, stage, provider, model, request_id, outcome,
              record_count, wall_ms, input_tokens, output_tokens,
              charge_status, charge_usd, price_ref))).fetchone()
        if inserted is None:
            prior = await (await conn.execute("""
                SELECT partition_id, stage, provider, model, request_id, outcome,
                       record_count, wall_ms, input_tokens, output_tokens,
                       charge_status, charge_usd, price_ref
                FROM backintel.usage_events WHERE event_id = %s
            """, (identifier,))).fetchone()
            if prior != (partition_id, stage, provider, model, request_id, outcome,
                         record_count, wall_ms, input_tokens, output_tokens,
                         charge_status, charge_usd, price_ref):
                raise ValueError("Usage event ID reused with different measurements")
    return identifier


def summary(partition_id: str) -> dict:
    """Report measured cost separately from unpriced usage and local resource time."""
    with psycopg.connect(dsn()) as conn:
        events = conn.execute("""
            SELECT stage, provider, outcome, record_count, wall_ms,
                   input_tokens, output_tokens, charge_status, charge_usd
              FROM backintel.usage_events WHERE partition_id = %s
              ORDER BY occurred_at, event_id
        """, (partition_id,)).fetchall()
        result = conn.execute("""
            SELECT disposition, record_count FROM backintel.partition_results
             WHERE partition_id = %s
        """, (partition_id,)).fetchone()
    priced = sum((e[8] or Decimal(0) for e in events), Decimal(0))
    estimated = sum((e[8] or Decimal(0) for e in events if e[7] == "estimated"), Decimal(0))
    measured = sum((e[8] or Decimal(0) for e in events if e[7] == "measured"), Decimal(0))
    unknown = sum(e[7] == "unknown" for e in events)
    accepted = result is not None and result[0] in ("accepted", "published")
    units = result[1] if accepted else None
    return {
        "partition_id": partition_id,
        "domain_status": result[0] if result else None,
        "accepted_records": units,
        "attempts": len(events),
        "priced_provider_charges_usd": str(priced),
        "estimated_provider_charges_usd": str(estimated),
        "measured_provider_charges_usd": str(measured),
        "unpriced_events": unknown,
        "total_cost_status": "unknown" if unknown or not events else "partial_local_compute_unpriced",
        "total_cost_usd": None,
        "priced_provider_charges_per_accepted_record_usd": str(priced / units) if units else None,
        "wall_ms_sum_not_elapsed_time": sum(e[4] for e in events),
        "input_tokens_reported": sum(e[5] or 0 for e in events),
        "output_tokens_reported": sum(e[6] or 0 for e in events),
        "missing_token_usage_events": sum(e[1] != "local" and (e[5] is None or e[6] is None) for e in events),
        "by_stage": {
            stage: {
                "attempts": sum(e[0] == stage for e in events),
                "priced_charges_usd": str(sum((e[8] or Decimal(0) for e in events if e[0] == stage), Decimal(0))),
                "unpriced_events": sum(e[0] == stage and e[7] == "unknown" for e in events),
                "wall_ms_sum": sum(e[4] for e in events if e[0] == stage),
            }
            for stage in sorted({e[0] for e in events})
        },
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python -m runtime.costs PARTITION_ID")
    print(json.dumps(summary(sys.argv[1]), indent=2))
