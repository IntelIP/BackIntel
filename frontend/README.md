# Decision workspace demo

Help a reviewer turn a finding into a recorded decision. The main React view follows the user-selected Front inbox reference. A separate Reflex view demonstrates the same task in Python. Both use the same local API and SQLite review history.

The adapter reads seven retained public GitHub issues and their existing experimental predictions. It adds three explicitly simulated equipment cases. It makes no collection, language-model or predictor calls. Language-model interpretation did not run for these issues; the displayed review suggestion is rule-based. Neither tested predictor beat the baseline on the seven-case holdout.

## Start

From the repository root, run the API in one terminal:

```sh
python3 -m runtime.decision_workspace
```

The default issue source is outside Git at `~/Library/Application Support/BackIntel/Evidence/IssuePredictionTest`. Use `--source /path/to/retained/evidence` to select a copy, or `--simulation-only` to demonstrate equipment without those files. Reviews default to `~/Library/Application Support/BackIntel/DecisionWorkspace/Reviews.sqlite3`.

In another terminal:

```sh
cd frontend
npm ci
npm run dev
```

Open <http://127.0.0.1:5173>. To run the Python alternative, from the repository root:

```sh
python3 -m venv reflex_demo/.venv
reflex_demo/.venv/bin/python -m pip install -r reflex_demo/requirements.txt
python3 scripts/sync_workspace_styles.py
cd reflex_demo
.venv/bin/reflex run --env preview --backend-port 3001
```

Open <http://127.0.0.1:3001>. Preview serves the Python UI and its event connection on one loopback port. It compiles the generated frontend first. Stop each terminal with Ctrl-C.

## Verify the task

1. Open an unreviewed public issue. Read its facts and the rule-based suggestion. Expand prediction estimates and check the experimental label.
2. Open evidence. Check that the original text and fingerprint remain available. External markup is rendered as text.
3. Choose a decision and add a reason. Save, reload, then inspect decision history and later outcome. The API withholds the outcome until the first review of that exact source.
4. Open the same case in Reflex. Check that the saved review is shared. Change the decision and save again. Both revisions remain in the store.
5. Search for a nonexistent case. Switch to equipment and confirm its simulation label. Repeat at a narrow viewport using the workflow and status selectors.
6. Keep two views open and save the same case from both. The stale view must show a conflict and preserve the unsaved reason. Refresh before retrying.

The API is loopback-only and validates the origin, body, source fingerprint and expected review revision. The append-only SQLite history is the system of record. Older prototype reviews without a fingerprint are preserved but are not attached to a current source.

## Repeatable checks

```sh
cd frontend
npm run build
npm test
npm run code:quality
```

Fallow is pinned to 2.89.0. It checks dead code, dependencies, imports, cycles, duplication and complexity. Complexity findings are observations to review; they are not a claim that every component meets a maintenance threshold.

For all Python unit modules, use an isolated PostgreSQL server whose test URL names a `test_` database. The role must be able to create disposable databases. From the repository root:

```sh
BACKINTEL_TEST_DATABASE_URL=postgresql://ROLE@localhost:PORT/test_backintel \
  python3 scripts/validation/check_units.py
```

The runner creates one owned database per module, initializes the schema where needed, records logs, and removes those databases. It does not touch the installed Olist service. The focused API tests need only Python's standard library:

```sh
python3 -m unittest discover -s tests -p test_decision_workspace.py -v
```

The CI workflow repeats the build, React tests, Fallow, full Python suite and Reflex export. Browser observations and screenshots remain a separate exact-candidate product check. After collecting them into `artifacts/validation/DecisionWorkspace/BrowserChecks.json`, run:

```sh
node scripts/validation/run.mjs --manifest frontend/tabellio.validation.json \
  --expected-commit "$(git rev-parse HEAD)" \
  --output artifacts/validation/DecisionWorkspace/Candidate
```

This frontend gate is separate from the root capability-platform contract. It does not establish real-model quality, staff time saved or production readiness.
