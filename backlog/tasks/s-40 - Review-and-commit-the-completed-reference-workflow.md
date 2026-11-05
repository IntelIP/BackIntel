---
id: S-40
title: Review and commit the completed reference workflow
status: Done
assignee:
  - '@codex'
created_date: '2026-10-16 02:03'
updated_date: '2026-10-16 16:08'
labels:
  - development-workflow
  - git-hygiene
  - post-reference
dependencies:
  - S-38
references:
  - docs/retail-reference-workflow.md
  - docs/roadmap/agile-backlog.md
priority: high
ordinal: 4035
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## User story

As a BackIntel maintainer, I want the completed PostgreSQL reference workflow reviewed and preserved in an approved commit, so the next development stage starts from an identifiable, recoverable version.

## Context and scope

S-38 and S-39 delivered the full local retail workflow. The 15-story implementation and its reports remain uncommitted after the earlier planning commit dfdf3d7 on codex/backintel-roadmap-sprint-4. Treat that as the starting context and refresh the relevant local Git facts when this story is selected. S-37 covered the earlier planning preservation and cleanup; do not reopen it or repeat its cleanup without a new reason.

Review the current implementation, tests, documentation, and Backlog changes together; distinguish unrelated work and exclude raw datasets, database archives, credentials, and local validation artifacts from Git. Reuse existing verification where the selected source has not changed and run the affected checks where it has. Prepare a concrete commit scope and message before seeking any still-required approval.

## Boundaries

Story creation authorizes tracking only. Commit requires explicit approval of the concrete work unless that exact action has already been authorized. This story does not authorize a push, pull-request publication, merge, deployment, branch deletion, or worktree cleanup. Such actions need their own selected scope. Preserve all existing working changes and history.

## Prerequisite

S-38 and its completed reference-workflow evidence. This is delivery housekeeping; existing product-story dependency relationships are unchanged.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The execution-time handoff identifies the candidate branch and revision, intended changed files, existing sprint history relevant to review, and unrelated or excluded local work. The proposed commit includes the intended implementation and documentation without raw datasets, database archives, secrets, or accidental unrelated changes.
- [x] #2 The review records the observed product result, material limitations, and relevant verification for the actual candidate. Unchanged evidence is reused where applicable; affected checks are rerun after material edits, and unresolved failures remain explicit.
- [x] #3 The concrete commit scope and message receive any required explicit approval, then the intended work is committed and the local commit is verified. Missing approval or a failed commit prevents this acceptance criterion from being checked.
- [x] #4 The task records the retained commit, scope, exclusions, approval, and remaining review or publication decisions. It makes no claim of push, merge, release, deployment, or independent-user acceptance.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Inventory the current candidate on codex/backintel-roadmap-sprint-4, preserving prior sprint history and all working changes.
2. Review the integrated reference, method-development, and continuous-update changes; reuse recorded live acceptance and run only necessary current-candidate checks.
3. Prepare the exact intended files, exclusions, material limits, and commit message; obtain explicit approval before the commit.
4. Verify the approved local commit and record its identity and scope, then continue the separately selected S-33 story.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Selected by the active goal 'Execute the tasking above' on 2026-10-16. Scope includes the completed reference workflow, forecast-method study, and S-20/S-21/S-24 continuous updates accumulated since dfdf3d7. No commit or new provider call is approved yet. Work remains in the current task-owned checkout so its uncommitted implementation is preserved.

S-40 review, 2026-10-16: candidate branch codex/backintel-roadmap-sprint-4 at dfdf3d7; the six earlier sprint commits remain retained. The intended scope is all 90 changed/untracked source, test, scenario, migration, guidance, and Backlog files inventoried in /Users/hudson/Library/Application Support/BackIntel/Validation/S40Review-20261016/candidate.json. No unrelated working changes were identified. Raw source data, database archives, runtime secrets, build output, and local validation evidence remain excluded from the commit. Two credential-pattern matches are a dynamically generated disposable test password and a deliberate invalid-DSN test, not retained credentials.

Reviewed the objective-to-workflow integrations, source permissions and migrations, immutable workflow/recovery behavior, current scenario definitions, and retained acceptance reports. Reuse S39Reference-20261015, the S-32 reference report, S20Live-20261016Attempt9, S21Live-20261016G, and S24Live-20261016C. Only task metadata is newer than the latest live acceptance; no implementation file changed afterward. Current-candidate checks passed: 21 web tests, production build, Python dead-code check, and git diff --check. Observed local result: full 541,909-record processing, checked analysis and forecast candidate evaluation, scheduled/event invocation, safe repair limits, and incremental insert/correction/deletion reconciliation. Material limits: historical local PostgreSQL data; metadata scans and complete downstream preparation/analysis remain; generated forecasting candidates did not beat the baseline; no live Databricks, coordinated specialist agents, deployment, independent-user acceptance, or measured business savings are claimed.

Proposed commit message: Add connected-source analysis and continuous workflow updates. Acceptance 3 and 4 remain pending explicit approval, a successful local commit, and commit readback. No push or publication is included.

The staged check additionally covered newly added files and found four whitespace-only lines in scripts/validation/workflow_update_cases.py. Removed their trailing spaces without changing executable content; repeated the staged diff check. This formatting correction is the only source-file edit made for S-40.

User approved the exact 90-file local commit in this turn. Commit 106b7ebd4dd58388ef94467bb7f07322e567c680 preserves the reviewed implementation, tests, configuration, documentation, and task records. Verified every staged blob against the approval inventory before committing and verified committed tree 40a69ba7e5dc20ed78c6ee2c3980821c2dbd9561 afterward. No push, publication, merge, deployment, branch deletion, or cleanup was performed. This completion note follows the preserved commit and will remain a normal subsequent tracking change.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Preserved the completed connected-source workflow, forecasting study, and continuous updates in approved local commit 106b7eb. The 90 committed files exactly match the reviewed candidate. Current build, 21 web tests, dead-code and staged patch checks passed; existing live acceptance was reused. S-33 coordination is the next selected product story.
<!-- SECTION:FINAL_SUMMARY:END -->
