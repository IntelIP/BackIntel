# BackIntel

Local Olist Seller Performance PoC: reconciled facts, background review enrichment, versioned semantic changes, and a source-linked manager review. This checkout is the integration home. The website remains a separate project.

- [Current repository map](docs/architecture/repository-map.md)
- [Recovery plan and retained worktrees](docs/roadmap/poc-recovery-plan.md)
- [Product contract and later release gates](docs/roadmap/v0.1.0-development-roadmap.md)

## Run the local PoC

Use the existing Python/PostgreSQL/Aegra stack. The demo defaults to replaying recorded observations and makes **no inference calls**. Missing recordings are an error; they are never replaced with fabricated Jev output.

Prerequisites: Docker Compose; approved Olist v2 files outside Git; an isolated local application database; and, for the no-spend demo, its previously recorded accepted observations. The local database snapshot under `~/Library/Application Support/BackIntel/Evidence/PoCRecovery/recorded-demo.pgdump` preserves this machine's existing facts and recordings. Keep that licensed data private and outside Git. A fresh facts-only load does not invent those recordings.

For a new, separately approved local runtime, set the following in your shell or ignored `.env`. Generate your own database password. Set the candidate SHA from a clean checkout before building.

```sh
export BACKINTEL_CANDIDATE_SHA="$(git rev-parse HEAD)"
export BACKINTEL_REPORT_DIR="$HOME/Library/Application Support/BackIntel/Evidence/PoCReports"
mkdir -p "$BACKINTEL_REPORT_DIR"
# Set BACKINTEL_RUNTIME_DB_PASSWORD through your local secret source.
docker compose -f compose.runtime.yml up --build -d
```

Do not run that command over the existing demonstration runtime until its transition is approved. Runtime/API binds only to loopback. Its checkpoint database, application facts database, and Redis broker serve different purposes.

The setup entrypoint creates the application database only when requested, applies every migration in order, verifies source fingerprints, and loads or reconciles the approved files. From a Python environment with `requirements.txt` installed and `BACKINTEL_APP_DATABASE_URL` set:

```sh
python -m scripts.poc setup --create-database \
  --data-dir "$HOME/Library/Application Support/BackIntel/Datasets/OlistV2"
```

Inside a container, provide the dataset through an explicitly approved read-only mount or run setup from a local environment that can reach the database. The database name must be `backintel_app`, or an explicitly configured test database ending in `_test`/starting with `test_`. Never point validation at the demonstration database.

To reproduce the recorded demo in a fresh isolated database, restore the retained snapshot with PostgreSQL's native `pg_restore --no-owner`, then run `python -m runtime.bootstrap` from the current candidate. That preserves original provider request IDs, source hashes, costs, and old snapshots; migration 0006 gives corrected attribution its own version.

Submit and disconnect:

```sh
python -m scripts.poc demo \
  --previous-partition openrouter-olist-2017-02-v1 \
  --partition openrouter-olist-2017-03-v1 \
  --receipt "$HOME/Library/Application Support/BackIntel/Evidence/PoC/demo-run.json"
```

Inspect the **same receipt** later; add `--wait` for a bounded terminal wait. Use a new receipt filename only for a deliberate replay.

```sh
python -m scripts.poc inspect \
  --receipt "$HOME/Library/Application Support/BackIntel/Evidence/PoC/demo-run.json" --wait
```

The result identifies HTML/JSON artifacts, hashes, source examples, candidate identity, and cost disposition. Container `/reports` paths correspond to `BACKINTEL_REPORT_DIR` on the host. `--base-url` selects an isolated validation runtime at submission; the receipt remembers it.

## What the demo proves

An accepted recorded review batch can run in the background, derive corrected versioned signals, compare two batches, and produce a review with source evidence. Replaying identical accepted inputs reuses observations and artifact content. Unknown categories and multi-seller orders do not receive category attribution.

The two five-review samples demonstrate integration. They do not establish population trends, verified complaint rates, model accuracy, seller responsibility, human time savings, or full v0.1.0 readiness. Provider charges, local compute, and human review stay separate; unknown required costs remain blocked.

## Validation

Set `BACKINTEL_TEST_DATABASE_URL` to a disposable, explicitly test-named database. Offline checks use synthetic fixtures and no paid calls:

```sh
python -m unittest discover -s tests -p test_olist_facts.py -v
python -m scripts.validation.check_runtime
node scripts/validation/run.mjs --manifest tabellio.validation.json \
  --expected-commit "$(git rev-parse HEAD)" --output artifacts/validation/local
```

Exact-commit validation requires a clean checkout. Preserve durable evidence outside the checkout. The manifest's offline pass does not substitute for the real recorded-data background run, recovery/cancellation checks, rendered review, or total-cost acceptance.
