---
id: S-14
title: Understand fields and table relationships
status: Done
assignee:
  - '@codex'
created_date: '2026-10-14 22:59'
updated_date: '2026-10-15 02:57'
labels:
  - toolkit
  - platform
  - shared-core
  - goal-reference-workflow
milestone: m-2
dependencies:
  - S-13
references:
  - >-
    backlog/tasks/s-38 -
    Deliver-one-checked-Databricks-answer-through-the-toolkit-and-platform.md
documentation:
  - docs/ROADMAP.md
  - docs/roadmap/README.md
  - docs/roadmap/agile-backlog.md#shared-delivery-contract
priority: high
type: task
ordinal: 8
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Original roadmap story: S14. Original priority: P0. Work type: implementation.

## Business outcome

As an analyst, I need BackIntel to interpret unfamiliar fields, units, identities, and relationships, so that preparation reflects the business meaning.

## Scope

Inspect types, missingness, units, dates, keys, and candidate relationships; propose meanings and mappings; retain unresolved ambiguity.

## Owned surface

Source profiling and semantic preparation definitions for the selected task.

## Prerequisites

S-13.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Correctly interpret a selected unfamiliar schema with independently known meanings. Ambiguous dates, units, identities, or joins remain explicit rather than being silently resolved. No dataset-specific importer is required from the user.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Profile the complete retained source through its existing permission boundary. Describe field types, missingness, numeric/date candidates, identity evidence and possible relationships without altering originals. 2. Use the actual saved objective and aggregate profiles to request a structured agent interpretation; constrain mappings to discovered fields and preserve ambiguity, especially dates, units and joins. No raw source records or identifier values enter the model prompt. Reuse existing model accounting and durable replay. 3. Show the interpretation and its limitations through the shared runtime and platform. Test profiles, unknown meanings, invalid mappings, denied reads and replay with labeled simulated model responses. 4. Prepare the exact real-data metadata payload, then obtain explicit additional paid-call authorization before live semantic interpretation because both earlier approved calls are exhausted. Compare the accepted meaning against the independent source dictionary. Stop at S-14 acceptance; preparation execution is S-15.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Selected after S-13 and S-23 completion. Only S-14 is active. Full-source collection is verified; interpretation is not yet implemented. Existing two-call spending authorization is exhausted. Profiling and implementation checks can proceed without provider calls.

Live S-14 interpretation passed on all 541,909 collected records and nine fields. One additional OpenRouter request cost US$0.02111769; one of the newly authorized two calls remains unused. Only the saved objective, field names and aggregate profiles were sent. Independent UCI meaning comparison passed while customer-country details, business identities, joins and timezone remain explicitly unresolved. Evidence: /Users/hudson/Library/Application Support/BackIntel/Validation/S14InterpretationRun-20261014/interpretation-evidence.json and independent-meaning-check.json; database dump retained there. Corrected interpretation dispatch to honor its current source grant without requiring a registered-dataset snapshot, and canonicalized request ordering to prevent duplicate paid requests after restore. Focused tests and the complete source-access suite passed; existing platform interaction/build checks remain valid; dead-code, diff and graph refresh passed. These are uncommitted local results, not publication validation.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
BackIntel profiles complete collected data and proposes field meanings through the toolkit/runtime and platform, preserving uncertain dates, identities, units and relationships. Real metadata-only inference, independent meaning comparison, source-access checks and replay tests passed. Preparation and business analysis remain later stories.
<!-- SECTION:FINAL_SUMMARY:END -->
