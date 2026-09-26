"""Initialize the isolated local application database after provisioning it."""
from pathlib import Path

import psycopg

from runtime.ledger import dsn


def initialize() -> None:
    root = Path(__file__).resolve().parents[1] / "migrations"
    with psycopg.connect(dsn()) as conn:
        for migration in sorted(root.glob("*.sql")):
            conn.execute(migration.read_text(), prepare=False)


if __name__ == "__main__":
    initialize()
    print("Application facts, result, usage, and semantic schemas ready")
