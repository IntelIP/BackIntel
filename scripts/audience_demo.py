"""Serve scoped local reports; private tokens never appear in URLs or logs."""

import argparse
import os
from pathlib import Path

import psycopg

from runtime.audience_server import AudienceServer, issue_grants
from runtime.ledger import dsn
from runtime.simulation import encoded


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", action="append", required=True)
    parser.add_argument("--port", type=int, default=2028)
    parser.add_argument("--access-file", type=Path, required=True, help="New private file for one-hour local audience tokens")
    args = parser.parse_args()
    with psycopg.connect(dsn(), autocommit=True) as connection:
        grants = issue_grants(connection, args.task)
    server = AudienceServer(dsn(), grants, args.port)
    args.access_file.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(args.access_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as output:
        output.write(encoded({"login": server.origin + "/login", "grants": grants}))
    print(f"Local reports: {server.origin}/login\nPrivate access file: {args.access_file.resolve()}", flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
