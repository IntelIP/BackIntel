# Independent local PostgreSQL installation (S-35)

This candidate lets an operator connect the public Online Retail dataset, give BackIntel a business question, inspect its proposed work and checked answer, and operate the saved workflow. Hudson is the independent tester. Record the actual result of each operator step below before treating S-35 as complete.

The package contains the current runtime, pinned Python requirements, built web interface, and source. It starts with a new PostgreSQL database and new access grants. It does not restore the implementer's database or substitute recorded model replies. This declared installation covers the connected PostgreSQL retail workflow. Databricks, optional local prediction-model weights, publication, and production operation are separate scopes.

## Install the candidate

Use Python 3.12 and a running local Docker daemon. Keep the existing four-CPU/about-eight-GB Docker allocation. The first setup may download public PostgreSQL and Python images. The built interface is included in the candidate; Node is needed only when rebuilding it from source.

Extract the supplied ZIP, enter its `BackIntel` directory, and create a fresh Python environment:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.platform.txt
```

Download `data.csv` from [Kaggle ecommerce-data](https://www.kaggle.com/datasets/carrie1/ecommerce-data), derived from [UCI Online Retail](https://archive.ics.uci.edu/dataset/352/online+retail). Attribution: Chen, D. (2015), DOI 10.24432/C5BW33. UCI states CC BY 4.0; Kaggle's license field is Unknown. Review those source statements before acknowledging the terms. The recorded snapshot contains 541,909 rows and has SHA-256 `d07aec9960083af2339975a3f9d3b26313b342dcd9f86cce0b919b1cde639a44`.

Choose a new private state directory outside the source package. In these commands, replace the two example absolute paths with your state directory and downloaded CSV:

```sh
.venv/bin/python -m scripts.local_platform --state /absolute/path/BackIntelLocalState setup --csv /absolute/path/data.csv --acknowledge-terms
.venv/bin/python -m scripts.local_platform --state /absolute/path/BackIntelLocalState start
```

Setup reports `ready`, 541,909 source rows, source reference `online-retail-postgres`, and model allowance zero. The source reader can only read `retail_raw`; owner credentials are used only for local installation and the explicit synthetic-update command. Database passwords and access grants stay in the private state directory with owner-only file permissions. Do not share that directory or copy it into source control.

The API runs in the foreground on `http://127.0.0.1:2028`. Startup refuses an occupied port and does not stop an existing service. In a second terminal, from the same candidate directory, open your manager access:

```sh
.venv/bin/python -m scripts.local_platform --state /absolute/path/BackIntelLocalState open
.venv/bin/python -m scripts.local_platform --state /absolute/path/BackIntelLocalState status
```

## Supply the question and limits

Create a commerce question using source reference `online-retail-postgres`, permitted schema `retail_raw`, and read-only source actions. A suitable first question is: “Which countries and products contribute most to net invoice value, and how much value comes from cancellation invoices?”

Use quantity multiplied by unit price as the GBP invoice-value measure; it is not audited revenue. Use all 541,909 rows across all countries and the full historical source period. Request reconciliation of totals, country groups, product groups, and record coverage. Set source limits to 104,857,600 bytes and 900 seconds, output to local, and list any unresolved business meanings for review. Confirm the objective before allowing work.

Source discovery can run without a model allowance. Fresh planning, field interpretation, and analysis-method generation need provider access and a new, explicit spending allowance. **No S-35 live model spending has been approved or executed by this installation work.** Earlier story allowances do not apply here. Until that allowance is agreed, stop after checking discovery and the proposed operating scope.

After a separate allowance is approved, inject `OPENROUTER_API_KEY` from your local credential store into the terminal environment; never put it in the command, state file, question, or report. Stop the foreground API with Ctrl-C and restart with both `--allow-models` and `--budget-usd AMOUNT`. AMOUNT is the explicitly approved cumulative manager cap, at most US$0.50, not an allowance added on every restart. Existing request, objective, domain and suite limits still apply. The default start clears inherited provider keys and sets the manager cap to zero.

Use the existing connected-source controls to discover the source, create a plan, collect the permitted records, interpret fields, prepare and check the information, and calculate the answer. Inspect warnings and source evidence before saving the successful workflow. Expected acceptance is a checked answer over the complete source with retained source and calculation evidence. A failed or blocked stage is not a completed answer. [Saved workflow guidance](saved-workflows.md) describes the controls, triggers, and retained evidence.

## Verify refresh and recovery

After accepting and saving a real answer, configure the existing event or schedule trigger with a short expiry and a small run limit. Saved deterministic refreshes use the accepted method without further model calls. Pause the trigger when this check is complete.

To introduce one clearly synthetic record into this installation's disposable source, run:

```sh
.venv/bin/python -m scripts.local_platform --state /absolute/path/BackIntelLocalState demo-update
```

This explicit owner action appends one row with quantity 1 and unit price GBP 10, dated within the source period, marked `S35-DEMO` and “Explicitly synthetic independent-installation check.” It prints the new source-row identity. It is a fictional transaction for the installation check. Observe the next saved-workflow source refresh: coverage should increase by one and net invoice value by GBP 10, with traceable source-change history. Do not manually rebuild or split the workflow.

During another accepted refresh, stop the foreground API with Ctrl-C, restart it from the same state directory, and inspect the existing job and answer history. Confirm the work resumes or reports an actionable failure without losing the last accepted answer or duplicating a charge. If restarting with live model access, reuse the same approved cumulative cap; a restart does not replenish it. Record any manual repair or implementer help.

## Shutdown and recover

Press Ctrl-C in the foreground API terminal, then stop this installation's database:

```sh
.venv/bin/python -m scripts.local_platform --state /absolute/path/BackIntelLocalState stop
```

Saved records and access grants remain in the state directory. Starting again reuses that database and updates local connection bindings if Docker assigns a different port. The stop command checks the installation label before touching a container. It does not prune Docker or delete data. Setup refuses an existing state directory; investigate an incomplete setup instead of overwriting it. Keep the candidate and its matching state together. Never reuse state while another copy is running against it.

If an image download, database startup, package installation, source hash, or port check fails, retain the error and candidate identity. Fix that specific prerequisite and report the intervention. Do not use the implementer's private environment or an old database archive to make the acceptance pass.

## Operator acceptance record

- Candidate ZIP hash and `local-candidate.json` base commit: pending independent run.
- Clean installation, credentials, source discovery and confirmed question: pending Hudson.
- Checked complete answer and any business-meaning decisions: pending Hudson and a separate model allowance.
- Synthetic update, current answer and retained change history: pending Hudson.
- Interruption/restart, retained answer and spending ledger: pending Hudson.
- Shutdown and any undocumented configuration or implementer assistance: pending Hudson.

An implementer check confirms only the tested installation behavior. It cannot count as Hudson's independent operation or establish production readiness. Local hardware and electricity remain unpriced.

## Rebuild the local candidate

From the selected source checkout, install the web dependencies and build the interface, then package it:

```sh
npm ci --prefix apps/web
npm run build --prefix apps/web
python3 -m scripts.local_platform package --output /absolute/path/BackIntelLocalCandidate.zip
```

The ZIP contains a manifest of file hashes and the base Git commit, explicitly identifying a working-tree candidate. It excludes ignored private state, datasets, credentials, virtual environments and node_modules. Packaging is local and does not commit, publish, or deploy the product.
