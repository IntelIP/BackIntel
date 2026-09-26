"""Application-owned, replay-safe results. Aegra run status is not a domain transaction."""
from __future__ import annotations

import os
import psycopg
from psycopg.conninfo import conninfo_to_dict


def dsn() -> str:
    value = os.environ.get("BACKINTEL_APP_DATABASE_URL", "")
    database = conninfo_to_dict(value).get("dbname", "")
    if database == "backintel_app":
        return value
    test_value = os.environ.get("BACKINTEL_TEST_DATABASE_URL", "")
    if value == test_value and (database.startswith("test_") or database.endswith("_test")):
        return value
    raise RuntimeError("Database URL must address backintel_app or an explicitly configured test database")


async def admit(partition_id: str, count: int, digest: str) -> None:
    async with await psycopg.AsyncConnection.connect(dsn()) as conn:
        await conn.execute("""
            INSERT INTO backintel.partition_results (partition_id, input_sha256, record_count, disposition)
            VALUES (%s, %s, %s, 'partial')
            ON CONFLICT (partition_id) DO NOTHING
        """, (partition_id, digest, count))
        row = await (await conn.execute("""
            SELECT input_sha256, record_count, disposition FROM backintel.partition_results
            WHERE partition_id = %s
        """, (partition_id,))).fetchone()
        if row[:2] != (digest, count) or row[2] in ("failed", "blocked"):
            raise ValueError("Partition ID was reused for conflicting input or blocked result")


async def accept(partition_id: str, count: int, digest: str, result_digest: str | None = None) -> str:
    result_digest = result_digest or digest
    async with await psycopg.AsyncConnection.connect(dsn()) as conn:
        row = await (await conn.execute("""
            SELECT input_sha256, record_count, disposition, result_sha256
            FROM backintel.partition_results WHERE partition_id = %s FOR UPDATE
        """, (partition_id,))).fetchone()
        if row is None or row[:2] != (digest, count) or row[2] in ("failed", "blocked"):
            raise ValueError("Cannot accept absent, conflicting, or blocked result")
        if row[2] == "partial":
            await conn.execute("""
                UPDATE backintel.partition_results SET disposition = 'accepted', result_sha256 = %s, updated_at = now()
                WHERE partition_id = %s
            """, (result_digest, partition_id))
        elif row[3] != result_digest:
            raise ValueError("An accepted result differs from this run's result")
        return result_digest
