"""Initialize the isolated local application database after provisioning it."""
from pathlib import Path

import psycopg

from runtime.ledger import dsn


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1] / "migrations"
    with psycopg.connect(dsn()) as conn:
        for name in ("0002_partition_results.sql", "0003_usage_events.sql", "0004_jev_observations.sql", "0005_semantic_signal_snapshots.sql"):
            conn.execute((root / name).read_text(), prepare=False)
    print("Application result and usage ledgers ready")
