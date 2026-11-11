# BackIntel v2 benchmark

Status: Draft, implemented under the owner's autonomous execution request. This is a
capability benchmark, not a production-readiness certification. The analyst is one Deep
Agents lead with schema discovery, bounded read-only queries and isolated Python. Numerical
references are computed separately with polars. The model never receives reference answers,
tolerances, grader code, credentials for loading data, or planted-change declarations.

## What it measures

The same logical data and questions exercise six storage types: SQLite, PostgreSQL,
FerretDB, Apache Iceberg on Garage S3 queried by DuckDB, ClickHouse, and raw CSV and JSON files.
`lake-parquet` is an additional local-file baseline, distinct from Iceberg coverage.
FerretDB results describe FerretDB 2.7 compatibility; they do not establish MongoDB parity.

Levels 1–3 measure aggregation, joins/multi-step reasoning, dirty data and justified refusal.
Level 4 requires PostgreSQL and SQLite together. Level 5 asks the analyst to explain several
related business metrics. Level 6 replays observations on simulated schedules: delivery
monthly, repeat purchasing quarterly, and category/seller performance weekly. No live
scheduler is running. Level 7 uses TPC-H SF1: a generated analytical workload of about
8.7 million rows, not a clickstream dataset or an official TPC-H performance submission.
Larger scale factors remain a separate desktop workload.

Repeat purchasing, delivery/satisfaction and category/seller performance are provisional
business themes. These datasets contain no complete cost ledger; revenue is not profit.
Questions requiring costs, causal identification, or external facts must be declined.

## Data and independence

Acquisition, licenses, archive checksums and canonical row counts are recorded in
`data/canonical/<dataset>/MANIFEST.json`. Downloads and store contents stay outside Git.
Online Retail II is UCI dataset 502 (CC BY 4.0); Olist is Kaggle's Brazilian E-Commerce
Public Dataset (CC BY-NC-SA 4.0), used here for noncommercial research. Dataset licenses
continue to govern the data independently of this code's MIT license.

The oracle reads typed canonical Parquet through polars, independently of each store's
query engine. The analyst sees copies with the same logical rows and no `source_sheet`
provenance field. Reference answers and the planted-change declaration live in
`benchmarks/answers/`, outside every agent filesystem and Python mount. Deep Agents can
read only its prompt/skills directory; filesystem writes and delegation are disabled.

Replay snapshots cut off order arrivals and hide delivery/review observations dated after
the cutoff. Estimated delivery dates remain visible because they are predictions supplied
at purchase. The original purchase-only snapshots are historical results with future
information and must not be presented as a prospective ambient-agent result. Frozen
snapshots simulate arrivals; they cannot reconstruct undocumented source-system status
history. One declared intervention adds seven days to SP deliveries from May 2018 onward.
Natural changes and this planted change are distinct when interpreting results.

## Grading

Every scenario has an explicit expected result, population, conventions and tolerance.
Counts use absolute tolerance; monetary and ratio tolerances are stored per scenario.
Rankings require the correct order. Tables require all expected rows without extra rows.
Reports require the correct value attached to the requested metric identifier, with no
missing, duplicate or invented metrics. Identifiers describe requested metrics, never the
hidden value or which states changed.

LangSmith receives separate feedback fields:

- `correct`: the requested result matches the independent reference.
- `partial_credit`: matching report facts/table rows or ranked-item overlap.
- `evidence_reproduces`: cited SQL, native aggregation JSON or Python re-executes and
  contains the result fields; a failed evidence item fails this check.
- `abstention_correct`: answered when the data can answer and declined otherwise.
- `judge_method`: a different model family grades conventions, method fit, overreach and
  material caveats. The revised judge writes a reason for every criterion and uses
  anchored ratings 0 (fails), 1 (partial/uncertain), 2 (satisfies), normalized to 0–1.
- `fully_supported`: all deterministic correctness, evidence and abstention checks pass.
  This field concerns the requested result fields. It does not certify every sentence
  in the explanation. Read the method judge and examples alongside it.

The old judge returned probabilities without reasons. Its results are versioned historical
baselines, not directly comparable to the revised rubric. A judge score is a heuristic,
not a calibrated probability, human agreement estimate, or proof of correctness. The
judge sees the question, answer and evidence code; it does not execute code or receive the
reference. Numerical correctness never depends on the judge.

Re-execution checks reproducibility, not complete data lineage: a contrived program can
print a constant, values can coincide, and a correct result can accompany an unsound
explanation. Independent references, hidden answers and method review reduce these risks;
the benchmark does not claim adversarial resistance. Grader tests include correct and
wrong values, partial answers, wrong ordering, zero results, extra rows, swapped report
labels, refusal and refused writes. The results report includes real trace inspection.

Infrastructure, verifier and judge errors must be reported separately from capability
failures. Retain original experiments when correcting the harness; reruns and rescoring
must name the change. The categorical replay status may be derived from reproduced per-state changes using the
declared 25% rule; the literal label need not be printed by the evidence program. A low
capability score is a valid finding. A skipped integration or
broken runner is unfinished work.

## Reproduction

Use Python 3.12, Docker and uv. Configuration comes from Doppler `backintel/dev`.

