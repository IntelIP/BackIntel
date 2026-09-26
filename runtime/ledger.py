"""Application-owned, replay-safe results. Aegra run status is not a domain transaction."""
from __future__ import annotations

import os
from urllib.parse import urlparse

import psycopg


def dsn() -> str:
    value = os.environ.get("BACKINTEL_APP_DATABASE_URL", "")
    if urlparse(value).path != "/backintel_app":
        raise RuntimeError("BACKINTEL_APP_DATABASE_URL must address the local backintel_app database")
    return value


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


async def accept(partition_id: str, count: int, digest: str) -> str:
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
            """, (digest, partition_id))
        elif row[3] != digest:
            raise ValueError("An accepted result differs from this run's result")
        return digest
