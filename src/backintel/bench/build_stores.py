"""Load canonical tables into each store. The same logical data, each store's native path."""

from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path

import polars as pl

from backintel.bench.datasets import SPLITS, base_dataset, load_canonical
from backintel.settings import Settings

SQLITE_TYPES = {
    pl.Int64: "INTEGER",
    pl.Int32: "INTEGER",
    pl.Float64: "REAL",
    pl.Utf8: "TEXT",
    pl.String: "TEXT",
    pl.Boolean: "INTEGER",
    pl.Datetime("us"): "TEXT",
    pl.Date: "TEXT",
}


def build_sqlite(
    dataset: str, settings: Settings, *, force: bool = False, tables: dict[str, pl.DataFrame] | None = None
) -> Path:
    tables = tables if tables is not None else load_canonical(dataset, settings)
    path = settings.stores_dir / "sqlite" / f"{dataset}.sqlite"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if not force:
            return path
        path.unlink()
    conn = sqlite3.connect(path)
    try:
        for name, frame in tables.items():
            if name == "geolocation":
                continue  # 1M rows of coordinates; not needed by levels 1-3 and slows the build
            if "source_sheet" in frame.columns:
                # The two yearly sheets overlap for 1-9 Dec 2010. A real export would not label
                # the sheet, so the store does not either; the oracle keeps the column.
                frame = frame.drop("source_sheet")
            columns = []
            for column, dtype in frame.schema.items():
                sql_type = SQLITE_TYPES.get(dtype, "TEXT")
                columns.append(f'"{column}" {sql_type}')
                if sql_type == "TEXT" and dtype in (pl.Datetime("us"), pl.Date):
                    frame = frame.with_columns(pl.col(column).dt.strftime("%Y-%m-%d %H:%M:%S"))
            conn.execute(f'CREATE TABLE "{name}" ({", ".join(columns)})')
            placeholders = ", ".join("?" for _ in frame.columns)
            conn.executemany(f'INSERT INTO "{name}" VALUES ({placeholders})', frame.iter_rows())
            # Any real store indexes its keys; without them SQLite joins on text ids take minutes.
            for column in frame.columns:
                if column.endswith("_id") or column in ("invoice", "stock_code", "customer_id"):
                    conn.execute(f'CREATE INDEX IF NOT EXISTS "ix_{name}_{column}" ON "{name}" ("{column}")')
        conn.commit()
        conn.execute("VACUUM")
    finally:
        conn.close()
    return path


def build_files(dataset: str, settings: Settings, *, force: bool = False) -> Path:
    from backintel.stores.files import export_csv_files

    return export_csv_files(
        dataset, settings.canonical_dir / dataset, settings.stores_dir / "files" / dataset, force=force
    )


def build_parquet(dataset: str, settings: Settings) -> Path:
    """A visible Parquet copy without oracle-only provenance, for SQL and Python alike."""
    source = settings.canonical_dir / base_dataset(dataset)
    visible = settings.stores_dir / "lake-parquet" / dataset
    visible.mkdir(parents=True, exist_ok=True)
    only = SPLITS[dataset][1] if dataset in SPLITS else None
    for path in source.glob("*.parquet"):
        if path.stem == "geolocation" or (only is not None and path.stem not in only):
            continue
        target = visible / path.name
        if target.exists() and target.stat().st_mtime_ns >= path.stat().st_mtime_ns:
            continue
        if "source_sheet" in pl.scan_parquet(path).collect_schema():
            frame = pl.read_parquet(path)
            frame = frame.drop("source_sheet")
            frame.write_parquet(target)
        else:
            shutil.copy2(path, target)
    return visible


def build_postgres(dataset: str, settings: Settings, *, force: bool = False) -> str:
    from backintel.stores.postgres import load_dataset

    tables = SPLITS[dataset][1] if dataset in SPLITS else None
    load_dataset(dataset, settings.canonical_dir / base_dataset(dataset), force=force, tables=tables)
    return f"postgres:{dataset}"


def build_replay_snapshots(settings: Settings, *, force: bool = False) -> list[Path]:
    """One SQLite store per replay period, with the planted changes applied before the as-of cut."""
    from backintel.bench.replay import SNAPSHOT_PERIODS, replay_frames, snapshot_name

    frames = load_canonical("olist", settings)
    frames.pop("geolocation", None)
    return [
        build_sqlite(snapshot_name(p), settings, force=force, tables=replay_frames(frames, p))
        for p in SNAPSHOT_PERIODS
    ]
