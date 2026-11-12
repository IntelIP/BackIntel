"""Direct parity check of both datasets on every native store. No model calls."""

import json
import math
from pathlib import Path

import polars as pl

from backintel.settings import Settings
from backintel.stores import open_store, services

settings = Settings.from_env()
results = []
for kind in (
    "sqlite",
    "postgres",
    "lake-parquet",
    "files",
    "files-mixed",
    "clickhouse",
    "ferretdb",
    "lake-iceberg",
):
    if kind in services.PROFILES:
        services.up(kind, settings)
    for dataset in ("olist", "online_retail_ii"):
        name = "orders" if dataset == "olist" else "transactions"
        money_table = "order_payments" if dataset == "olist" else name
        canonical = settings.canonical_dir / dataset
        expected_rows = pl.scan_parquet(canonical / f"{name}.parquet").select(pl.len()).collect().item()
        expression = pl.col("payment_value") if dataset == "olist" else pl.col("quantity") * pl.col("price")
        expected_total = (
            pl.scan_parquet(canonical / f"{money_table}.parquet").select(expression.sum()).collect().item()
        )
        store = open_store(f"{kind}:{dataset}", settings)
        try:
            if kind.startswith("files"):
                files = [
                    f
                    for f in store.files
                    if (f.startswith("online_retail") if dataset != "olist" else f.startswith(name + "."))
                ]
                rows = sum(store.describe_table(f).row_count for f in files)
                money_files = [
                    f
                    for f in store.files
                    if (f in files if dataset != "olist" else f.startswith(money_table + "."))
                ]
                total = sum(store._frame(f).select(expression.sum()).collect().item() for f in money_files)
            elif kind == "ferretdb":
                rows = store.query(json.dumps({"collection": name, "pipeline": [{"$count": "n"}]})).rows[0][0]
                expr = "$payment_value" if dataset == "olist" else {"$multiply": ["$quantity", "$price"]}
                total = store.query(
                    json.dumps(
                        {
                            "collection": money_table,
                            "pipeline": [
                                {"$group": {"_id": None, "total": {"$sum": expr}}},
                            ],
                        }
                    )
                ).rows[0][1]
            else:
                rows = int(store.query(f'SELECT COUNT(*) FROM "{name}"').rows[0][0])
                expr = "payment_value" if dataset == "olist" else "quantity * price"
                total = float(store.query(f'SELECT SUM({expr}) FROM "{money_table}"').rows[0][0])
            assert rows == expected_rows, (kind, dataset, rows, expected_rows)
            assert math.isclose(float(total), expected_total, rel_tol=1e-8, abs_tol=0.01), (
                kind,
                dataset,
                total,
                expected_total,
            )
            results.append({"store": store.id, "rows": rows, "total": total, "passed": True})
            print(store.id, rows, total, flush=True)
        finally:
            store.close()
    if kind in services.PROFILES:
        services.compose(kind, "stop")
Path("results/store-parity.json").write_text(json.dumps(results, indent=2) + "\n")
