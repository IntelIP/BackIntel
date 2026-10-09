# Issue-review data test — 2026-09-28

**Follow-up:** the [first actual prediction test](issue-prediction-results.md) recovered the missing archive hour, established bounded recorded-history outcomes, and executed both local predictors. The initial findings below remain the record of the first, narrower check.

**Question:** can we recover original issue text and seven-day outcomes well enough to test response-gap predictions?

**Result: blocked for prediction testing.** The first source check ran on 20 real issues. Original text is largely recoverable, but this bounded check does not establish complete seven-day coverage or two verified outcome classes. No models ran and no GitHub records changed.

| Check | Result |
| --- | --- |
| Current issue, comment, and event histories collected | 20 of 20; paginated and comment counts reconciled |
| Creation records recovered from original GH Archive files | 19 of 20; recovered creation timestamps match GitHub |
| Currently visible comments within seven days matched to original archives | 34 of 34 |
| Cases with a verified qualifying historical maintainer response | 3 |
| Cases with a verified seven-day response gap | Not established |
| Original versus current text differences | 2 titles and 5 bodies changed |
| Historical role differs from the archive index field | 13 comments |
| Deterministic role, bot, author, and deadline boundary checks | Passed |

## What the test caught

- [Issue #201663](https://github.com/microsoft/vscode/issues/201663) has a current creation timestamp but no opening event was found in its expected archive hour. Its original input remains excluded; it was not replaced with current text.
- The public ClickHouse index did not preserve comment roles correctly for this sample. Original archive payloads are required for this target.
- Current GitHub roles can differ from roles recorded at comment creation. Current roles must not determine historical response labels.
- Matching all currently visible comments does not establish that no other activity existed. Only selected creation/comment hours were read, not the full seven-day event windows. No absence-based label was accepted.

## Scope and limits

Selected the earliest 20 **currently searchable** non-PR issues created in January 2024, ordered by creation time and issue ID. This is a feasibility sample, not the frozen training cohort: historical issues no longer searchable may change eligibility and ordering.

The observed histories suggest seven response-gap cases and thirteen other cases, but those counts are **provisional, not training labels**. Positive archived response evidence verifies three non-gap outcomes. Full state and absence coverage remains unfinished. Public archive gaps and deleted activity remain source limitations even after a wider scan.

The bot exclusions used for this check were `vscodenpa`, `VSCodeTriageBot`, and `github-actions[bot]`, plus accounts marked `Bot` or ending in `[bot]`. Original authors were excluded. Only historical `OWNER`, `MEMBER`, or `COLLABORATOR` comments within the inclusive seven-day window qualified.

## Next action

Resolve creation and full-window coverage before freezing the model cohort. Keep incomplete cases excluded. The recovered sources can support a review-screen preview, with any simulated findings clearly labelled. Do not expand to training on the provisional labels.

## Evidence and reproduction

Local evidence is stored at `~/Library/Application Support/BackIntel/Evidence/IssueFeasibility/`: `report.html` shows the 20-case table; `assessment.json` contains individual outcomes and limits; `evidence-manifest.json` records file hashes. Raw third-party content remains outside the repository.

`collect.py` retrieves/caches read-only API records and the discovery index; `check_archive.py` retrieves selected original events; `assess.py` repeats the assessment offline and checks the label boundaries. Run the last script to reproduce results without network or model calls. These are research scripts, not a new product integration or exact-commit product acceptance.

Sources: [GH Archive](https://www.gharchive.org/), the hourly files recorded in the evidence manifest, [GitHub issue comments](https://docs.github.com/en/rest/issues/comments), [GitHub issue events](https://docs.github.com/en/rest/issues/events), and the [ClickHouse public query service](https://play.clickhouse.com/). Retrieval: September 28, 2026, America/New_York (September 29 UTC). Model calls: zero. Provider spending: zero. Local compute/network costs were not priced.
