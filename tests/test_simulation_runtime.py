"""Use the real existing graph and PostgreSQL ledger in an explicitly isolated test database."""
import asyncio
import os
import tempfile
import unittest
import uuid
from unittest.mock import patch

import psycopg

from runtime.ledger import dsn
from runtime.simulation_graph import graph


class SimulationRuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def test_concurrent_replay_and_conflicting_scenario(self):
        key = f"simulation-{uuid.uuid4()}"
        state = {"scenario": "support", "partition_id": key}
        with tempfile.TemporaryDirectory() as output, patch.dict(os.environ, {"BACKINTEL_REPORT_DIR": output}):
            first, replay = await asyncio.gather(graph.ainvoke(state), graph.ainvoke(state))
            self.assertEqual(first["result"], replay["result"])
            self.assertEqual(first["report"], replay["report"])
            with psycopg.connect(dsn()) as conn:
                rows = conn.execute("SELECT disposition, record_count FROM backintel.partition_results WHERE partition_id=%s", (key,)).fetchall()
            self.assertEqual(rows, [("accepted", 10)])
            with self.assertRaises(ValueError):
                await graph.ainvoke({"scenario": "equipment", "partition_id": key})
            equipment = await graph.ainvoke({"scenario": "equipment", "partition_id": f"simulation-{uuid.uuid4()}"})
            self.assertEqual(equipment["result"]["batches"][1]["summary"]["flagged"], 2)
