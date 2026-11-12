# BackIntel v2 agent instructions

Use plain, complete English. Lead with the measured result and what it means for the
analyst's capability. Preserve required behavior and checks.

## What this is

BackIntel v2 is an ambient data-analyst agent: given connected data stores and a few
standing business problems, it answers questions on a schedule and tells a consistent story
over time. This branch (`codex/backintel-v2`) is a fresh build; v1 lives in Git history and on
the older branches, and nothing from it is imported.

The build order is deliberate (owner decision, 2026-11-09): benchmark first, agent second,
infrastructure last. The agent's value is measured, not asserted.

## Architecture

- `src/backintel/agent.py`: one Deep Agents lead (`create_deep_agent`), **no sub-agents**.
  Add a sub-agent only when a LangSmith trace shows a specific failure and a before/after
  experiment improves the score; keep it only if the score stays better. Number checking is
  code, never another model.
- Tools (`tools.py`): `list_tables`, `describe_table`, `run_sql` or `run_query` (read-only, 200-row cap),
  `run_python` (SmolVM sandbox, no network, read-only data mount). Skills in `agent_files/skills`
  are loaded on demand through the Deep Agents skills middleware; `agent_files/lead.md` is the
  system prompt.
- Contract (`contracts.py`): the analyst returns an `AnalystAnswer` with `evidence` (the exact
  SQL or Python that produced the number), `method` and `caveats`. Code re-executes the
  evidence; an answer that cannot be reproduced from its evidence is scored as unsupported.
- Stores (`stores/`): `sqlite`, `postgres`, `ferretdb` (native aggregation JSON),
  `lake-iceberg` (DuckDB over Iceberg metadata and Parquet on Garage S3), `clickhouse`,
  `files` (CSV) and `files-mixed` (CSV/JSON). `lake-parquet` is a separate local Parquet
  baseline; `multi` connects several stores. Docker services use profiles in `compose.yaml`.
  Never load FerretDB during an experiment: loading temporarily thaws its PostgreSQL backend,
  then freezes it before returning. FerretDB 2.7's declared MongoDB read role does not enforce
  read-only access; the frozen backend does. See `docs/benchmark.md`.
- Benchmark (`bench/`): datasets are downloaded by script with pinned checksums and never
  committed; `oracle/` computes reference answers with polars over canonical Parquet,
  independently of any store, into `benchmarks/answers/*.json`; `scoring.py` and `judge.py`
  score; `run.py` runs scenarios locally or as LangSmith experiments; `scorecard.py`
  aggregates into `results/scorecard.md`.
- Models (`models.py`): `openrouter/<vendor>/<model>` (OpenAI, Anthropic, Google only, per the
  technology-selection policy), `chatgpt-plan/<model>` (operator's ChatGPT plan after
  `backintel chatgpt login`), `openai/<model>`. The judge is a different model family from
  the analyst.

## Working rules

- Python with `uv`; configuration from Doppler project `backintel` (`doppler run -p backintel
  -c dev -- uv run backintel ...`). No `.env` files. Never print or commit credentials.
- Lint: `uv run ruff check src tests scripts`; format: `uv run ruff format src tests scripts`; tests:
  `uv run pytest -q`. Tests never call a model provider.
- Datasets, SQLite files, Parquet and raw results stay out of Git (`.gitignore`). Commit
  download scripts, checksums, reference answers and scorecards.
- Scenario references and tolerances are evaluator-owned: existing cases live in
  `benchmarks/answers`, controlled development/reserved cases in `benchmarks/acceptance`,
  and frozen comparison selections in `benchmarks/improvement`. The analyst sees only its
  question and bound store through its tools. Keep dataset-specific hints and reference
  answers out of runtime skills and coding-worker inputs: the benchmark measures discovery.
- Record every experiment's model, source/reference hashes, method version (prompt and skills), sandbox
  backend and git SHA; they are in each record and in the scorecard.
- A low score is a finding. A broken runner, a skipped store, or a fabricated result is
  unfinished work. Mark local verification, measured results and planned behavior
  separately in any summary.
- Linear project BackIntel (team `INT`) owns status and priority; GitHub owns code, PRs and
  CI; this repository's Markdown owns specs and evidence, never status.
- Ask the owner before any commit or push, and before any deployment or cloud resource.

## Levels

1. Single table. 2. Joins and multi-step. 3. Messy data and unanswerable questions.
4. Cross-store: Olist split into `postgres:olist_orders` and `sqlite:olist_catalog`
   (`backintel split build`), run with `--store multi:postgres:olist_orders+sqlite:olist_catalog`.
5. Standing problems: `report` answers with one metric per row; facts are scored by metric and value, the
   story by the judge.
6. Ambient replay: `backintel replay build` writes Olist snapshots for monthly delivery, quarterly
   repeat-purchasing and weekly category/seller reviews. Future observations are hidden; planting
   is declared in `bench/replay.py`. Each scenario binds its immutable snapshot store.
7. Scale: TPC-H generated with DuckDB (`backintel tpch generate --sf 1`) and queried as a lake.
   Scale factors above 1 belong on the Windows desktop.

## Deferrals

Production hosting, web UI, live scheduling, customer integrations, Infrastructure Engine
enrollment and scale factors above 1. The public-benchmark comparison in INT-399 is separate
from this execution goal; these results do not establish external leaderboard performance.
