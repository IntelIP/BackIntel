"""Append-only, content-addressed evidence on the existing PostgreSQL stack."""
from __future__ import annotations

from psycopg.types.json import Jsonb

from runtime.simulation import digest


def canonical_body(value):
    """PostgreSQL JSONB normalizes negative zero; hash the same representation."""
    if isinstance(value,float) and value == 0:
        return 0.0
    if isinstance(value,list):
        return [canonical_body(item) for item in value]
    if isinstance(value,dict):
        return {key:canonical_body(item) for key,item in value.items()}
    return value


class Evidence:
    def __init__(self, connection, task_id: str):
        self.connection = connection
        self.task_id = task_id

    def put(self, kind: str, identity: str, body: dict, available_at: int, parents=()) -> dict:
        if type(available_at) is not int or available_at < 0:
            raise ValueError("Evidence availability must be a nonnegative integer")
        parents = sorted(set(parents))
        body = canonical_body(body)
        record = {"task_id": self.task_id, "kind": kind, "identity": identity,
                  "body": body, "available_at": available_at, "parents": parents}
        sha = digest(record)
        with self.connection.transaction():
            for parent in parents:
                if self.get(parent)["available_at"] > available_at:
                    raise ValueError("Evidence cannot predate its parents")
            self.connection.execute("""
                INSERT INTO backintel.capability_evidence
                    (sha256, task_id, kind, identity, available_at, body, parents)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (task_id, kind, identity) DO NOTHING
            """, (sha, self.task_id, kind, identity, available_at, Jsonb(body), parents))
            saved = self.find(kind, identity)
            if saved["sha256"] != sha:
                raise ValueError("Evidence identity reused with conflicting content")
        return saved

    @staticmethod
    def _record(row) -> dict:
        if row is None:
            raise ValueError("Evidence does not exist in this task")
        keys = ("sha256", "task_id", "kind", "identity", "available_at", "body", "parents")
        return dict(zip(keys, row))

    def get(self, sha: str) -> dict:
        record = self._record(self.connection.execute("""
            SELECT sha256,task_id,kind,identity,available_at,body,parents
            FROM backintel.capability_evidence WHERE sha256=%s AND task_id=%s
        """, (sha, self.task_id)).fetchone())
        if digest({k: v for k, v in record.items() if k != "sha256"}) != sha:
            raise ValueError("Evidence digest mismatch")
        return record

    def find(self, kind: str, identity: str) -> dict | None:
        row = self.connection.execute("""
            SELECT sha256,task_id,kind,identity,available_at,body,parents
            FROM backintel.capability_evidence WHERE task_id=%s AND kind=%s AND identity=%s
        """, (self.task_id, kind, identity)).fetchone()
        return self.get(row[0]) if row else None

    def list(self, kind: str, cutoff: int | None = None) -> list[dict]:
        rows = self.connection.execute("""
            SELECT sha256 FROM backintel.capability_evidence
            WHERE task_id=%s AND kind=%s AND (%s::bigint IS NULL OR available_at<=%s)
            ORDER BY available_at,identity
        """, (self.task_id, kind, cutoff, cutoff)).fetchall()
        return [self.get(row[0]) for row in rows]

    def lock(self) -> None:
        """Serialize task admission/transitions until the surrounding transaction ends."""
        self.connection.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", (self.task_id,))

    def lineage(self, sha: str) -> list[dict]:
        pending, records = [sha], {}
        while pending:
            current = pending.pop()
            if current not in records:
                records[current] = self.get(current)
                pending.extend(records[current]["parents"])
        return list(records.values())
