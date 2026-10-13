# Sprint 4 review — Run fresh support analysis as a script

Completed October 12, 2026. **Status: Done for the local script scope.**

A reviewer supplies a support-ticket CSV through a script and gets a fresh queue comparison with supporting records and a saved report. Changing the file changes the answer and saved evidence.

The browser version was implemented and checked in commit `ced9f11`. Hudson then requested a script. The current delivery removes that support screen, its local HTTP server, and their tests. The existing authenticated workspace and recorded demo remain available.

## Closed user issues

| Issue | Observed result | Status |
| --- | --- | --- |
| APP-06 — Supply a ticket file | One command accepts the CSV and rejects invalid input before creating an output folder. The included fictional example is recognized automatically. | Done |
| APP-07 — Get a fresh answer | The example selects Email: averages are Email 12, Chat 3.5, and Phone 2 hours. Setting Chat durations to 20 selects Chat; at 12, Chat and Email are both selected. | Done |
| APP-08 — Inspect and save evidence | The output folder contains the exact input, a readable report, and structured findings with all supporting records and source hash. An existing folder cannot be overwritten. | Done |

## Run the script

From the repository root, using the existing Python environment:

```sh
.venv/bin/python -m scripts.support_analysis \
  --input docs/demo/Sprint3SupportTickets.csv \
  --output "$HOME/Library/Application Support/BackIntel/Reports/support-check"
```

For your own records, replace the input path and choose a new output folder. Add `--fictional` when using a custom fictional file. The included sample is recognized by its known content hash; other inputs are labelled supplied records whose accuracy is not independently verified.

The command prints the selected queues and the saved report path. The new folder contains:

- `input.csv`: the exact source used for the calculation.
- `report.md`: the finding, queue comparison, supporting tickets for every selected queue, and limits.
- `report.json`: the structured answer, every ticket's identity and duration, comparisons, input hash, and calculation evidence.

CSV requirements: UTF-8 with or without a byte-order mark; unique column names; required columns `ticket_id`, `channel`, and `resolution_time_hours`; nonempty, unique ticket identities; named queues; nonnegative, finite resolution hours; 2–20 queues; at most 1 MB and 10,000 tickets. Rows must not contain extra cells. Supply closed tickets only. Open-ticket status is not inferred from the file.

The calculation uses a temporary snapshot before creating any report folder. Invalid input leaves no new output folder. Existing folders are preserved. No server, browser, database, or provider request is needed. The archived Sprint 3 command continues to work.

## Checks and evidence

The actual script command saved the example's source, correct finding, supporting tickets, and both reports. The script checks passed for changed input, tied queues, fictional and supplied labels, UTF-8 byte-order marks, escaped report values, and preserving existing reports. Invalid-input checks rejected empty, oversized, excessive-ticket, malformed, incorrectly encoded, missing-column, duplicate-column, incomplete-row, duplicate-identity, negative-duration, nonfinite-duration, and invalid-queue inputs without creating an output folder. Direct calculation checks make provider dispatch fail if attempted.

The existing workspace checks and rebuilt web app passed after the support screen was removed. The required dead-code check, updated repository relationship index, documentation links, and `git diff --check` passed. Removed support-screen and server names have no remaining source registrations.

Commands used:

```sh
python3 /Users/hudson/.codex/skills/token-efficient-code-tools/scripts/code_context.py run -- \
  .venv/bin/python -m unittest discover -s tests -p test_sprint3_support_analysis.py -v
python3 /Users/hudson/.codex/skills/token-efficient-code-tools/scripts/code_context.py run -- \
  npm test --prefix apps/web
python3 /Users/hudson/.codex/skills/token-efficient-code-tools/scripts/code_context.py run -- \
  npm run build --prefix apps/web
bash scripts/check-dead-code.sh
graphify update .
```

The earlier browser receipts and screenshots under `~/Library/Application Support/BackIntel/Validation/Sprint4/` describe the historical browser delivery. They are not the validation of the script replacement.

## Scope and limits

This reuses the Sprint 3 support adapter, aggregation, and answer validator. It selects every channel tied for the longest average observed resolution time among supplied closed tickets. It does not explain delays, count open workload, or account for ticket difficulty. AI reasoning, prediction, and autonomous work were not run. Customer benefit, release readiness, and independent installation remain unverified.

The changes are committed locally. Toolkit recovery and qualification remain separate; S02/S03 are unfinished.

See the [completed Sprint 4 plan](current-sprint.md), [Sprint 3 review](sprint-3-review.md), [ordered backlog](agile-backlog.md), and [roadmap](README.md).
