# BackIntel v2

An ambient data-analyst agent built on the Deep Agents SDK, benchmarked before it is
productised. One lead agent, no sub-agents, native read-only queries, schema discovery, sandboxed
Python and storage skills, and an answer contract whose numbers are re-checked by code.

## Quick start

```bash
uv sync
doppler run -p backintel -c dev -- uv run backintel data build all      # download + canonical + SQLite
doppler run -p backintel -c dev -- uv run backintel oracle build all    # reference answers
docker build -f Dockerfile.sandbox -t backintel-sandbox:py312 .         # the Python sandbox
doppler run -p backintel -c dev -- uv run backintel sandbox check
doppler run -p backintel -c dev -- uv run backintel ask --store sqlite:olist "How many orders were delivered?"
doppler run -p backintel -c dev -- uv run backintel bench run --dataset olist --levels 1,2,3
doppler run -p backintel -c dev -- uv run backintel bench scorecard
```

Environment (from Doppler): `OPENROUTER_API_KEY`, `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT`,
`LANGSMITH_TRACING`, optional `BACKINTEL_MODEL`, `BACKINTEL_JUDGE_MODEL`,
`BACKINTEL_SANDBOX` (`docker` or `subprocess`), `BACKINTEL_DATA_DIR`. Kaggle downloads read
`~/.kaggle/access_token` or `KAGGLE_API_TOKEN`.

## Datasets

| Dataset | Source | Licence | Used for |
|---|---|---|---|
| Online Retail II | UCI Machine Learning Repository (id 502) | CC BY 4.0 | single-table and messy-data levels |
| Brazilian E-Commerce (Olist) | Kaggle `olistbr/brazilian-ecommerce` | CC BY-NC-SA 4.0 | joins and messy-data levels |

Raw files never enter Git. `backintel data build` downloads them, verifies the pinned SHA-256,
writes typed Parquet copies under `data/canonical/` and loads SQLite stores under `data/stores/`.

## Benchmark

Seven levels; all have scenarios, stores and scoring:

1. **Single table**: filters, aggregates, rankings with stated conventions.
2. **Joins / multi-step**: three-table joins, ratios, identity resolution.
3. **Messy data**: duplicated exports, cancellations as negative quantities, null ids,
   non-product codes, untranslated categories, grain mismatches, and questions the data
   cannot answer (the right answer is to decline).
4. **Cross-store**: the same dataset split across PostgreSQL and SQLite; answers need both.
5. **Standing problems**: one problem, several facets, answered as a report that tells a story.
6. **Ambient replay**: monthly delivery, quarterly repeat-purchasing, and weekly category/seller questions against
   snapshots that hide future observations, with a
   planted step change (declared in `bench/replay.py`) among the data's natural variation.
7. **Scale**: TPC-H generated at a chosen scale factor and queried as a Parquet lake.

Stores: `sqlite`, `postgres`, `ferretdb`, `lake-iceberg` (Iceberg on Garage S3 through DuckDB),
`clickhouse`, `files` (CSV), `files-mixed` (CSV/JSON), `lake-parquet` (local-file baseline), and
`multi` (several at once). Build them with `backintel data build all`,
`backintel split build`, `backintel replay build`, `backintel tpch generate --sf 1`.

Scores, all recorded as LangSmith feedback and in `results/`:

- `correct`: answer matches the polars-computed reference within the scenario's tolerance.
- `evidence_reproduces`: the cited SQL/Python is re-executed read-only and yields the answer.
- `abstention_correct`: answered when answerable, declined when not.
- `judge_method`: a cross-family LLM rubric on conventions, method fit, overreach, caveats.
- `fully_supported`: correct + evidence + abstention, the headline number.

See [the capability report](docs/results.md) for the measured outcome and limitations,
[the scorecard](results/scorecard.md) for all experiments, and [the benchmark specification](docs/benchmark.md)
for exact scoring and reproduction commands. `doppler run -p backintel -c dev --
scripts/prepare_testbed.sh` prepares every local store; `uv run python scripts/verify_testbed.py`
checks both datasets through each native path without model calls. `scripts/run_matrix.sh`
runs the full matrix with the configured paid analyst and judge. The measured matrix is
listed in the report; the three-question mixed-file probe is explicitly a probe.

Python-only checks run in GitHub Actions. Publication waits for owner approval under
AGENTS.md; no production service is deployed by this build.
