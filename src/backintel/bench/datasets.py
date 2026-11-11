"""Dataset acquisition and canonical typed copies. Raw data never enters Git.

Each dataset has a manifest: where it comes from, its licence, the checksum of the archive
we downloaded, and the canonical tables we derive from it (typed Parquet, rows untouched).
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import zipfile
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import httpx
import polars as pl

from backintel.settings import Settings

KAGGLE_API = "https://www.kaggle.com/api/v1/datasets/download"


@dataclass(frozen=True)
class DatasetSpec:
    name: str
    title: str
    source_url: str
    licence: str
    licence_note: str
    archive_name: str
    expected_sha256: str | None  # pinned after the first verified download
    kaggle_ref: str | None = None
    direct_url: str | None = None


DATASETS: dict[str, DatasetSpec] = {
    "online_retail_ii": DatasetSpec(
        name="online_retail_ii",
        title="Online Retail II (UCI Machine Learning Repository, id 502)",
        source_url="https://archive.ics.uci.edu/dataset/502/online+retail+ii",
        licence="CC BY 4.0",
        licence_note="Chen, D. (2019). Online Retail II. UCI Machine Learning Repository. "
        "Verified on the UCI dataset page, 2026-11-09.",
        archive_name="online_retail_ii.zip",
        expected_sha256="572e36277c2390fbfde10664750731e0a86f55e33470d91919085f0408e67bfb",
        direct_url="https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip",
    ),
    "olist": DatasetSpec(
        name="olist",
        title="Brazilian E-Commerce Public Dataset by Olist (Kaggle)",
        source_url="https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce",
        licence="CC BY-NC-SA 4.0",
        licence_note="Kaggle dataset metadata reports CC-BY-NC-SA-4.0 (read via the Kaggle API, "
        "2026-11-09). Non-commercial: fine for this open benchmark, not for a paid product.",
        archive_name="olist.zip",
        expected_sha256="967e41e04fc306fe604e2a693f488995a8b41e5047418f8a5c8e4abd6deca784",
        kaggle_ref="olistbr/brazilian-ecommerce",
    ),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def kaggle_token() -> str:
    token = os.environ.get("KAGGLE_API_TOKEN")
    path = Path(os.environ.get("KAGGLE_CONFIG_DIR") or Path.home() / ".kaggle") / "access_token"
    if not token and path.exists():
        token = path.read_text().strip()
    if not token:
        raise RuntimeError("No Kaggle token: set KAGGLE_API_TOKEN or create ~/.kaggle/access_token.")
    return token


def download(spec: DatasetSpec, settings: Settings, *, force: bool = False) -> Path:
    target_dir = settings.raw_dir / spec.name
    target_dir.mkdir(parents=True, exist_ok=True)
    archive = target_dir / spec.archive_name
    if archive.exists() and not force:
        actual = sha256_file(archive)
        if spec.expected_sha256 and actual != spec.expected_sha256:
            raise RuntimeError(f"{archive} has checksum {actual}, expected {spec.expected_sha256}.")
        return archive
    if spec.direct_url:
        url, headers = spec.direct_url, {}
    else:
        url, headers = (
            f"{KAGGLE_API}/{spec.kaggle_ref}",
            {"Authorization": f"Bearer {kaggle_token()}"},
        )
    with (
        httpx.Client(follow_redirects=True, timeout=600) as client,
        client.stream("GET", url, headers=headers) as response,
    ):
        response.raise_for_status()
        tmp = archive.with_suffix(".part")
        with tmp.open("wb") as handle:
            for chunk in response.iter_bytes(1 << 20):
                handle.write(chunk)
    actual = sha256_file(tmp)
    if spec.expected_sha256 and actual != spec.expected_sha256:
        tmp.unlink()
        raise RuntimeError(f"Downloaded {spec.name} has checksum {actual}, expected {spec.expected_sha256}.")
    tmp.replace(archive)
    return archive


def _canonical_online_retail_ii(archive: Path, out_dir: Path) -> dict[str, int]:
    import openpyxl

    with zipfile.ZipFile(archive) as zf:
        name = next(n for n in zf.namelist() if n.lower().endswith(".xlsx"))
        workbook = openpyxl.load_workbook(io.BytesIO(zf.read(name)), read_only=True)
    frames = []
    for sheet in workbook.worksheets:
        rows = sheet.iter_rows(values_only=True)
        header = next(rows)
        assert list(header) == [
            "Invoice",
            "StockCode",
            "Description",
            "Quantity",
            "InvoiceDate",
            "Price",
            "Customer ID",
            "Country",
        ], header
        data = [(str(r[0]), str(r[1]), r[2], r[3], r[4], r[5], r[6], r[7], sheet.title) for r in rows]
        frames.append(
            pl.DataFrame(
                data,
                orient="row",
                schema={
                    "invoice": pl.Utf8,
                    "stock_code": pl.Utf8,
                    "description": pl.Utf8,
                    "quantity": pl.Int64,
                    "invoice_date": pl.Datetime("us"),
                    "price": pl.Float64,
                    "customer_id": pl.Int64,
                    "country": pl.Utf8,
                    "source_sheet": pl.Utf8,
                },
            )
        )
    frame = pl.concat(frames)
    frame.write_parquet(out_dir / "transactions.parquet")
    return {"transactions": frame.height}


OLIST_TABLES = {
    "olist_customers_dataset.csv": "customers",
    "olist_orders_dataset.csv": "orders",
    "olist_order_items_dataset.csv": "order_items",
    "olist_order_payments_dataset.csv": "order_payments",
    "olist_order_reviews_dataset.csv": "order_reviews",
    "olist_products_dataset.csv": "products",
    "olist_sellers_dataset.csv": "sellers",
    "product_category_name_translation.csv": "product_category_translation",
    "olist_geolocation_dataset.csv": "geolocation",
}
OLIST_DATES = {
    "orders": [
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ],
    "order_items": ["shipping_limit_date"],
    "order_reviews": ["review_creation_date", "review_answer_timestamp"],
}


def _canonical_olist(archive: Path, out_dir: Path) -> dict[str, int]:
    counts = {}
    with zipfile.ZipFile(archive) as zf:
        for member, table in OLIST_TABLES.items():
            frame = pl.read_csv(io.BytesIO(zf.read(member)), infer_schema_length=100_000)
            for column in OLIST_DATES.get(table, []):
                frame = frame.with_columns(
                    pl.col(column).str.strptime(pl.Datetime("us"), "%Y-%m-%d %H:%M:%S", strict=False)
                )
            frame.write_parquet(out_dir / f"{table}.parquet")
            counts[table] = frame.height
    return counts


CANONICAL_BUILDERS = {"online_retail_ii": _canonical_online_retail_ii, "olist": _canonical_olist}


def build_canonical(name: str, settings: Settings, *, force: bool = False) -> dict:
    spec = DATASETS[name]
    archive = download(spec, settings)
    out_dir = settings.canonical_dir / name
    manifest_path = out_dir / "MANIFEST.json"
    if manifest_path.exists() and not force:
        return json.loads(manifest_path.read_text())
    out_dir.mkdir(parents=True, exist_ok=True)
    counts = CANONICAL_BUILDERS[name](archive, out_dir)
    manifest = {
        **asdict(spec),
        "archive_sha256": sha256_file(archive),
        "tables": counts,
        "built_at": datetime.now(UTC).isoformat(),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2))
    return manifest


# Named subsets of a dataset's tables, used to spread one dataset across several stores for the
# cross-store level. A split is loaded into a store under its own name, e.g. `postgres:olist_orders`.
SPLITS: dict[str, tuple[str, tuple[str, ...]]] = {
    "olist_orders": ("olist", ("orders", "customers", "order_payments", "order_reviews")),
    "olist_catalog": ("olist", ("order_items", "products", "sellers", "product_category_translation")),
}


def base_dataset(name: str) -> str:
    return SPLITS[name][0] if name in SPLITS else name


def load_canonical(name: str, settings: Settings) -> dict[str, pl.DataFrame]:
    base, tables = SPLITS.get(name, (name, None))
    out_dir = settings.canonical_dir / base
    if not (out_dir / "MANIFEST.json").exists():
        raise FileNotFoundError(f"Canonical data for {base} is not built; run `backintel data build {base}`.")
    frames = {p.stem: pl.read_parquet(p) for p in sorted(out_dir.glob("*.parquet"))}
    return frames if tables is None else {t: frames[t] for t in tables}
