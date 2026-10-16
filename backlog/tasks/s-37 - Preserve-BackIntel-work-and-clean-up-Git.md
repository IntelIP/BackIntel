---
id: S-37
title: Preserve BackIntel work and clean up Git
status: Done
assignee:
  - '@codex'
created_date: '2026-10-15 00:31'
updated_date: '2026-10-15 01:03'
labels:
  - development-workflow
  - git-hygiene
dependencies: []
references:
  - AGENTS.md
  - docs/roadmap/agile-backlog.md
  - 'https://github.com/IntelIP/BackIntel/pull/1'
  - 'https://github.com/IntelIP/BackIntel/pull/2'
priority: high
type: chore
ordinal: 1035
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## User story

As the BackIntel product owner, I want completed work preserved and redundant Git branches and worktrees cleaned up, so the next toolkit or platform task starts from a clear, recoverable baseline.

## Scope

Cover the current development branch, its intended planning and Backlog.md changes, its full difference from main, and the disposition of existing local branches, worktrees, and pull requests. Repository housekeeping is separate from the 36 product-roadmap stories. Preserve unrelated work; this story does not implement a product feature, repeat the full application acceptance campaign, or require every historical branch to be removed.

## Starting context — October 14 inspection, before this story was created

The checkout is /Users/hudson/Documents/GitHub/BackIntel, on codex/backintel-roadmap-sprint-4 at 3cd9991. It was six commits ahead of GitHub main, with no remote counterpart or upstream. Those commits include Sprint 1 planning and Sprint 2–4 installation, support implementation, and tests; a review from this branch is not documentation-only.

The working tree had seven modified planning/guidance files and 48 new files: Backlog configuration, nine milestones, 36 tasks, docs/ROADMAP.md, and docs/SYSTEM_DESIGN.md. There were 15 local branches, four worktrees, no stashes, and no conflicts. The three extra worktrees had no ordinary Git changes; ignored files and local assets were not qualified for removal.

PR #1, Python dead-code checks, was open. PR #2, the consolidated demo, was merged, and its recorded head matched codex/backintel-consolidated. Potential retirement candidates were codex/backintel-roadmap-sprint-2, recovery/design-preservation, and the merged consolidated branch. These are leads to recheck, not deletion instructions. Other benchmark and recovery histories were not proven redundant.

## Authority and completion boundary

Recheck current state when execution starts. Commit and push require explicit confirmation under /Users/hudson/AGENTS.md; prepare the exact changes and destination before requesting that confirmation. Story creation is not approval to run those commands. Respect any authorization already supplied when the story is later executed.

Do not merge, close unrelated pull requests, force-push, discard work, or remove branches/worktrees outside the authorized cleanup scope. A clean status or a merged/squashed PR alone does not prove that unique commit history or ignored local assets can be discarded. Retain an item with a concrete reason when preservation or active use makes removal inappropriate.

If a required preservation action lacks approval or fails, save progress and report the specific remaining requirement; do not mark the story Done. Use only checks needed for the preservation and cleanup claims. Any implementation testing follows the actual branch changes and repository requirements, not a new blanket audit.

## Goal prompt

Complete this BackIntel Git preservation and cleanup story in /Users/hudson/Documents/GitHub/BackIntel. Preserve the intended current-branch work in reviewed commits and a verified remote branch, establish the full review scope against main, and retire only redundant branches or worktrees within the authorized scope. Follow AGENTS.md and native Backlog.md execution/finalization guidance. Prepare concrete changes before requesting required commit or push confirmation. Preserve unrelated history and active pull requests. Stop when the acceptance criteria pass, and report any required approval or failed check without claiming completion.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 An execution-time inventory identifies the current branch and revision, live remote comparison, staged/unstaged/untracked work, stashes, branch/worktree ownership or active use, and relevant PR states. It distinguishes the starting snapshot above from current facts.
- [x] #2 All intended planning, guidance, and Backlog changes are preserved in explicitly approved commits, distinguishable from the existing sprint commits. No existing work or history is discarded, and excluded local data, secrets, or ignored assets are not inadvertently committed.
- [x] #3 The approved current-work branch is published with the intended upstream, and its remote tip is verified against the local commit containing the preserved work. An unapproved or failed push does not satisfy this criterion.
- [x] #4 A review handoff describes the entire branch difference from current main, including earlier sprint code and tests plus new planning changes. PR #1 has an explicit retain/review disposition; changing or closing it is not required for this story.
- [x] #5 Each cleanup candidate is either retired within the authorized scope after proving its work/history is preserved, or retained with a specific reason. Worktree removal accounts for ignored assets and active use. Unrelated benchmark and recovery work remains recoverable.
- [x] #6 Final Git checks show no unresolved conflicts, unintended deletions, or unexplained working-tree changes. Any deliberately excluded files or final Backlog bookkeeping changes are named; no extra commit loop is required solely to record verification.
- [x] #7 The task records the retained local and remote commits, review handoff, branch/worktree changes, retained-item reasons, and any remaining user action. Required preservation failures or missing approvals remain explicit and prevent Done.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Refresh the current-branch, remote, pull-request, and worktree inventory; identify ignored assets and active-use reasons before choosing cleanup candidates.
2. Review the intended planning/backlog paths, record the full branch review handoff and retention decisions, and stage one focused preservation commit.
3. Obtain the required explicit commit/push confirmations, preserve the scoped changes, publish the current branch with upstream tracking, and verify the remote tip.
4. Retire only proved-redundant local branch references after preservation; retain original squash-merge history, open-PR work, and other unqualified histories/worktrees with reasons.
5. Run direct Git and task checks, record exact retained commits and any final bookkeeping changes, and finalize only when every acceptance criterion is satisfied.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## Execution inventory — October 14, 2026

