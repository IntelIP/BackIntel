"""Local-only benchmark services. Start only the selected profile to limit memory use."""

from __future__ import annotations

import secrets
import subprocess
import time

import httpx

from backintel.settings import Settings, repo_root
from backintel.stores.postgres import ensure_network

PROFILES = {"clickhouse": "clickhouse", "ferretdb": "ferretdb", "lake-iceberg": "lake"}


def compose(kind: str, *args: str) -> None:
    subprocess.run(["docker", "compose", "--profile", PROFILES[kind], *args], cwd=repo_root(), check=True)


def up(kind: str, settings: Settings) -> None:
    ensure_network()
    if kind == "lake-iceberg":
        directory = settings.stores_dir / "garage"
        directory.mkdir(parents=True, exist_ok=True)
        config = directory / "garage.toml"
        if not config.exists():
            config.write_text(
                'metadata_dir = "/var/lib/garage/meta"\ndata_dir = "/var/lib/garage/data"\n'
                'db_engine = "sqlite"\nreplication_factor = 1\n'
                'rpc_bind_addr = "[::]:3901"\nrpc_public_addr = "backintel-garage:3901"\n'
                f'rpc_secret = "{secrets.token_hex(32)}"\n'
                '[s3_api]\ns3_region = "garage"\napi_bind_addr = "[::]:3900"\n'
                'root_domain = ".s3.garage.localhost"\n'
            )
            config.chmod(0o600)
    compose(kind, "up", "-d")
    for _ in range(60):
        try:
            if kind == "ferretdb":
                from backintel.stores.ferretdb import client

                with client(loader=True) as conn:
                    conn.admin.command("ping")
            else:
                port = 18123 if kind == "clickhouse" else 13900
                httpx.get(f"http://127.0.0.1:{port}", timeout=2)
            return
        except Exception:
            time.sleep(1)
    raise RuntimeError(f"{kind} did not become ready in 60 seconds")


def build(kind: str, dataset: str, settings: Settings, *, force: bool = False) -> None:
    up(kind, settings)
    if kind == "lake-iceberg":
        from backintel.stores.iceberg import load_dataset

        load_dataset(dataset, settings, force=force)
    else:
        from importlib import import_module

        import_module(f"backintel.stores.{kind}").load_dataset(
            dataset, settings.canonical_dir / dataset, force=force
        )
