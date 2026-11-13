"""PostgreSQL store: a local container on an internal Docker network, read through a read-only role.

The runner connects over localhost; the SmolVM sandbox receives only a socket bridge to
the assigned service, using the same container hostname inside its offline guest.
The `analyst` role has SELECT only and read-only transactions.
"""

from __future__ import annotations

import re
import subprocess
import threading
import time
from pathlib import Path

import polars as pl
import psycopg

from backintel.stores.base import MAX_ROWS, ColumnInfo, QueryRefused, QueryResult, TableInfo, clip_cell

CONTAINER = "backintel-postgres"
NETWORK = "backintel-net"
IMAGE = "postgres:17"
HOST_PORT = 55432
ADMIN_PASSWORD = "backintel-local-admin"  # local container bound to 127.0.0.1 only
ANALYST_PASSWORD = "backintel-local-analyst"
READ_ONLY_PREFIXES = ("select", "with", "explain", "table", "values")
FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|truncate|grant|revoke|copy|set|reset|vacuum|analyze|"
    r"listen|notify|lock|do|call|refresh|cluster|reindex|begin|commit|rollback|pg_sleep|dblink|"
    r"pg_read_file|pg_ls_dir|lo_import|lo_export)\b",
    re.I,
)


def screen_sql(text: str) -> str:
    cleaned = re.sub(r"--[^\n]*", "", text)
    cleaned = re.sub(r"/\*.*?\*/", "", cleaned, flags=re.S).strip().rstrip(";").strip()
    if not cleaned:
        raise QueryRefused("Empty query.")
    if ";" in cleaned:
        raise QueryRefused("Send one statement at a time.")
    if not cleaned.lower().startswith(READ_ONLY_PREFIXES):
        raise QueryRefused("Only SELECT / WITH / EXPLAIN statements are allowed; the database is read-only.")
    if FORBIDDEN.search(cleaned):
        raise QueryRefused(
            "The statement contains a write, DDL or session keyword; the database is read-only."
        )
    return cleaned


def admin_dsn(dataset: str) -> str:
    return f"postgresql://postgres:{ADMIN_PASSWORD}@127.0.0.1:{HOST_PORT}/{dataset}"


def analyst_dsn(dataset: str, *, host: str = "127.0.0.1", port: int = HOST_PORT) -> str:
    return f"postgresql://analyst:{ANALYST_PASSWORD}@{host}:{port}/{dataset}"


# ---------------------------------------------------------------------- container lifecycle
def ensure_network() -> None:
    if subprocess.run(["docker", "network", "inspect", NETWORK], capture_output=True).returncode != 0:
        subprocess.run(
            ["docker", "network", "create", "--internal", NETWORK], check=True, capture_output=True
        )


def container_up() -> None:
    ensure_network()
    state = subprocess.run(
        ["docker", "inspect", "-f", "{{.State.Running}}", CONTAINER], capture_output=True, text=True
    )
    if state.returncode == 0 and state.stdout.strip() == "true":
        return
    if state.returncode == 0:
        subprocess.run(["docker", "start", CONTAINER], check=True, capture_output=True)
    else:
        # The container sits on the default bridge for the host's published port and joins the
        # internal network so sandboxes (which have no other network) can reach it by name.
        subprocess.run(
            [
                "docker",
                "run",
                "-d",
                "--name",
                CONTAINER,
                "--memory",
                "1g",
                "-p",
                f"127.0.0.1:{HOST_PORT}:5432",
                "-e",
                f"POSTGRES_PASSWORD={ADMIN_PASSWORD}",
                "-v",
                "backintel-postgres-data:/var/lib/postgresql/data",
                IMAGE,
            ],
            check=True,
            capture_output=True,
        )
        subprocess.run(["docker", "network", "connect", NETWORK, CONTAINER], check=True, capture_output=True)
    for _ in range(60):
        try:
            with psycopg.connect(
                f"postgresql://postgres:{ADMIN_PASSWORD}@127.0.0.1:{HOST_PORT}/postgres", connect_timeout=2
            ):
                return
        except psycopg.OperationalError:
            time.sleep(1)
    raise RuntimeError("PostgreSQL container did not become ready.")


def container_down() -> None:
    subprocess.run(["docker", "stop", CONTAINER], capture_output=True)


PG_TYPES = {
    pl.Int64: "BIGINT",
    pl.Int32: "INTEGER",
    pl.Float64: "DOUBLE PRECISION",
    pl.Utf8: "TEXT",
    pl.String: "TEXT",
    pl.Boolean: "BOOLEAN",
    pl.Datetime("us"): "TIMESTAMP",
    pl.Date: "DATE",
}


