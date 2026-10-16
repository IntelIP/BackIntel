---
id: S-39
title: Complete the PostgreSQL commerce reference workflow
status: Done
assignee:
  - '@codex'
created_date: '2026-10-15 01:25'
updated_date: '2026-10-15 06:27'
labels:
  - platform
  - goal-reference-workflow
dependencies:
  - S-19
  - S-22
references:
  - 'https://www.kaggle.com/datasets/carrie1/ecommerce-data'
  - 'https://archive.ics.uci.edu/dataset/352/online+retail'
  - >-
    backlog/tasks/s-38 -
    Deliver-one-checked-Databricks-answer-through-the-toolkit-and-platform.md
  - docs/retail-reference-workflow.md
priority: high
type: task
ordinal: 3035
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## User story

As a business owner, I want to connect a permitted PostgreSQL database containing the selected Kaggle commerce data and receive a checked answer, so I can see BackIntel build and run the analysis through a real data connection without setting up Databricks.

## Scope

Use the Kaggle carrie1/ecommerce-data snapshot (UCI Online Retail) as the first business-data scenario. Integrate source discovery, collection, unfamiliar-data preparation, checks, full-workload analysis, and saved execution for S-12. The source must be a separately named local PostgreSQL demo database with a scoped read-only identity. Preserve existing runtime and unrelated application databases. Reuse the shared runtime and toolkit interfaces.

The user explicitly requested an open-source alternative because no Databricks workspace is available. PostgreSQL is the selected first integration; S-26 retains the later Databricks integration. The data is real historical retail data, not current business activity. Original data files remain outside Git.

## Prerequisites and completion boundary

S-19 and S-22, the selected scenario, and a working PostgreSQL source connection. A local database is a real source connection for this story. A fake connector response or CSV-only calculation cannot satisfy connected-source acceptance. Model calls and other paid operations retain their existing authorization limits.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Connect through the selected PostgreSQL read-only identity to the dedicated demo database. The agent discovers permitted tables and columns, identifies the data needed for the S-12 question, and builds the workflow without a user-written importer or transformation script.
- [x] #2 Process all eligible records in the pinned Kaggle snapshot, account for every exclusion or failure, and return a checkable answer with source and query evidence. The PostgreSQL result reconciles with an independently calculated expectation using exact monetary arithmetic.
- [x] #3 Invoke the accepted saved workflow through the shared toolkit interface and the platform and obtain equivalent checked results. Demonstrate interruption recovery, duplicate protection, and insufficient-access handling.
- [x] #4 Record the dataset version/hash, attribution and source license evidence, historical time range, connection scope, measured time/resources, known cost, and remaining human intervention. Do not describe this as a Databricks integration, current customer operations, or proved business value.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Restore the accepted S-19 state into an isolated local runtime and provision the existing dedicated PostgreSQL reference source from the unchanged pinned Kaggle CSV using the existing source-owner bootstrap. Inject its scoped read-only connection by the existing secret-reference environment variable. Verify discovery, complete collection and denied source writes through that identity.
2. Invoke the accepted workflow on this newly collected input through the platform API and shared manual toolkit, then reconcile all rows, all product/country groups and exact totals against the saved independent expectation. Reuse S-19's measured real interruption/recovery evidence and verify duplicate/denied-access behavior on this integrated path. No new model calls are required.
3. Exercise the real local platform presentation and save a concise demonstration report with source/query links, dataset hash/attribution/license evidence, historical period, scope, elapsed time, configured resources, measured provider costs, unknown local-compute cost and remaining operator setup. Read back all member-story acceptance dispositions before completing S-39 and S-38. No commit, push, publication or deployment is included.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Selected after S-19 completed. Reuse scripts/validation/run_source_discovery.py:provision_source; this source-owner bootstrap exposes the dataset and is separate from BackIntel's agent collection. Use S19InvocationAttempt2-20261015/workflow-invocation-result.dump and workflow-package.json. Original CSV remains outside Git. No added inference spending or external workspace is required.

Acceptance review: (1) dedicated backintel_retail_source with retail_reader SELECT-only access, discovery and agent-created workflow; original run_reference.py asserted denied source writes before processing. (2) full new collection 06a29492143c processed with exact independent reconciliation and source-query-evidence.json. (3) manual/API/browser equivalent accepted run 54bb3045aa0f; repeated browser invocation returned it, revoked access returned 403; real interruption/recovery is in S19InvocationAttempt2-20261015/invocation-evidence.json. (4) reference-evidence.json and docs/retail-reference-workflow.md record source provenance, timings, measured retained database size, configured limits, costs, explicit missing CPU/peak-memory/bootstrap measurements and human intervention. Browser harness corrected display/selector/origin setup; no data pipeline rerun. All 17 web interaction checks, production build and browser check passed.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Completed the real local PostgreSQL retail workflow over all 541,909 rows. All 4,070 product-code groups, 38 country groups and exact totals matched the independent CSV expectation. Toolkit, API and browser reused the same saved run; browser checks, duplicate protection and revoked-access checks passed. S-19 supplies the real full-data interruption/recovery result. Recorded time, measured retained database bytes, configured resource caps, source hash/license/attribution, USD 0.063327825 total provider cost, unknown CPU/memory/local cost and remaining operator setup are in docs/retail-reference-workflow.md and the S39Reference-20261015 receipts. No new inference calls, commit, push or deployment.
<!-- SECTION:FINAL_SUMMARY:END -->