```bash
uv sync --frozen
uv run backintel data build all
uv run backintel oracle build all
uv run backintel split build
uv run backintel replay build
uv run backintel tpch generate --sf 1
uv run backintel oracle build tpch_sf1
docker build -f Dockerfile.sandbox -t backintel-sandbox:py312 .
uv run backintel sandbox check
uv run backintel stores build clickhouse
uv run backintel stores build ferretdb
uv run backintel stores build lake-iceberg
```

`stores build` starts only that local service profile, loads both datasets, creates read-only
analyst credentials, and preserves data in Docker volumes. Stop a profile with
`backintel stores stop <kind>`. The sandbox has no internet access; database clients join
only the internal Docker network. PostgreSQL and ClickHouse enforce read-only roles;
FerretDB freezes its PostgreSQL backend in read-only mode after loading; Garage gives the analyst a read-only bucket key.
Service ports bind only to localhost. Loader credentials are local development credentials,
not production secrets. Garage's generated keys stay in gitignored data files.

```bash
doppler run -p backintel -c dev -- uv run backintel bench run \
  --dataset olist --store clickhouse:olist --levels 1,2,3 --concurrency 1
doppler run -p backintel -c dev -- uv run backintel bench run \
  --dataset olist --store sqlite:olist --levels 5,6 --concurrency 1
uv run backintel bench scorecard
uv run ruff check src tests scripts
uv run ruff format --check src tests scripts
uv run vulture src --min-confidence 100
uv run pytest -q
```

Use `--store ferretdb:olist`, `lake-iceberg:olist`, `postgres:olist`, `files:olist`,
`sqlite:olist`, or `lake-parquet:olist` for the other paths. `backintel data build`
prepares SQLite; the PostgreSQL and raw-file loaders are in `bench/build_stores.py`.
`--store multi:postgres:olist_orders+sqlite:olist_catalog --levels 4` runs the cross-store
suite. `--dataset tpch_sf1 --store lake-parquet:tpch_sf1 --levels 7` runs scale.

LangSmith dataset sync writes examples and reference outputs to the owner's workspace;
only question/input fields reach the target agent. Experiment URLs print on startup and
completion. `results/raw/*.jsonl` saves each completed scenario incrementally with its run
ID, answer, scores, comments, latency and provider-reported model usage. Cost columns cover
reported analyst charges; historical judge charges are not included. Missing costs are not
zero-cost claims. Source and reference hashes identify new working-tree runs; historical
`git_sha` values identify the old base commit, not a committed v2 implementation.

## Sources and selections checked 2026-11-09

This build preserves the approved OpenRouter/OpenAI analyst and Anthropic judge. New
storage selections use the upstream projects and their official images/SDKs:

- [FerretDB company and founders](https://www.ferretdb.com/company) and
  [2.7 Docker/DocumentDB pairing](https://docs.ferretdb.io/installation/ferretdb/docker/).
  The self-hosted server uses FerretDB with Microsoft's DocumentDB PostgreSQL extension. Its 2.7 MongoDB role declarations did
  not prevent writes in the direct check; backend read-only transactions did. Loading
  and evaluation are separate phases, and the loader freezes the backend before use.
- [ClickHouse company history](https://clickhouse.com/company/our-story) identifies its
  Delaware incorporation and Bay Area headquarters; its
  [official image documentation](https://clickhouse.com/docs/install/docker) supplies the
  native server. No hosted ClickHouse service is used.
- [Garage project](https://garagehq.deuxfleurs.fr/) is developed by Deuxfleurs and funded
  by European public programs; its [single-node setup](https://garagehq.deuxfleurs.fr/documentation/quick-start/)
  supplies the local S3 backend. It is a benchmark service, with no redundancy claim.
- [Apache PyIceberg configuration](https://py.iceberg.apache.org/configuration/) documents
  the SQLite catalog and S3 endpoint options. DuckDB's upstream `iceberg`, `avro` and
  `httpfs` extensions are preinstalled in the sandbox; no extension is downloaded by the
  evaluated agent.
- [LangSmith multiple scores](https://docs.langchain.com/langsmith/multiple-scores)
  documents the Python evaluator's list-of-feedback return contract.

The relevant Deep Agents, evaluation, advanced-evaluation, eval-engineering, Ponytail and
product-validation skills inform this design. LangSmith is the chosen evaluation runner;
this task does not add a second Harbor runner. This document is the task specification for
that adaptation. The repository World Knowledge Skill records reusable local facts, with
no scenario truth or scoring answers.

The new API default caps each completion at 8,192 tokens, configurable with
`BACKINTEL_MAX_COMPLETION_TOKENS`, so concurrent reservation of an unbounded completion
cannot consume the remaining development credit. This is not a cap on tool output or
file inspection. A transient provider/credit-reservation failure invalidated the first
mixed-file probe; its sequential retry passed. See the [OpenRouter parameter contract](https://openrouter.ai/docs/api/api-reference/chat/send-chat-completion-request)
for `max_completion_tokens`. No credits were purchased.

Future runs retain partial message usage when execution fails. Failed historical runs'
available usage was recovered from their LangSmith traces; missing costs remain unknown.
Gitleaks 8.30.1 scans the current candidate files locally and in CI. Legacy history cleanup
is outside this fresh-build goal. Hosted CI remains a separate observable check after the
owner approves commit and push.