Selected S-37 is the only In Progress story and is assigned to @codex. Current checkout: /Users/hudson/Documents/GitHub/BackIntel. Current branch: codex/backintel-roadmap-sprint-4; HEAD 3cd99917fbfec1521255b40340ef1a72e24883af. Live origin main is c6de6ae44a57917bb1e16e60eb63f283ad260227, matching the local remote-tracking base. The branch is six commits ahead and zero behind that base, has no upstream, and does not exist among live remote heads. GitHub's connected search found no PR for the current branch.

The start-of-execution working tree has seven modified tracked files and 49 untracked files (the earlier snapshot had 48 before S-37 was created). These are planning/guidance documents, Backlog configuration, nine milestones, and 37 task records. Nothing was staged initially. No stashes, conflicts, locked worktrees, or prunable worktree records were reported.

Four worktrees remain registered. The canonical checkout is assigned to this goal. The quality checkout belongs to open draft PR #1; the decision and local-resume checkouts retain their named historical branches. Their current human/chat owners were not inferred. All three extra worktrees have no ordinary tracked/untracked changes, but ignored files exist. Quality has graph/cache files; decision has validation artifacts and local release records; local-resume has .env and local dependencies. No checkout or ignored asset is scheduled for removal.

Connected GitHub metadata confirms PR #1 is an open draft and PR #2 is merged. Retain PR #1 for separate review. No new PR, merge, closure, or remote branch deletion is needed for this preservation story.

## Full branch review handoff

Base: published main c6de6ae44a57917bb1e16e60eb63f283ad260227. Existing head before preservation: 3cd99917fbfec1521255b40340ef1a72e24883af. Six existing commits cover Sprint 1 planning, Sprint 2 installation/demo checks, Sprint 3 support calculation and checks, and Sprint 4's final script workflow. Their net comparison changes 29 files, including scripts/sprint3_support_analysis.py, scripts/support_analysis.py, tests/test_sprint3_support_analysis.py, and dated demonstration/review evidence.

The proposed new commit adds the autonomous product roadmap and system diagrams, separates toolkit/platform/shared delivery, migrates 36 stories into native Backlog files, and includes this maintenance story and current execution record. It updates guidance and preserves older plans as historical context. It changes no application code. A future review of the complete branch must include the earlier implementation and evidence; it must not be described as documentation-only. Historical application checks retain their original scope; this cleanup will claim only fresh Git/document/task checks.

## Branch and worktree disposition

- codex/backintel-consolidated (59f582e): Retain local and remote refs: PR #2 is merged, but this preserves the original 81-commit pre-squash history that is not an ancestor of the current branch.
- codex/backintel-local-resume (53ffa85): Retain branch and worktree: local recovery history is not proved redundant; ignored .env and working dependencies remain in that checkout.
- codex/backintel-roadmap-sprint-2 (592ef45): Retire this local branch name only after the current branch is verified remotely; its tip 592ef45 is an ancestor of the current branch.
- codex/backintel-roadmap-sprint-4 (3cd9991): Retain current branch and checkout; publish the existing sprint history plus the planning/backlog preservation commit.
- codex/benchmark-campaign (9a4570b): Retain unpublished benchmark history; it is not an ancestor of the current branch and is outside this cleanup's implementation scope.
- codex/benchmark-scoring (3050fe9): Retain unpublished benchmark history; it is not an ancestor of the current branch and is outside this cleanup's implementation scope.
- codex/benchmark-scoring-repair (e1aca5f): Retain unpublished benchmark history; it is not an ancestor of the current branch and is outside this cleanup's implementation scope.
- codex/benchmark-workflow-repair (ebd3126): Retain unpublished benchmark history; it is not an ancestor of the current branch and is outside this cleanup's implementation scope.
- codex/benchmark-workflows (7e50d0b): Retain unpublished benchmark history; it is not an ancestor of the current branch and is outside this cleanup's implementation scope.
- codex/code-quality-backintel-20260928 (21c5227): Retain branch and worktree for open draft PR #1. Keep that PR open for its separate review; do not change its scope here.
- codex/decision-workspace (499ae9e): Retain branch and worktree: history is not proved redundant and ignored validation/release artifacts are present.
- codex/poc-foundation-20260929 (c4565a0): Retain the unpublished historical foundation ref; it is not an ancestor of the current branch and has not been qualified for retirement.
- codex/recovery-original-20261006 (23dd937): Retain the original-recovery ref; it is not an ancestor of the current branch and protects historical source.
- main (c6de6ae): Retain the default branch at the verified published base.
- recovery/design-preservation (e060018): Retire this local branch name after preservation: its tip e060018 is already an ancestor of published main and the current branch.

