# Sprint 4 — Run fresh support analysis from the app

Selected October 12, 2026. **Status: Done for the approved local app scope.** See the [sprint review](sprint-4-review.md). Hudson approved executing the proposed plan.

## User outcome

A reviewer chooses a support-ticket CSV, gets the queue comparison in the current app, inspects the supporting tickets, and saves a self-contained checked report. Changing the file must produce the correct new answer.

The rule reviews all channel queues tied for the longest average observed resolution time among closed tickets. This is a local statistical calculation, not AI reasoning or a prediction.

**Owner:** Codex. **Timebox:** one focused working session. **Boundary:** local execution and fictional validation inputs, no paid calls, no model download, no database provisioning, no publication. Reuse the current web app and Sprint 3 calculation. Keep the existing authenticated workspace and recorded demo available. Toolkit qualification remains separate; S02/S03 stay unfinished.

## Ordered user issues

APP-06–APP-08 are local planning labels, not external tickets.

| Order | Issue | User problem | Observable result | Status |
| --- | --- | --- | --- | --- |
| 1 | APP-06 — Choose a ticket file | A reviewer should not need a terminal to supply tickets. | The app accepts a CSV or offers a clearly fictional example. Invalid files receive useful errors. | Done |
| 2 | APP-07 — Get a fresh answer | A saved demo cannot answer from new records. | A local calculation shows every queue, its count and average, and every queue tied for attention. | Done |
| 3 | APP-08 — Inspect and save the evidence | A reviewer needs records behind the answer and a report to keep. | Supporting ticket identities and durations are visible. A downloaded report includes the finding, evidence, input hash, and limits. | Done |

## Required checks and done condition

1. Run the actual current app in a browser and select the fictional example. Email must be selected, with averages of 12, 3.5, and 2 hours for Email, Chat, and Phone.
2. Upload an altered fictional file with every Chat duration set to 20 hours. Chat must become selected, and its supporting records and downloaded report must reflect that new input.
3. Selecting a new file clears the previous report. Invalid input shows an error without retaining a stale result.
4. The server rejects malformed input, oversized files, and requests from another website. No provider dispatch occurs.
5. The existing workspace checks and current app build pass. Inspect the browser at desktop and narrow widths.
6. Record observed results in the sprint review, update roadmap statuses, and commit locally. No push or deployment.

**Done when:** a reviewer can complete file selection, fresh analysis, evidence inspection, and saving through the app; changed-input and rejection checks pass.

## References

- [Completed Sprint 3 plan](sprint-3.md)
- [Sprint 3 review](sprint-3-review.md)
- [Ordered backlog](agile-backlog.md)
- [Roadmap](README.md)

## Completed result

APP-06–APP-08 are Done. The actual browser flow selects Email from the fictional example, then selects Chat when an uploaded fictional file changes Chat durations to 20 hours. Supporting records and both downloaded reports match the selected inputs. See the [review](sprint-4-review.md) for setup, checks, and limits.
