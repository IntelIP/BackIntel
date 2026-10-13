# Sprint 3 review — Produce and check a fresh support finding

Completed October 12, 2026. **Status: Done for the approved local sample scope.**

A reviewer can supply a fresh support-ticket CSV and receive an answer with the records behind it. The [saved report](../demo/sprint-3-support-result/report.md) answers “Which queue needs attention?” for 24 explicitly fictional closed tickets.

The rule selects every channel queue tied for the highest average resolution time. Email is selected in this sample. These are observed durations, not predicted outcomes.

| Queue | Closed tickets | Total resolution hours | Average hours |
| --- | --- | --- | --- |
| Email | 8 | 96 | 12 |
| Chat | 8 | 28 | 3.5 |
| Phone | 8 | 16 | 2 |

## Closed user issues

| Issue | Result | Status |
| --- | --- | --- |
| APP-03 — Prepare a fresh input and local runner | The existing support adapter reads the new CSV. Existing aggregation and answer validation functions run locally. | Done |
| APP-04 — Produce the finding and evidence | The report compares queues and cites all eight Email ticket identities and durations. It retains the input and its SHA-256 hash. | Done |
| APP-05 — Check the answer independently | A separate raw-file calculation agrees. Changing Chat durations to 20 hours makes Chat the selected queue. | Done |

## Execution and direct checks

The [runner](../../scripts/sprint3_support_analysis.py) reuses `runtime.analysis_data.support`, `runtime.analysis_agent.aggregate`, and `runtime.analysis_agent.validate_answer`. It runs without a database or provider request. It requires a new output folder so saved results remain intact.

From the repository root, the successful sample command was:

```sh
.venv/bin/python -m scripts.sprint3_support_analysis \
  --input docs/demo/Sprint3SupportTickets.csv \
  --output docs/demo/sprint-3-support-result
```

The output folder now exists. For another run, choose a different output folder. The command saved [the input snapshot](../demo/sprint-3-support-result/input.csv), [the report](../demo/sprint-3-support-result/report.md), and [the calculation details](../demo/sprint-3-support-result/report.json).

The focused changed-input check passed:

```sh
python3 /Users/hudson/.codex/skills/token-efficient-code-tools/scripts/code_context.py run -- \
  .venv/bin/python -m unittest discover -s tests \
  -p test_sprint3_support_analysis.py -v
```

That check changes all eight Chat durations to 20 hours, confirms Chat is selected with eight tickets and a 20-hour average, and makes provider dispatch fail if attempted. The answer validator remains unchanged. The report uses its supported comparison wording.

A separate Python check read the original CSV with `csv.DictReader` and calculated totals and averages with `Decimal`. It did not import the support adapter or aggregation function. Queue counts, total hours, averages, selected queues, all ticket identities and durations, supporting identities in Markdown, the input hash, and saved input bytes agreed. Its results are saved in [verification.json](../demo/sprint-3-support-result/verification.json).

Input SHA-256: `b19bc97f78f66e1d32ee519d0f743b783a9d7c3d16034381efda5e38471309f4`.

The repository relationship index was updated with `graphify update .` through the code-context wrapper. The runner's callers and helper dependencies were inspected and checked against current source. Local links passed for all seven changed or generated documents checked. `git diff --check` passed.

## Limits and roadmap position

This sprint demonstrates a fresh local statistical calculation on fictional closed tickets. No paid provider calls were made. The finding does not show why a queue is slower or account for open tickets, ticket difficulty, or business priorities.

Live agent reasoning, prediction accuracy, scheduled processing, measured customer benefit, release readiness, and the separate developer toolkit remain unverified by this result. Toolkit stories S02/S03 stay unfinished.

See the [completed Sprint 3 plan](sprint-3.md), [ordered backlog](agile-backlog.md), and [Sprint 2 review](sprint-2-review.md).
