---
id: S-36
title: Meet sustained workload and freshness targets
status: Done
assignee:
  - '@codex'
created_date: '2026-10-14 22:59'
updated_date: '2026-10-18 23:33'
labels:
  - platform
  - post-reference
milestone: m-5
dependencies:
  - S-29
  - S-30
  - S-33
  - S-34
references:
  - docs/retail-reference-workflow.md
  - docs/roadmap/agile-backlog.md
documentation:
  - docs/ROADMAP.md
  - docs/roadmap/README.md
  - docs/roadmap/agile-backlog.md#shared-delivery-contract
priority: medium
type: task
ordinal: 24
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Original roadmap story: S36. Original priority: P1. Work type: implementation.

## Business outcome

As an operations owner, I need complete results within the time, freshness, resource, and cost limits of my environment, so I can rely on continuous analysis at the intended scale.

## Scope

Agree representative volume, arrival rate, concurrent users/agents, completion time, freshness, failure/recovery conditions, compute/memory, and spending limits. Exercise the actual selected deployment path and fix the demonstrated constraint. Reuse internal partitioning and work near the source where justified by permission and measurements.

## Owned surface

Capacity, scheduling, concurrency, and recovery for the selected operating environment. No numeric target, paid infrastructure, or general scale guarantee is invented by this plan.

## Prerequisites

S-29, S-30, S-33, S-34 and agreed operating targets.

## Next staged delivery

Prove that the selected deployment can keep complete answers current under sustained arrivals and concurrent work. This stage establishes measured operating limits; the single local historical run is useful input but does not establish sustained capacity.

## Decisions before selection

Agree the actual environment, workload volume and arrival rate, observation duration, concurrent users and agents, correctness and freshness limits, recovery cases, CPU/memory/storage limits, and cost ceiling. Required unknown measurements must be resolved before claiming the target.

These refinements record future work. Hudson selects one implementation story at a time; no implementation, model spending, live scheduling, commit, publication, or deployment is authorized by this planning update.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Under the agreed sustained workload, results remain correct, complete, current, isolated, and within measured limits. Show overload and recovery without silent data loss, misleading completion, or unbounded cost. Report actual throughput, latency, freshness, resources, and known cost against the declared targets. A small fixture or worker count cannot establish this result; unknown required costs remain unresolved.
- [x] #2 The operating report compares the declared targets with measured completion, throughput, waiting time, freshness, CPU, peak memory, storage, and known cost over the agreed sustained period. Configured caps are reported separately from observed resource use.
- [x] #3 When arrivals exceed capacity, accepted work and waiting work remain visible and bounded. Recovery preserves complete results without manual user batching, silent loss, a false fresh-answer status, or unbounded spending.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Reuse the disposable retail PostgreSQL/API harness and retained accepted method. Give two owners separate private workflow contexts and zero model budgets.
2. Enforce six waiting analysis jobs at the shared admission boundary, including retries, with a transaction lock across domains. Preserve stable replay and expose the waiting limit in the queue response. Verify concurrent overload rejection.
3. Run the actual saved refresh and calculation paths for 30 minutes. Insert 100 clearly identified synthetic retail records at minutes 0, 5, 10, 15, 20 and 25; submit both owners through native event admissions. Compare each completed answer with independently calculated full-source totals. Measure wall-clock freshness and waiting, not run-row timestamp differences.
4. Exercise one bounded overload burst and terminate one trial-owned worker to verify retry/recovery. Sample queue, Docker CPU/memory, separate host-process CPU/memory, and additional storage. Retain progress and final operating report; stop only trial-owned services afterward.
5. Compare all observations with the approved limits; report a failed target as failed without relaxing scope. Run focused tests, dead-code/patch checks, Graphify update and scoped dependency inspection. No paid calls, commit, push, or deployment.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-18: Hudson approved the local S-36 trial: 30 minutes; two owners; at most two active jobs and six waiting jobs; one 100-record source update every five minutes; resulting answers within five minutes; one forced interruption and recovery. Preserve existing Docker allocation (4 CPUs, 8322945024 bytes memory); at most 4 GB additional storage; measure host-process use separately; zero paid model calls. Local hardware/electricity costs remain explicitly unpriced and outside the monetary pass target. Finish S-34 before activation. Scope decisions are resolved; plan the actual shared workflow and measurements before implementation.

