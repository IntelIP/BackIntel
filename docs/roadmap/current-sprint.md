# Sprint 4 — Run fresh support analysis as a script

Selected October 12, 2026. **Status: Done for the local script scope.** Hudson requested a script after the browser version was delivered. See the [sprint review](sprint-4-review.md).

## User outcome

A reviewer supplies a support-ticket CSV through one command, gets the queue comparison, and keeps the finding, supporting tickets, and report. Changing the file must produce the correct new answer.

The rule reviews all channel queues tied for the longest average observed resolution time among closed tickets. It calculates directly from the supplied records.

**Owner:** Codex. **Timebox:** one focused working session. **Boundary:** local execution, fictional validation inputs, no paid calls, no model download, no database provisioning, no publication. Reuse the Sprint 3 calculation. Keep the existing authenticated workspace and recorded demo available. Toolkit qualification remains separate; S02/S03 stay unfinished.

## Ordered user issues

APP-06–APP-08 are local planning labels, not external tickets. Their delivery method now follows Hudson's script preference.

| Order | Issue | User problem | Observable result | Status |
| --- | --- | --- | --- | --- |
| 1 | APP-06 — Supply a ticket file | A reviewer wants to run analysis through a script. | One command accepts a CSV. Invalid files receive useful errors without leaving an unfinished report. | Done |
| 2 | APP-07 — Get a fresh answer | A saved demo cannot answer from new records. | The calculation saves every queue's count and average, and selects all queues tied for attention. | Done |
| 3 | APP-08 — Inspect and save the evidence | A reviewer needs records behind the answer and a report to keep. | A new folder contains the source CSV, a readable report, and structured findings with supporting records, input hash, and limits. Existing reports are preserved. | Done |

## Required checks and done condition

1. Run the actual script with the fictional example. Email must be selected, with averages of 12, 3.5, and 2 hours for Email, Chat, and Phone.
2. Change every Chat duration to 20 hours. Chat must become selected with eight supporting tickets. At 12 hours, Chat and Email must both be selected.
3. Reject invalid input without creating an output folder. Preserve size, ticket-count, encoding, column, identity, duration, and queue checks.
4. Preserve existing output folders. Recognize the included fictional example, label other records as supplied, and allow custom fictional inputs to be marked explicitly. No provider dispatch occurs.
5. The existing workspace checks and web build pass after removing the support screen. Run the required dead-code check and update the repository relationship index.
6. Record results in the sprint review, update roadmap statuses, and commit locally. No push or deployment.

**Done when:** a reviewer can supply a file, run a fresh calculation, and inspect the saved finding and records through the script; changed-input, rejection, and report-preservation checks pass.

## References

- [Completed Sprint 3 plan](sprint-3.md)
- [Sprint 3 review](sprint-3-review.md)
- [Ordered backlog](agile-backlog.md)
- [Roadmap](README.md)

## Completed result

APP-06–APP-08 are Done for the script delivery. The support screen and its local server were removed. The earlier browser delivery remains in commit `ced9f11`. See the [review](sprint-4-review.md) for the command, saved files, checks, and limits.
