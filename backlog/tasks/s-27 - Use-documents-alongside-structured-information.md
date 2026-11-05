---
id: S-27
title: Use documents alongside structured information
status: Done
assignee:
  - '@codex'
created_date: '2026-10-14 22:59'
updated_date: '2026-10-18 19:04'
labels:
  - toolkit
  - platform
  - shared-core
milestone: m-5
dependencies:
  - S-17
  - S-18
documentation:
  - docs/ROADMAP.md
  - docs/roadmap/README.md
  - docs/roadmap/agile-backlog.md#shared-delivery-contract
priority: medium
type: task
ordinal: 20
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Original roadmap story: S27. Original priority: P1. Work type: implementation.

## Business outcome

As a business user, I need relevant document information included, so that the answer can use evidence that is not already in tables.

## Scope

Select supported document types and one task; retain originals and cited passages; connect extracted information to the checked analysis definitions.

## Owned surface

Selected document ingestion and evidence integration. Supported formats remain to be chosen.

## Prerequisites

S-17, S-18 and selected document requirements.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Complete the selected task with traceable passages and correctly linked facts. Missing text, uncertain interpretation, and hostile document instructions receive explicit handling without altering authority.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Use the already selected retail question and the official UCI Online Retail field guide as the first document case. Support bounded UTF-8 plain text and HTML, retaining original bytes, source URL, hashes, and exact quoted passages. Reuse private objective access and versioning; attached document changes invalidate old workflow definitions without rewriting accepted history. Include relevant passages in field interpretation, validate field-to-passage references, and carry accepted quotations into saved workflows and final answers. Expose attachment and inspection through the application/API and shared Python functions. Verify empty/unsupported text, uncertain meanings, hostile instructions, cross-user access, document changes, and calculation parity against the retained retail reference. No new paid inference is authorized; prepare any necessary live request for a concrete, separately bounded decision after local checks.

2026-10-18 approval: execute at most two live document interpretation calls within US$0.25, then reuse the retained calculation method. The disposable restored principal must have the same approved allowance; the native per-run budget and two-request guard remain in force.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Selected independently while the S-34 integration choice is pending; S-17 and S-18 are complete. Existing retail question and dataset scope are unchanged. Public original retrieved from https://archive.ics.uci.edu/dataset/352/online+retail and retained at localdevelopmentpilot/work/S27Documents/online-retail.html. SHA-256 8d95fd49a01d6b8cee892c8f1cb84a88620bdd05f0591e325b2e088560fafb3c; 174302 bytes. It explicitly describes cancellation invoice codes and unit prices in sterling. Stop condition: traceable passages support the selected checked answer, failures remain explicit, and document content cannot change permissions or execution authority.

Document ingestion, immutable originals, goal-version attachment checks, field citation validation, saved-workflow checks, and UI controls are implemented. Text/HTML extraction and citation tests pass; UI checks now pass (28 tests) and web build passes. Document database/native retail acceptance is running in Validation/S27Documents-20261017A using the retained UCI original and simulated provider replies; no new paid inference is authorized. Pending: finish acceptance, inspect browser outputs, and record exact limits. Existing roadmap goal remains active; S-34 alternative-path question is still pending.

Local document trial passed. All 541,909 retained retail rows matched the full reference calculation (totals, every group, currency, dates, coverage). Exact UCI quotations support InvoiceNo cancellations and UnitPrice sterling. Both confirmation and version checks block the prior workflow after document changes; original bytes remain accessible only to permitted users. 179 database/application tests passed (S27Documents-20261017B/document-checks.log), 28 web tests and build passed, dead-code and patch checks passed. Execution and browser evidence are in S27Documents-20261017C; final successful summary and cleanup are in S27Documents-20261017D. The continuation reused completed interpretation/calculation/browser artifacts. No new provider calls or charges. Interpretation was simulated and the method was retained; fresh autonomous document interpretation is not yet verified. S-27 remains In Progress with its acceptance criterion open pending the async request for up to two S-27 OpenRouter interpretation calls, US$0.25 total. Prepared exact request: Validation/S27Documents-20261017C/interpretation-request.json. S-34 scope choice is also still pending. No commit or push is authorized.

Continued safe preparation while the existing paid-call question remains unanswered. Added an explicit --documents-live path that resumes the reviewed pre-calculation archive, reuses the retained aggregate profile, allows at most two interpretation requests within the same native US$0.25 run budget, and stops for unresolved charges. It reuses the previously generated calculation method and records that origin; only document interpretation may contact the provider. The model-output schema now requires citation fields while old saved records remain readable. Data-specialist citation guidance is supplied as system policy, separate from document data. Seventeen focused schema/compatibility, call-limit, objective, and coordination tests passed; CLI help, dead-code, patch checks, and Graphify refresh passed. The exact updated request is localdevelopmentpilot/work/S27Documents/live-interpretation-request.json (22,329 bytes), and the unexecuted command is recorded in docs/saved-workflows.md. No provider or credential retrieval was performed. Previous goal turn made implementation progress; this turn completed the execution preparation. Remaining S-27 work requires the outstanding allowance decision; S-34 still requires its outstanding scope decision.

The existing S-27 allowance question remains unanswered after three consecutive goal turns. Implementation, local acceptance, the capped live command, and focused schema/guard checks are complete; no live process remains. Current Backlog review found no independent ready story: S-34 awaits the requested local-alternative decision, S-36 depends on S-34 and agreed targets, S-35 depends on S-34/S-36, and S-31 follows S-35. S-26 still needs the permitted Databricks environment; toolkit qualification still depends on the unavailable S-02 candidate; optional S-28 has not been selected. Further goal progress requires one of the outstanding user decisions. The full goal remains incomplete, and no new paid call, commit, or push was performed.

2026-10-18: Hudson approved all outstanding decisions. S-27 may make up to two OpenRouter document interpretation requests, including one revision, with US$0.25 cumulative spend. Execute the prepared live command from the retained pre-calculation archive, preserve request/charge records, and reuse the retained calculation method. This resolves the allowance blocker; no additional spending, commit, push, or deployment is authorized.

2026-10-18: Live document acceptance passed at Validation/S27LiveDocuments-20261018B. One measured OpenRouter request cost US$0.04056129; all eight source fields have exact quotations. All 541909 rows, totals, product/country groups, currency, dates, and coverage match the reference. Original download, desktop/narrow browser, workflow save, and attachment-change guards passed. Existing calculation method reused without a paid method call. Initial zero-budget attempt made zero calls; corrected disposable principal allowance preserves the US$0.25 per-run cap. Seven focused document tests passed (database class skipped; earlier 179 database/application tests retained), dead-code/patch checks and Graphify passed. No commit or push.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Documents now support a checked answer through immutable originals and exact field citations. The live UCI interpretation and full retail calculation passed in S27LiveDocuments-20261018B, with one request costing US$0.04056129. UTF-8 text/HTML only; the retained calculation method was reused.
<!-- SECTION:FINAL_SUMMARY:END -->
