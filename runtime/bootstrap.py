"""Initialize the isolated local application database after provisioning it."""
from pathlib import Path

import psycopg

from runtime.ledger import dsn


if __name__ == "__main__":
    migration = Path(__file__).resolve().parents[1] / "migrations" / "0002_partition_results.sql"
    with psycopg.connect(dsn()) as conn:
        conn.execute(migration.read_text(), prepare=False)
    print("Application result ledger ready")
