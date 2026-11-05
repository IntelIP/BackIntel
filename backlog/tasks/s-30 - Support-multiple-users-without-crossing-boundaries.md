---
id: S-30
title: Support multiple users without crossing boundaries
status: Done
assignee:
  - '@codex'
created_date: '2026-10-14 22:59'
updated_date: '2026-10-17 04:34'
labels:
  - platform
  - post-reference
milestone: m-5
dependencies:
  - S-19
  - S-04
  - S-05
references:
  - docs/retail-reference-workflow.md
  - docs/roadmap/agile-backlog.md
documentation:
  - docs/ROADMAP.md
  - docs/roadmap/README.md
  - docs/roadmap/agile-backlog.md#shared-delivery-contract
priority: medium
type: task
ordinal: 23
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Original roadmap story: S30. Original priority: P1. Work type: implementation.

## Business outcome

As an application owner, I need multiple users to work safely, so that their data, permissions, jobs, and budgets remain separate.

## Scope

Agree the representative concurrency target; exercise distinct roles and source scopes; resolve demonstrated contention while preserving admission and recovery guarantees.

## Owned surface

Selected multi-user execution, isolation, and capacity constraints. High risk: access and concurrent financial admission.

## Prerequisites

S-19, S-04, S-05 and an agreed concurrent-user target.

## Next staged delivery

Let several permitted users run the selected workflows while keeping their information, results, progress, and spending separate. User separation is required before claiming sustained operation for a shared deployment.

## Decisions before selection

Agree representative roles, source scopes, simultaneous-user and workload targets, shared resource limits, and how queued work is shown. Do not invent a concurrency target from the current machine or worker count.

These refinements record future work. Hudson selects one implementation story at a time; no implementation, model spending, live scheduling, commit, publication, or deployment is authorized by this planning update.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Concurrent permitted users complete the selected workflows without cross-user disclosure or overspending. An attempted cross-user access is denied. Report observed capacity rather than inferring it from the current worker configuration.
- [x] #2 The agreed concurrent run records results, failures, waiting time, and known usage by user and for the shared service. Shared capacity contention is visible, and one user cannot inspect, change, cancel, or spend against another user's work without explicit permission.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Add private-by-default objective access with explicit sharing; enforce it in application and direct workflow entry points, retaining independent source grants. Separate administration of shared sources and account grants from ordinary objective ownership. 2. Add owner-level spending limits under existing shared limits and expose only authorized usage and queue status. 3. Reuse the durable dispatcher with a bounded two-job pool and retain existing recovery controls. 4. Run the approved four-analysis retail workload with two owners and one read-only viewer; check result parity, cross-user reads/writes/cancellation/spending denial, explicit sharing, queue visibility and no paid requests. Exercise concurrent budget admission with local simulated charges, and run relevant regression, browser, dead-code and dependency checks. 5. Record measured completion, failures, waiting and known usage; complete S-30 only when its approved scope passes.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Hudson approved the initial local scope: two workflow owners with separate source access and budgets, plus one read-only user; each owner submits two full retail analyses; at most two active jobs with waiting work visible; no paid model calls. Parent roadmap execution remains active beyond this story. Current gaps: domain-wide objective visibility and management, no individual owner budget cap, and a single-job dispatcher.

Implementation progress: private objective access and explicit sharing, independent user caps, two-job dispatcher, and visible queue are implemented. Web build and 25 web tests passed; dead-code check passed; Graphify refreshed. Disposable regression runs exposed outdated synchronous revocation fixtures that attempted writes after newly added authority locks; fixtures are being moved before the first lock, preserving revocation checks. The four-owner-context retained-retail scenario and browser runner are implemented but have not passed. S-30 remains In Progress; no paid calls, commits, pushes, or deployment. Next: finish regressions, run four real saved-workflow executions, record measured queue/waiting/results, then review acceptance.

Current verification: all 158 database/application regressions passed in Validation/S30Retail-20261017G/multiuser-checks.log; 25 web tests and current build passed. The live native loader failure was reproduced and fixed by evaluating API request annotations at import; its direct regression passes. Real API now denies cross-owner reads/changes and viewer execution and accepts an explicit read share. Retail harness import IDs corrected to the required 64-character digest format. Active retail scenario: Validation/S30Retail-20261017H, exec session 60354. It must finish four fresh workflow executions, browser checks, full calculation parity, and queue/usage measurements before S-30 can be completed. No paid requests or Git publication.

Acceptance completed for the agreed local scope. H removed its temporary database and stopped the native server. No commit, push, deployment, or paid inference occurred. Broader goal remains active. S-34 is the next dependency for S-36; its Databricks dependency and source/destination scope require the explicit local-alternative decision currently asked in this chat.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Completed the approved local multi-user scope. Two independent owners each completed two real saved-workflow executions over all 541,909 retail records; every full calculation matched the reference. Four runs finished in 280.816 seconds after admission, with at most two active jobs, visible waiting work, no failed/excluded/pending rows, and zero model calls or charges. Owners waited 1.99–2.76 seconds and 140.71–140.95 seconds respectively. Native API and browser checks verified private workspaces, explicit read-only sharing, cross-owner denial, and per-user usage. Concurrent simulated reservations enforced each user cap. Evidence: Validation/S30Retail-20261017H (retail, queue, results, browser); S30Retail-20261017G/multiuser-checks.log (158 passing regressions). All 25 web tests, web build, dead-code check, patch check, and Graphify refresh passed. This is one local retained-method trial; local computer cost is unknown, and sustained operation remains S-36.
<!-- SECTION:FINAL_SUMMARY:END -->
