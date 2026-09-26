"""Local-container contract checks for replay-safe domain publication."""
import asyncio
import hashlib
import unittest
import uuid

import psycopg

from runtime.ledger import accept, admit, dsn


class LedgerTests(unittest.IsolatedAsyncioTestCase):
    async def test_concurrent_duplicate_submission_keeps_one_result(self):
        key = f"test-{uuid.uuid4()}"
        digest = hashlib.sha256(f"{key}:7".encode()).hexdigest()
        await asyncio.gather(admit(key, 7, digest), admit(key, 7, digest))
        await asyncio.gather(accept(key, 7, digest), accept(key, 7, digest))
        with psycopg.connect(dsn()) as conn:
            rows = conn.execute("SELECT record_count, disposition, result_sha256 FROM backintel.partition_results WHERE partition_id=%s", (key,)).fetchall()
        self.assertEqual(rows, [(7, "accepted", digest)])

    async def test_conflicting_input_is_refused_without_overwrite(self):
        key = f"test-{uuid.uuid4()}"
        original = hashlib.sha256(f"{key}:7".encode()).hexdigest()
        await admit(key, 7, original)
        await accept(key, 7, original)
        with self.assertRaises(ValueError):
            await admit(key, 8, hashlib.sha256(f"{key}:8".encode()).hexdigest())
        with psycopg.connect(dsn()) as conn:
            row = conn.execute("SELECT record_count, disposition, result_sha256 FROM backintel.partition_results WHERE partition_id=%s", (key,)).fetchone()
        self.assertEqual(row, (7, "accepted", original))

    async def test_partial_blocked_failed_accepted_and_published_are_distinct(self):
        blocked_key = f"test-{uuid.uuid4()}"
        await admit(blocked_key, 7, hashlib.sha256(f"{blocked_key}:7".encode()).hexdigest())
        with psycopg.connect(dsn()) as conn:
            self.assertEqual(conn.execute("SELECT disposition FROM backintel.partition_results WHERE partition_id=%s", (blocked_key,)).fetchone(), ("partial",))
            conn.execute("UPDATE backintel.partition_results SET disposition='blocked' WHERE partition_id=%s", (blocked_key,))
        with psycopg.connect(dsn()) as conn:
            with self.assertRaises(psycopg.errors.CheckViolation):
                conn.execute("UPDATE backintel.partition_results SET disposition='published' WHERE partition_id=%s", (blocked_key,))
        with self.assertRaises(ValueError):
            await accept(blocked_key, 7, hashlib.sha256(f"{blocked_key}:7".encode()).hexdigest())

        failed_key = f"test-{uuid.uuid4()}"
        await admit(failed_key, 7, hashlib.sha256(f"{failed_key}:7".encode()).hexdigest())
        with psycopg.connect(dsn()) as conn:
            conn.execute("UPDATE backintel.partition_results SET disposition='failed' WHERE partition_id=%s", (failed_key,))

        accepted_key = f"test-{uuid.uuid4()}"
        accepted_digest = hashlib.sha256(f"{accepted_key}:7".encode()).hexdigest()
        await admit(accepted_key, 7, accepted_digest)
        await accept(accepted_key, 7, accepted_digest)
        with psycopg.connect(dsn()) as conn:
            conn.execute("UPDATE backintel.partition_results SET disposition='published' WHERE partition_id=%s", (accepted_key,))
            states = dict(conn.execute("SELECT partition_id, disposition FROM backintel.partition_results WHERE partition_id = ANY(%s)", ([blocked_key, failed_key, accepted_key],)).fetchall())
        self.assertEqual(states, {blocked_key: "blocked", failed_key: "failed", accepted_key: "published"})
