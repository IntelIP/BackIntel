---
id: S-24
title: Collect incremental changes and refresh the result
status: Done
assignee:
  - '@codex'
created_date: '2026-10-14 22:59'
updated_date: '2026-10-16 08:00'
labels:
  - toolkit
  - platform
  - shared-core
  - post-reference
milestone: m-4
dependencies:
  - S-23
  - S-20
  - S-21
references:
  - docs/retail-reference-workflow.md
  - docs/roadmap/agile-backlog.md
documentation:
  - docs/ROADMAP.md
  - docs/roadmap/README.md
  - docs/roadmap/agile-backlog.md#shared-delivery-contract
priority: medium
type: task
ordinal: 19
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Original roadmap story: S24. Original priority: P1. Work type: implementation.

## Business outcome

As an operations user, I need new and changed source records incorporated, so that a recurring answer stays current without unnecessary full recollection.

## Scope

Retain collection progress; apply the selected source's update and deletion semantics; invoke the saved workflow and recover an interrupted update.

## Owned surface

Incremental extraction, source-change admission, refresh, and recovery for the selected connector.

## Prerequisites

S-23, S-20, S-21.

## Next staged delivery

Use the selected source to keep a checked business answer current as information arrives or is corrected. Collection must retain original records and progress without asking the user to split work into batches.

## Decisions before selection

Define the source change marker and how insertions, corrections, deletions, and late-arriving records are represented. State when a complete recollection is necessary instead of pretending every source supports incremental reads.

These refinements record future work. Hudson selects one implementation story at a time; no implementation, model spending, live scheduling, commit, publication, or deployment is authorized by this planning update.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Add and change known records, then show the correct refreshed answer and retained originals. Repeated or interrupted collection does not lose or duplicate accepted records. Failed collection preserves the last useful result and identifies staleness.
- [x] #2 The selected change cases include additions, corrections, and the agreed deletion semantics. The refreshed answer reconciles against an independent complete calculation of the resulting source state, with retained originals and counts for affected, excluded, failed, and pending records.
- [x] #3 The result records which source changes were read and which workflow steps were reused or recomputed. A necessary full reread is disclosed. Toolkit and platform callers observe the same accepted result and freshness state after repetition or interruption.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Outcome: keep the saved retail answer current through additions, corrections, and deletions from the permitted PostgreSQL source, using the same toolkit and application contract. Hudson approved removing deleted records from current totals while preserving their originals and deletion history. Start only after S-21 is accepted.

1. Extend the existing complete-collection contract with source-side row fingerprints and a stable primary key. Read change markers within one consistent source snapshot; fetch changed record values and reconstruct the complete current input from verified retained rows plus changed rows. Record inserts, replacements, deletions, retained originals, source observation time, and complete affected/excluded/failed/pending counts. Disclose initial or required full rereads and metadata scans.
2. Persist the collection-to-saved-workflow progression using the existing durable job machinery. Retries and repeated event identities reuse accepted work. Interrupted or failed collection cannot publish a fresh answer or lose the last accepted result. Recheck current source authority and existing limits throughout.
3. Connect manual toolkit/application refresh and the bounded S-20 event/schedule path to this same progression. Keep Aegra as the sole timer owner. The user selects a saved workflow and operating limits; no hand-written collection query or repeated manual file splitting is required.
4. Demonstrate changes on a disposable PostgreSQL copy of the historical retail source. Include an insertion, a correction, a deletion, duplicate invocation, interrupted recovery, and failed collection. Independently calculate the complete resulting source totals and groups and reconcile the accepted answer. Show which data and steps were reused or recomputed and the same accepted result and freshness state through toolkit and platform.
5. Record local acceptance and clean up the bounded demonstration. No new model calls, permanent schedule, hosted deployment, commit, or push is authorized. Production scale and sustained freshness targets remain later roadmap work; do not claim them from this local demonstration.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Hudson approved deletion semantics on 2026-10-16: remove deleted source records from future totals, retaining original values and deletion history. Additions and corrections likewise preserve immutable earlier source responses. S-24 follows accepted S-20 and S-21; it is not active yet.

S-21 accepted; S-24 is now the sole active story. Approved deletion policy: omit deleted rows from current totals, retain originals and deletion history. Implement against existing source collection, saved workflows, durable jobs and trigger paths. Existing collection reads all row values; use primary-key fingerprints within one source snapshot to fetch changed rows and reconstruct complete input. No new provider spending or permanent schedules.

Current-source collection and durable saved-workflow continuation are implemented. PostgreSQL fingerprints identify changed values; a temporary disk index reconstructs complete inputs. Originals and insertion/correction/deletion history are retained with permission-checked toolkit/API history. Manual application refresh, CLI refresh, event and due-schedule admission share the progression. Added status counts and full-reread disclosure. Existing source checks, update guards, 21 web checks, build and dead-code check passed; Graphify refreshed. Full-retail local acceptance is running as S24Live-20261016C. A stopped before work on the browser selector; it now has an explicit accessible name. B exposed the test server random port conflicting with the existing browser write-origin policy; C uses the permitted loopback port 2028 without changing that policy. All acceptance boxes remain open. No model spending, deployment, commit or push.

Accepted locally on 2026-10-16. Evidence: /Users/hudson/Library/Application Support/BackIntel/Validation/S24Live-20261016C (summary.json, incremental-cases.json, retained runtime-result.dump, browser logs and screenshots). The actual application button collected all 541,909 PostgreSQL rows after a value-preserving text-storage change and disclosed the full reread. The initial total remained exactly GBP 9,747,747.934. Real insertion, correction and deletion then fetched only 2 changed record values, scanned all 541,909 primary-key fingerprints, retained 541,907 unchanged records, and reported 3 affected / 0 excluded / 0 failed / 0 pending records. Current totals exclude the deletion; unchanged originals and the deletion/correction history were read back, including through the authenticated history API. The accepted total GBP 9,747,767.444 and every product/country group reconcile to an independent full SQL calculation. An interruption after retaining a real source page resumed the same request; duplicate requests and event identities reused accepted work without duplicate runs. Revoking source SELECT caused a visible failed update while preserving the accepted answer and source time. Toolkit and authenticated application accepted state matched; desktop and mobile update panels were inspected. Real event and due-schedule admission used the new current-source progression and fetched zero unchanged record values. The native timer itself is covered by the accepted S-20 demonstration; S-24 directly exercised its due handler and removed its test trigger. Final request-table comparison proves zero new provider requests or charges. Cleanup confirmed server stopped and disposable databases removed. Existing source and update checks, 21 web checks, production build, dead-code check and refreshed Graphify relationships passed. First two attempts stopped before work on the browser selector and the existing write-origin policy; both setups were corrected without weakening application policy. Limitations: all keys/fingerprints are still scanned and preparation/validation/analysis recompute the complete dataset; no hosted deployment, sustained production freshness or throughput claim. All prior uncommitted work is preserved; no commit, push, predictor promotion or permanent schedule.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Saved answers can now refresh from the permitted PostgreSQL source through the toolkit, application, events and due schedules. Additions and corrections update totals; deletions leave current totals while originals and history remain available. Interrupted or failed collection preserves the last accepted answer. The complete historical retail demonstration reconciled every total and group, including after real source changes. Local acceptance only; deployment and sustained production capacity remain separate.
<!-- SECTION:FINAL_SUMMARY:END -->
