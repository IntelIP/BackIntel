---
id: S-35
title: Operate the autonomous workflow independently
status: In Progress
assignee:
  - '@codex'
created_date: '2026-10-14 22:59'
updated_date: '2026-10-19 00:45'
labels:
  - platform
  - post-reference
milestone: m-6
dependencies:
  - S-24
  - S-39
  - S-32
  - S-33
  - S-34
  - S-30
  - S-36
references:
  - docs/retail-reference-workflow.md
  - docs/roadmap/agile-backlog.md
documentation:
  - docs/ROADMAP.md
  - docs/roadmap/README.md
  - docs/roadmap/agile-backlog.md#shared-delivery-contract
  - docs/local-platform.md
priority: medium
type: task
ordinal: 25
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Original roadmap story: S35. Original priority: P1. Work type: manual-task and implementation.

## Business outcome

As a new user, I need a reproducible installation and operating instructions, so I can run the declared autonomous workflow without the implementer's private environment.

## Scope

Package the identified runtime, interfaces, workflow definitions, and dependencies; document connections, permissions, limits, results, freshness, recovery, and material escalation. Have an independent user run the declared scope. Select any client/service split through a separate justified design decision.

## Owned surface

Autonomous-product packaging, entry points, operating guidance, and independent reproduction. This does not depend on recovering the separate historical toolkit candidate.

## Prerequisites

S-24, S-39, S-32, S-33, S-34, S-30, S-36.

## Next staged delivery

Demonstrate that another user can operate the selected autonomous platform workflow from the documented distribution candidate, without the implementer's private environment. Shared toolkit calls remain part of the declared workflow; this does not qualify the unavailable historical toolkit alpha or authorize a release.

## Decisions before selection

Select the distribution candidate, clean supported environment, independent operator, required credentials and source setup, and declared workflow. The separate historical toolkit path remains S-02 through S-03 and its existing qualification stories.

These refinements record future work. Hudson selects one implementation story at a time; no implementation, model spending, live scheduling, commit, publication, or deployment is authorized by this planning update.

## Selected independent installation

On 2026-10-18 Hudson selected the local PostgreSQL workflow and will perform the independent operator check. S-39 replaces S-26 for this declared installation; the actual Databricks check remains open under S-26. Package the current source and documented dependencies without private runtime images, database archives, local work paths, or recorded model responses supplying application behavior. Model spending starts disabled. Preparation and clean-install checks do not substitute for Hudson completing the independent installation, answer, refresh, and recovery steps.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The user installs the identified candidate, grants the intended access, supplies the business objective, receives a checked answer, and observes refresh and recovery. Record the human configuration and intervention still required. Private workspace files or hardcoded demonstration responses cannot supply missing behavior. Required review/checks apply to the same candidate; actual publication and deployment are separate authorized outcomes.
- [ ] #2 The independent operator uses only the documented candidate, dependencies, and their permitted credential references to install, start, run, inspect, and recover the declared workflow. Any implementer intervention or undocumented setup is recorded and resolved before independent-operation acceptance.
- [x] #3 Instructions explain expected outputs, remaining human decisions, spending and source limits, failure recovery, and shutdown. Successful local installation does not imply publication, deployment elsewhere, or qualification of an unavailable toolkit candidate.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Identify and reuse the existing runtime entry points, source connection setup, dependency pins and interface. Package an installable local PostgreSQL candidate with explicit configuration and no private image/archive requirement.
2. Provide startup, source permissions, objective/limits, result inspection, refresh/recovery and shutdown instructions. Disable provider spending by default; any live inference must have separate explicit authority.
3. Validate installation from the documented candidate in an isolated local state directory, including startup, authentication and source access. Reuse focused workflow checks for behavior; label fixture responses where used. Run required relevant checks and inspect scoped Graphify relationships.
4. Give Hudson the candidate, exact commands, expected outputs and operator checklist. Keep independent-operation acceptance open until Hudson runs the workflow and reports the outcome; record any intervention. No publication, deployment or commit is included.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Hudson selected local PostgreSQL and will be the independent tester. S-36 has passed and is Done. Existing Dockerfile.analysis assumes a private base image; investigate and replace the installation dependency while preserving the current runtime. No new model spending is authorized.

2026-10-18: Prepared the PostgreSQL installation candidate /Users/hudson/Library/Application Support/BackIntel/Candidates/S35Local-20261018C.zip (SHA-256 bfcb5bef56e355e3bcf2a5c4bad21e825b4e0e852613f3c5545d3a838cfd8d22; 322 manifest-verified files; base commit 106b7ebd4dd58388ef94467bb7f07322e567c680, explicitly an uncommitted working-tree candidate). Added requirements.platform.txt, scripts/local_platform.py and docs/local-platform.md; the testing dependency file now reuses the same platform pins. Setup creates its own PostgreSQL database and read-only retail source from the operator-supplied pinned CSV, with owner-only state/access files. It uses public Python/PostgreSQL images and no private database archive, recorded model replies, existing provider credentials, or model weights. Default startup clears inherited source/provider bindings and sets model spending to zero. Explicit model mode requires an injected key and a finite cumulative allowance at most US$0.50; no such S-35 allowance has been approved or used.

The fresh Python environment installed successfully from the packaged requirements. Actual installer preflight passed interface/authentication, all 541,909 source rows and denied source writes, real source discovery through the installed toolkit, preservation of the saved goal/discovery across API and database restart, one clearly synthetic GBP10 source update, and zero model requests. Both API processes and the owned database were stopped. Evidence: /Users/hudson/Library/Application Support/BackIntel/Validation/S35Install-20261018A/installation-report.json and candidate-check.json. The initial native API check exposed libpq-versus-URL configuration mismatch; the corrected candidate converts and escapes the URL and waits for current database health after restart. A separate validator-only stale-port issue was corrected by reloading the saved connection after restart. Failure logs are retained. Four focused installer tests, web build, dead-code and Graphify update passed; current dependency/caller relationships were inspected.

Hudson remains the independent operator. Acceptance 1 and 2 remain unchecked: the independent installation, complete checked answer, source refresh, interruption recovery and any assistance must be recorded. A fresh model allowance is needed before new planning/interpretation/method requests. The operator guide explains those gates, expected outputs, zero-spend startup, synthetic update, retained state and shutdown. Do not mark S-35 or the overall goal complete from the installer preflight.
<!-- SECTION:NOTES:END -->
