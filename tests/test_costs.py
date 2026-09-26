"""Cost accounting contracts; only synthetic IDs and provider usage here."""
import asyncio
import uuid
import unittest
from decimal import Decimal

import psycopg

from runtime.costs import record_usage, summary
from runtime.ledger import admit, accept, dsn


class CostTests(unittest.IsolatedAsyncioTestCase):
    async def test_known_and_unknown_costs_and_retry_are_not_conflated(self):
        key = f"usage-test-{uuid.uuid4()}"
        await admit(key, 5, "fixture-digest")
        await accept(key, 5, "fixture-digest")
        await record_usage(partition_id=key, stage="runtime", provider="local",
                           outcome="success", record_count=5, wall_ms=400,
                           charge_status="not_applicable")
        event = uuid.uuid4()
        fields = dict(partition_id=key, stage="jev", provider="typesafe",
                      model="jev-latest", request_id="fixture-request", outcome="success",
                      record_count=5, wall_ms=120, input_tokens=500, output_tokens=100,
                      charge_status="estimated", charge_usd=Decimal("0.001500000"),
                      price_ref="fixture-pricing-only", event_id=event)
        await record_usage(**fields)
        await record_usage(**fields)  # Retransmission, not an additional charge.
        with self.assertRaises(ValueError):
            await record_usage(**(fields | {"charge_usd": Decimal("0.002000000")}))
        await record_usage(partition_id=key, stage="jev", provider="typesafe",
                           outcome="error", record_count=0, wall_ms=40,
                           charge_status="unknown")
        result = summary(key)
        self.assertEqual(result["domain_status"], "accepted")
        self.assertEqual(result["attempts"], 3)
        self.assertEqual(result["accepted_records"], 5)
        self.assertEqual(result["priced_provider_charges_usd"], "0.001500000")
        self.assertEqual(result["estimated_provider_charges_usd"], "0.001500000")
        self.assertEqual(result["measured_provider_charges_usd"], "0")
        self.assertEqual(result["priced_provider_charges_per_accepted_record_usd"], "0.000300000")
        self.assertEqual(result["wall_ms_sum_not_elapsed_time"], 560)
        self.assertEqual(result["unpriced_events"], 1)
        self.assertEqual(result["missing_token_usage_events"], 1)
        self.assertEqual(result["by_stage"]["jev"]["attempts"], 2)
        self.assertEqual(result["by_stage"]["jev"]["priced_charges_usd"], "0.001500000")
        self.assertEqual(result["input_tokens_reported"], 500)
        self.assertIsNone(result["total_cost_usd"])
        self.assertEqual(result["total_cost_status"], "unknown")

    async def test_unpriced_local_compute_is_not_reported_as_free(self):
        key = f"usage-test-{uuid.uuid4()}"
        await record_usage(partition_id=key, stage="runtime", provider="local",
                           outcome="cancelled", record_count=3, wall_ms=17,
                           charge_status="not_applicable")
        result = summary(key)
        self.assertIsNone(result["accepted_records"])
        self.assertEqual(result["priced_provider_charges_usd"], "0")
        self.assertIsNone(result["total_cost_usd"])
        self.assertEqual(result["total_cost_status"], "partial_local_compute_unpriced")
        self.assertIsNone(result["priced_provider_charges_per_accepted_record_usd"])

    async def test_invalid_price_without_provenance_fails(self):
        with self.assertRaises(psycopg.errors.CheckViolation):
            await record_usage(partition_id=f"usage-test-{uuid.uuid4()}",
                               stage="jev", provider="typesafe", outcome="success",
                               record_count=1, wall_ms=2, charge_status="estimated",
                               charge_usd=Decimal("0.01"))
