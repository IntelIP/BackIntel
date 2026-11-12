#!/bin/sh
# Run the complete store matrix after prepare_testbed.sh. One experiment at a time.
# Run under Doppler; this intentionally calls the configured analyst and judge APIs.
set -eu
cd "$(dirname "$0")/.."
for kind in sqlite postgres lake-parquet files files-mixed clickhouse ferretdb lake-iceberg; do
  case "$kind" in
    clickhouse|ferretdb|lake-iceberg) uv run backintel stores up "$kind" ;;
  esac
  for dataset in olist online_retail_ii; do
    uv run backintel bench run --dataset "$dataset" --store "$kind:$dataset" --levels 1,2,3 --concurrency 1
  done
  case "$kind" in
    clickhouse|ferretdb|lake-iceberg) uv run backintel stores stop "$kind" ;;
  esac
done
uv run backintel bench run --dataset olist --store 'multi:postgres:olist_orders+sqlite:olist_catalog' --levels 4 --concurrency 1
uv run backintel bench run --dataset olist --store sqlite:olist --levels 5,6 --concurrency 1
uv run backintel bench run --dataset tpch_sf1 --store lake-parquet:tpch_sf1 --levels 7 --concurrency 1
uv run backintel bench scorecard
