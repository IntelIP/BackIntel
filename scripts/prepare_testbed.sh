#!/bin/sh
# Prepare the immutable local testbed. Run under Doppler. Never run during an experiment:
# the FerretDB loader briefly thaws its database, then freezes it before returning.
set -eu
cd "$(dirname "$0")/.."
uv sync --frozen
uv run backintel data build all
uv run backintel oracle build all
uv run python - <<'PY'
from backintel.settings import Settings
from backintel.bench.build_stores import build_files, build_postgres, build_parquet
from backintel.stores.files import export_csv_files
s=Settings.from_env()
for name in ('olist', 'online_retail_ii'):
    build_postgres(name,s)
    build_files(name,s)
    build_parquet(name,s)
    export_csv_files(name,s.canonical_dir/name,s.stores_dir/'files-mixed'/name,mixed=True)
PY
uv run backintel split build
uv run backintel replay build
for kind in clickhouse ferretdb lake-iceberg; do
  uv run backintel stores build "$kind"
  uv run backintel stores stop "$kind"
done
uv run backintel tpch generate --sf 1
uv run backintel oracle build tpch_sf1
docker build -f Dockerfile.sandbox -t backintel-sandbox:py312 .
uv run backintel sandbox check