2026-10-18 implementation: shared admission now reserves six outstanding jobs including active retries, with two active jobs at most. The queue API exposes both waiting and outstanding limits. Added the actual 30-minute native-worker trial and reused the existing private reference-import helper. Measurements cover owned calculation containers and temporary files, database use, and separate host process use. Initial database checks found four old fixture assumptions; corrected the historical 20-job expectation and fixture cleanup, and the rerun is active. Syntax, dead-code and patch checks passed; Graphify updated. The full workload remains unexecuted. Concurrent overload is tested in the disposable database; sustained capacity is established only by the actual retail trial.

Queue validation: 158 of 159 checks passed in S36QueueChecks-20261018B. The sole remaining failure was a historical-cost fixture trying to mark an unexecuted job completed; changing that fixture to cancelled passed its focused database rerun in S36FocusedChecks-20261018. No product queue guard was bypassed. The full approved trial is now running as S36Sustained-20261018A, with native workers and no paid model calls. Do not start a duplicate trial while that process is live.

Actual attempt S36Sustained-20261018A failed the freshness target: owner B first answer was correct but took 486.1 seconds; owner A had not completed. Observed 681.4 seconds before intentional stop, with three source updates; this is not a completed 30-minute trial. Peak observed storage 1.361 GB, host RSS 798 MB, container memory 893 MB; at most two active/two waiting jobs. Confirmed a new event waiting on SELECT analysis_goals FOR UPDATE, held behind a running job, plus dispatcher batch barriers delaying retries. Archive retained and native server/database stopped. Fixing read-compatible admission and prompt reuse of freed worker slots; full targets remain unchanged.

The scheduling/admission repairs and bounded short-query connection pool passed S36QueueChecks-20261018C, including focused live-database tests for free-slot reuse, concurrent read-compatible admission, queue limits, and permission revocation. Dead-code, patch and refreshed Graphify relationship checks passed. A fresh full trial S36Sustained-20261018B is now running; observe its existing process rather than starting a duplicate. No acceptance criteria are checked yet.

S36Sustained-20261018B stopped after 995.7 seconds because PostgreSQL reported Docker disk exhaustion. Before that, all six answers for three updates were correct and completed in 136.4–150.0 seconds, including worker interruption/recovery. The model-call ledger was unchanged; nine trial containers were observed. This is still a failed, incomplete 30-minute trial. Host storage has about 35 GB free; the shared Docker storage is constrained by existing volumes/cache. Keep unrelated Docker data intact. Next trial uses a fresh host bind mount inside its own evidence directory, within the same approved 4 GB allowance and unchanged CPU/memory allocation. Also count prior S-36 artifacts in storage and verify every product group as well as all countries/totals.

S36Sustained-20261018C is now running with a fresh trial-owned PostgreSQL host bind mount, no shared Docker cache/volume deletion, and unchanged four-CPU/about-eight-GB Docker allocation. Prior S-36 artifact bytes are included in the four-GB storage guard. Every product and country group is checked independently. Current process handle is 15518; inspect that live handle and retained report rather than restarting the trial.

Live checkpoint: S36Sustained-20261018C is running; 369.4 seconds observed, 2 updates admitted, 2 answers reconciled against all country/product groups. Slowest completed answer: 139.2s. Keep observing existing exec session 15518; do not start a duplicate or mark acceptance yet.

2026-10-18: S36Sustained-20261018C passed the full 1800.93-second local workload. Six 100-record source updates produced twelve independently reconciled complete answers over 542,009–542,509 rows, including all countries and products. Freshness was 116.95–139.23 seconds against 300 seconds; the forced interruption recovered on attempt two. Peak measured active/waiting jobs: 2/2; six-outstanding admission limit retained. Peak sampled container memory 1,278,570,496 bytes; host RSS 1,611,628,544 bytes and CPU 131.2%; observed container CPU 460.94 CPU-seconds with sampling limits disclosed. Peak additional storage 2,517,318,096 bytes, including prior attempts; retained storage with archive 2,216,769,519 bytes. Docker allocation unchanged. Zero new model requests and US$0 provider cost; local hardware/electricity unpriced as approved. Native server and database container stopped; evidence retained at /Users/hudson/Library/Application Support/BackIntel/Validation/S36Sustained-20261018C. Focused suite: 162 checks passed; prior syntax, dead-code, patch and scoped Graphify checks passed. Documentation now reports targets, observations and limits. This validates the local working tree, not a release or production capacity.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Completed the agreed 30-minute local sustained workload: twelve correct full-source answers, all within five minutes, with interruption recovery, bounded admission and measured resources below the approved limits. No model calls. Evidence: S36Sustained-20261018C; operating report in docs/saved-workflows.md.
<!-- SECTION:FINAL_SUMMARY:END -->