No branch or worktree has been deleted yet. The two retirement candidates have no associated worktree; their commits must remain reachable from retained, published refs before deletion.

## Prepared preservation action

Proposed commit message: Align BackIntel roadmap and add Backlog task tracking.
Proposed destination: origin/codex/backintel-roadmap-sprint-4 at https://github.com/IntelIP/BackIntel.git, with upstream tracking and no force push.
Stage only the seven existing modified guidance/planning paths, docs/ROADMAP.md, docs/SYSTEM_DESIGN.md, and the explicit Backlog configuration/milestone/task files. Exclude .env, datasets, model/artifact directories, dependency/build/cache directories, and unrelated worktrees. Commit and push are still pending the required explicit user confirmation.

## Pre-commit checks and next action

Prepared 56 explicit files (54 Markdown, one YAML, one text file), totaling approximately 179 KB before this note. The proposed full branch comparison against published main covers 82 files; the only application paths in that full comparison are the two support-analysis scripts and their test from earlier sprint commits. This new preservation commit contains no application code changes.

Staged content matched the working copies. Local Markdown links and fence balance passed. Git staged whitespace checks passed. A scoped credential-pattern check found no candidate private keys, provider tokens, GitHub tokens, or AWS access keys in staged text; ignored credential/data/model/build paths were excluded. Backlog doctor reported no duplicate IDs, self-dependencies, or dependency cycles. No unstaged paths or conflicts were present at that check. Application tests were not rerun because this goal changed planning/task records only and does not claim fresh application qualification.

Required next action: request explicit confirmation to commit the prepared files with message "Align BackIntel roadmap and add Backlog task tracking" and push codex/backintel-roadmap-sprint-4 to origin with upstream tracking. After verified remote preservation, retire the two redundant local branch names, retain all other recorded histories/worktrees, and perform final direct checks. No commit, push, merge, PR change, branch deletion, or worktree removal has occurred in this goal yet.

## Completed preservation and cleanup

The user explicitly approved the prepared commit and push. Commit dfdf3d7abab483d2a3ea8f3f4549331ae2b8db1f ("Align BackIntel roadmap and add Backlog task tracking") preserves the 56 reviewed planning, guidance, and Backlog files. The six earlier sprint commits remain intact, making seven commits ahead of main c6de6ae44a57917bb1e16e60eb63f283ad260227.

Published codex/backintel-roadmap-sprint-4 to origin at https://github.com/IntelIP/BackIntel.git without force. The live remote tip, local HEAD, and configured upstream origin/codex/backintel-roadmap-sprint-4 all matched dfdf3d7abab483d2a3ea8f3f4549331ae2b8db1f.

After confirming both candidate tips were ancestors of the published branch, safely removed only the local branch names codex/backintel-roadmap-sprint-2 (592ef45c96476c4aee4535f76d90b71f11d567bd) and recovery/design-preservation (e060018db72ef6376df5ac05f0bebc8ba0b81c56). Their commits remain reachable from the published branch. Thirteen local branches and all four worktrees remain. Every other retain/review decision above still applies, including the consolidated pre-squash history, PR #1, benchmark/recovery histories, and ignored worktree assets.

The earlier full-branch review handoff remains applicable: 82 changed files against main, including the two support-analysis scripts and test from the six earlier sprint commits. This preservation commit itself changes no application code. Application checks were not rerun, and preservation does not claim application qualification, merge readiness, or deployment.

Final checks before this bookkeeping update found a clean working tree, no conflicts, no stashes, no whitespace errors, and no file deletions in the branch comparison. The final status, acceptance checks, and completion notes in backlog/tasks/s-37 - Preserve-BackIntel-work-and-clean-up-Git.md are deliberately left as the sole local bookkeeping change, as acceptance criterion 6 permits. No remote branches or worktrees were removed, and no PR was created, closed, or merged.

No required preservation action remains. A later product task or full-branch review can be selected separately; PR #1 remains open for its separate review.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Preserved the approved 56-file planning and Backlog change in dfdf3d7abab483d2a3ea8f3f4549331ae2b8db1f and published it with the six existing sprint commits to origin/codex/backintel-roadmap-sprint-4. Verified local, upstream, and live remote tips match. Retired two redundant local branch names after ancestry checks; retained 13 branches, four worktrees, active PR work, and historical/ignored assets with documented reasons. The full-branch review handoff is recorded. Only this task's final bookkeeping remains uncommitted. No required user action remains for S-37.
<!-- SECTION:FINAL_SUMMARY:END -->