def load_dataset(
    dataset: str, canonical_dir: Path, *, force: bool = False, tables: tuple[str, ...] | None = None
) -> None:
    """Create the database and the analyst role, then COPY the canonical tables in."""
    container_up()
    with psycopg.connect(
        f"postgresql://postgres:{ADMIN_PASSWORD}@127.0.0.1:{HOST_PORT}/postgres", autocommit=True
    ) as conn:
        exists = conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", (dataset,)).fetchone()
        if exists and not force:
            return
        if exists:
            conn.execute(f'DROP DATABASE "{dataset}" WITH (FORCE)')
        conn.execute(f'CREATE DATABASE "{dataset}"')
        if not conn.execute("SELECT 1 FROM pg_roles WHERE rolname = 'analyst'").fetchone():
            conn.execute(f"CREATE ROLE analyst LOGIN PASSWORD '{ANALYST_PASSWORD}'")
        conn.execute("ALTER ROLE analyst SET default_transaction_read_only = on")
        conn.execute("ALTER ROLE analyst SET statement_timeout = '60s'")
    with psycopg.connect(admin_dsn(dataset), autocommit=True) as conn:
        for path in sorted(canonical_dir.glob("*.parquet")):
            if path.stem == "geolocation" or (tables is not None and path.stem not in tables):
                continue
            frame = pl.read_parquet(path)
            if "source_sheet" in frame.columns:
                frame = frame.drop("source_sheet")
            columns = ", ".join(f'"{c}" {PG_TYPES.get(t, "TEXT")}' for c, t in frame.schema.items())
            conn.execute(f'CREATE TABLE "{path.stem}" ({columns})')
            with (
                conn.cursor() as cur,
                cur.copy(f"COPY \"{path.stem}\" FROM STDIN WITH (FORMAT csv, NULL '')") as copy,
            ):
                copy.write(frame.write_csv(include_header=False, datetime_format="%Y-%m-%d %H:%M:%S"))
        conn.execute("GRANT USAGE ON SCHEMA public TO analyst")
        conn.execute("GRANT SELECT ON ALL TABLES IN SCHEMA public TO analyst")
        conn.execute("ANALYZE")


class PostgresStore:
    kind = "postgres"
    query_language = "SQL (PostgreSQL 17 dialect)"

    def __init__(self, dataset: str, *, timeout_s: float = 60.0):
        self.dataset = dataset
        self.id = f"postgres:{dataset}"
        self.timeout_s = timeout_s
        self._lock = threading.Lock()
        container_up()
        self.conn = psycopg.connect(
            analyst_dsn(dataset),
            autocommit=True,
            options=f"-c statement_timeout={int(timeout_s * 1000)} -c default_transaction_read_only=on",
        )

    def close(self) -> None:
        self.conn.close()

    def _tables(self) -> list[str]:
        rows = self.conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY 1"
        ).fetchall()
        return [r[0] for r in rows]

    def _columns(self, name: str) -> list[tuple[str, str]]:
        rows = self.conn.execute(
            "SELECT column_name, data_type FROM information_schema.columns WHERE table_schema='public' "
            "AND table_name=%s ORDER BY ordinal_position",
            (name,),
        ).fetchall()
        return [(r[0], r[1]) for r in rows]

    def list_tables(self) -> list[TableInfo]:
        with self._lock:
            out = []
            for name in self._tables():
                count = self.conn.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
                out.append(
                    TableInfo(
                        name=name,
                        row_count=count,
                        columns=[ColumnInfo(name=c, type=t) for c, t in self._columns(name)],
                    )
                )
            return out

    def describe_table(self, name: str) -> TableInfo:
        with self._lock:
            if name not in self._tables():
                raise QueryRefused(f"No table named {name!r}. Tables: {', '.join(self._tables())}")
            count = self.conn.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
            cols = self._columns(name)
            null_expr = ", ".join(f'COUNT(*) - COUNT("{c}")' for c, _ in cols)
            nulls = self.conn.execute(f'SELECT {null_expr} FROM "{name}"').fetchone()
            columns = [
                ColumnInfo(name=c, type=t, nulls=int(n)) for (c, t), n in zip(cols, nulls, strict=True)
            ]
            cur = self.conn.execute(f'SELECT * FROM "{name}" LIMIT 3')
            names = [d.name for d in cur.description]
            sample = [dict(zip(names, (clip_cell(v) for v in row), strict=True)) for row in cur.fetchall()]
        return TableInfo(name=name, row_count=count, columns=columns, sample=sample)

    def query(self, text: str, *, max_rows: int = MAX_ROWS) -> QueryResult:
        sql = screen_sql(text)
        started = time.monotonic()
        with self._lock:
            try:
                cur = self.conn.execute(sql)
                rows = cur.fetchmany(max_rows + 1)
                columns = [d.name for d in cur.description] if cur.description else []
            except psycopg.errors.QueryCanceled as error:
                raise QueryRefused(f"Query exceeded {self.timeout_s:.0f}s and was cancelled.") from error
            except psycopg.Error as error:
                raise QueryRefused(f"PostgreSQL error: {str(error).splitlines()[0][:400]}") from error
        truncated = len(rows) > max_rows
        rows = rows[:max_rows]
        return QueryResult(
            columns=columns,
            rows=[[clip_cell(v) for v in row] for row in rows],
            row_count=len(rows),
            truncated=truncated,
            elapsed_ms=int((time.monotonic() - started) * 1000),
            note=f"Only the first {max_rows} rows are shown; aggregate or add LIMIT/OFFSET."
            if truncated
            else None,
        )

    def python_mounts(self) -> dict[str, str]:
        return {}

    def sandbox_network(self) -> str | None:
        return NETWORK

    def python_environment(self) -> dict[str, str]:
        dsn = analyst_dsn(self.dataset, host=CONTAINER, port=5432)
        return {
            "BACKINTEL_POSTGRES_DSN": dsn,
            "BACKINTEL_STORE_NOTE": (
                "A read-only PostgreSQL database is reachable at the DSN in BACKINTEL_POSTGRES_DSN. Use "
                "psycopg.connect(dsn) and cursor.execute(sql), or polars.read_database_uri(sql, dsn)."
            ),
        }
