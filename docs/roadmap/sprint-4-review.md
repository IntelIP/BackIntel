# Sprint 4 review — Run fresh support analysis from the app

Completed October 12, 2026. **Status: Done for the approved local app scope.**

A reviewer can choose a support-ticket CSV in the current BackIntel web app, run a fresh local calculation, inspect supporting tickets, and save a self-contained checked report. Changing the file changes the answer and saved evidence.

## Closed user issues

| Issue | Observed result | Status |
| --- | --- | --- |
| APP-06 — Choose a ticket file | Native file selection accepts the support CSV. The app also offers a clearly fictional example. Invalid input receives useful errors. | Done |
| APP-07 — Get a fresh answer | The example selects Email: averages are Email 12, Chat 3.5, and Phone 2 hours. Uploading fictional tickets with Chat durations changed to 20 hours selects Chat. | Done |
| APP-08 — Inspect and save evidence | Supporting ticket identities and durations are visible. Browser downloads contain the correct finding, records, source hash, and limits for each input. | Done |

## Open the local app

From the repository root, using the existing repository dependencies:

```sh
npm run build --prefix apps/web
.venv/bin/python -m scripts.support_workspace --port 2055
```

Open <http://127.0.0.1:2055/support>. Stop with Ctrl-C. Choose another port if 2055 is occupied.

Select **Use fictional example**, then **Run analysis**. Expand **Supporting tickets** and choose **Save checked report**. To use another file, select it through **Support-ticket file** and run again.

CSV requirements: UTF-8; unique column names; nonempty, unique `ticket_id`; a named `channel`; nonnegative, finite `resolution_time_hours`; 2–20 queues; at most 1 MB and 10,000 tickets. Supply closed tickets only. Open-ticket status is not inferred from the file.

The calculation runs on this computer. Uploads use temporary files that are removed after calculation. Reports are saved through the browser's download control. The reviewer supplies the file; the app does not establish its real-world accuracy.

## Checks and evidence

The current app build and all 14 existing workspace checks passed. The existing Sprint 3 changed-input check also passed. The new HTTP integration check exercised actual local calculations while making provider dispatch fail if attempted. It checked changed input, tied queues, input hashes, supporting records, self-contained reports, escaped report values, and rejection of malformed, negative, oversized, wrong-format, cross-site, and wrong-host requests.

The browser check used the real current web build and local HTTP handler. It selected the example, uploaded an altered fictional CSV, inspected all eight supporting tickets for each selected queue, and downloaded both reports. A new selection cleared the previous answer and download link. Invalid input displayed an error with no stale answer. Desktop and 390-pixel layouts were inspected; narrow tables scroll within their own containers. No browser page errors occurred.

Commands used:

```sh
python3 /Users/hudson/.codex/skills/token-efficient-code-tools/scripts/code_context.py run -- \
  .venv/bin/python -m unittest discover -s tests -p test_sprint3_support_analysis.py -v
python3 /Users/hudson/.codex/skills/token-efficient-code-tools/scripts/code_context.py run -- \
  .venv/bin/python -m unittest discover -s tests -p test_support_workspace.py -v
python3 /Users/hudson/.codex/skills/token-efficient-code-tools/scripts/code_context.py run -- \
  npm test --prefix apps/web
python3 /Users/hudson/.codex/skills/token-efficient-code-tools/scripts/code_context.py run -- \
  npm run build --prefix apps/web
python3 /Users/hudson/.codex/skills/token-efficient-code-tools/scripts/code_context.py run -- \
  node apps/web/tests/support-browser.mjs
```

Each browser run writes a receipt, the altered fictional input, both downloaded reports, and desktop/narrow screenshots under `~/Library/Application Support/BackIntel/Validation/Sprint4/`. The receipt identifies the source revision and whether the working tree was clean. The final local commit is checked using the same commands.

The repository relationship index was updated with `graphify update .`. The web entry point, new upload handler, shared calculation, and callers were checked against current source. Documentation links and `git diff --check` passed.

## Scope and limits

This is the current web app's local support-check mode. It reuses the Sprint 3 support adapter, aggregation, and answer validator. The existing authenticated workspace and the separately packaged recorded demo remain available.

The review rule selects every channel tied for the longest average observed resolution time among closed tickets. It does not explain delays, count open workload, or account for ticket difficulty. No AI reasoning, prediction, or paid provider call is involved. Customer benefit, release readiness, and independent installation remain unverified.

Toolkit recovery and qualification are still separate. S02/S03 remain unfinished.

See the [completed Sprint 4 plan](current-sprint.md), [Sprint 3 review](sprint-3-review.md), [ordered backlog](agile-backlog.md), and [roadmap](README.md).
