# Sprint 3 — Produce and check a fresh support finding

Selected October 12, 2026. **Status: Done for the approved local sample scope.** See the [sprint review](sprint-3-review.md). Hudson approved this sprint with “Proceed.”

## User outcome

A reviewer supplies a new, fictional ticket set and receives a finding with the supporting records. This answers “Which queue needs attention?” under a stated rule, rather than playing back the Sprint 2 recording.

**Rule:** group closed tickets by communication channel, treat each channel as a queue, and review every queue tied for the highest average resolution time. This is a descriptive check of observed durations, not a prediction or an autonomous model interpretation.

**Owner:** Codex. **Timebox:** one focused working session. **Boundary:** local execution, no paid calls, no private data, no credential discovery, no changes to existing services. Reuse the current analysis functions and installed environment. The separate toolkit stories S02/S03 remain unfinished.

## Ordered user issues

APP-03–APP-05 are local planning labels, not external tickets. Start them in order.

| Order | Issue | User problem | Observable result | Status |
| --- | --- | --- | --- | --- |
| 1 | APP-03 — Prepare a fresh input and local runner | A saved recording cannot show a new calculation. | A new fictional CSV is read by the current support adapter and local analysis functions. | Done |
| 2 | APP-04 — Produce the finding and evidence | A reviewer needs an answer and the records behind it. | A report names the queue to review, compares all queues, and lists supporting ticket identities and durations. | Done |
| 3 | APP-05 — Check the answer independently | A plausible-looking report can still be wrong or fixed to one example. | An independent raw-file calculation agrees, and changed ticket durations change the selected queue. | Done |

## APP-03 — Prepare a fresh input and local runner

1. Create a small, explicitly fictional CSV in the existing support-ticket format. Retain it as a reproducible example.
2. Reuse `runtime.analysis_data.support`, `runtime.analysis_agent.aggregate`, and `runtime.analysis_agent.validate_answer`.
3. Use the existing local Python environment. Invoke no agent/provider request, model download, database provisioning, or credentials.
4. Keep the closed-ticket observation and channel-queue definition explicit.

**Done when:** the real support adapter reads the new records and the local analysis functions run successfully.

## APP-04 — Produce the finding and evidence

1. Copy the input into a new output folder so earlier results stay intact.
2. Calculate count and average resolution time per channel. Select all highest-average queues.
3. Validate the factual claims against the calculated table.
4. Save the input snapshot, machine-readable result, and plain report with ticket evidence and input identity.

**Done when:** a new report answers the stated question and exposes the records and rule used.

## APP-05 — Check the answer independently

1. Read the raw CSV with a separate calculation using decimal arithmetic; do not reuse the analysis adapter or aggregation function for this check.
2. Compare queue counts, total hours, averages, selected queue, and cited ticket identities with the report.
3. Change the sample so another queue becomes the slowest. Confirm the result changes and no provider dispatch occurs.
4. Run the focused test, record commands and results, and close this sprint when the outcome is demonstrated.

**Done when:** the independent calculation agrees and the changed-input check proves the answer comes from the new records.

## Review boundary

This sprint checks a fresh local statistical answer on fictional closed tickets. It does not establish prediction accuracy, live agent reasoning, scheduled processing, customer value, release readiness, or developer-toolkit qualification. Do not close S02/S03 from these results.

## References

- [Completed Sprint 2 plan](sprint-2.md)
- [Sprint 2 results](sprint-2-review.md)
- [Ordered backlog](agile-backlog.md)
- [Roadmap](README.md)

## Completed result

The [saved report](../demo/sprint-3-support-result/report.md) selects Email from 24 fictional closed tickets: Email averages 12 hours, Chat 3.5, and Phone 2. The independent raw-file check agrees. Changing Chat durations to 20 hours selects Chat without provider dispatch. APP-03–APP-05 are Done; see the [review](sprint-3-review.md) for commands, evidence, and limits.
