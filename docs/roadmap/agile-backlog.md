# BackIntel Backlog.md task index

Updated October 14, 2026. All 36 roadmap stories now live in [Backlog.md task files](../../backlog/tasks). Those files own descriptions, acceptance criteria, dependencies, and status. This page is an index and shared delivery contract; it does not keep a second live task list.

The original S01–S36 labels map to native S-01–S-36 IDs. Historical sprint reports keep their original labels. P0/P1/P2 priorities map to high/medium/low; original priority and work type remain recorded in each task's migration context.

Repository-maintenance stories are tracked alongside these 36 product stories and listed separately below.

## Using the backlog

- Read [AGENTS.md](../../AGENTS.md#use-backlogmd) for the installed CLI path and workflow. Use the CLI for task changes; it preserves IDs, filenames, relationships, and metadata.
- The board has **To Do**, **In Progress**, **Review**, and **Done**. `needs-refinement` means the story still needs a bounded, selected implementation scope. `blocked` records an unresolved external prerequisite. `optional` requires a specific product need before selection.
- Hudson selects and starts one development task at a time. A dependency-ready task is not automatically approved or ready for implementation. Check its labels, business inputs, access, expected result, and applicable limits.
- The [roadmap](../ROADMAP.md) owns product priorities; the [detailed milestones](README.md) own product outcomes and milestone acceptance. Keep progress and task status in Backlog.md.
- Completed app/script work remains in the [Sprint 1](sprint-1-review.md), [Sprint 2](sprint-2-review.md), [Sprint 3](sprint-3-review.md), and [Sprint 4](sprint-4-review.md) reviews. This migration does not change their acceptance or start product work.

## Task index

### Toolkit and platform views

Use the native task labels to select the work:

- `toolkit`: toolkit-only work plus shared capabilities it uses.
- `platform`: platform-only work plus the same shared capabilities.
- `shared-core`: the reusable work appearing in both views. Complete it once; do not create duplicate toolkit and platform stories for the same behavior.

The [delivery split and execution sequence](README.md#toolkit-and-platform-delivery) explains the two outcomes, task allocation, and handoffs. Labels preserve existing task status, dependencies, acceptance, and optional/refinement conditions. The detailed task records remain authoritative.


## Established baseline

### Know what works today

[S-01 — task details, acceptance, and status](<../../backlog/tasks/s-01 - Know-what-works-today.md>) (original S01).

## Shared controls — Protect access, spending, and progress

### Use only permitted information and actions

[S-04 — task details, acceptance, and status](<../../backlog/tasks/s-04 - Use-only-permitted-information-and-actions.md>) (original S04).

### Control spending and explain charges

[S-05 — task details, acceptance, and status](<../../backlog/tasks/s-05 - Control-spending-and-explain-charges.md>) (original S05).

### Resume accepted work after interruption

[S-06 — task details, acceptance, and status](<../../backlog/tasks/s-06 - Resume-accepted-work-after-interruption.md>) (original S06).

## Stage 1 — Understand the objective and find permitted data

### Define the business question and operating limits

[S-12 — task details, acceptance, and status](<../../backlog/tasks/s-12 - Define-the-business-question-and-operating-limits.md>) (original S12).

### Configure a scoped connection

[S-22 — task details, acceptance, and status](<../../backlog/tasks/s-22 - Configure-a-scoped-connection.md>) (original S22).

## Stage 2 — Complete one business-system pipeline

### Admit permitted inputs and retain originals

[S-13 — task details, acceptance, and status](<../../backlog/tasks/s-13 - Admit-permitted-inputs-and-retain-originals.md>) (original S13).

### Collect complete and traceable information

[S-23 — task details, acceptance, and status](<../../backlog/tasks/s-23 - Collect-complete-and-traceable-information.md>) (original S23).

### Understand fields and table relationships

[S-14 — task details, acceptance, and status](<../../backlog/tasks/s-14 - Understand-fields-and-table-relationships.md>) (original S14).

### Prepare data inside an isolated workspace

[S-15 — task details, acceptance, and status](<../../backlog/tasks/s-15 - Prepare-data-inside-an-isolated-workspace.md>) (original S15).

### Check that preparation preserves meaning

[S-16 — task details, acceptance, and status](<../../backlog/tasks/s-16 - Check-that-preparation-preserves-meaning.md>) (original S16).

### Complete the workload without manual batching

[S-29 — task details, acceptance, and status](<../../backlog/tasks/s-29 - Complete-the-workload-without-manual-batching.md>) (original S29).

### Answer the question from the prepared data

[S-17 — task details, acceptance, and status](<../../backlog/tasks/s-17 - Answer-the-question-from-the-prepared-data.md>) (original S17).

### Save a reusable, versioned workflow

[S-18 — task details, acceptance, and status](<../../backlog/tasks/s-18 - Save-a-reusable-versioned-workflow.md>) (original S18).

### Invoke the workflow manually or from an application

[S-19 — task details, acceptance, and status](<../../backlog/tasks/s-19 - Invoke-the-workflow-manually-or-from-an-application.md>) (original S19).

### Complete the Databricks reference workflow

[S-26 — task details, acceptance, and status](<../../backlog/tasks/s-26 - Complete-the-Databricks-reference-workflow.md>) (original S26).

## Stage 3 — Develop and compare methods

### Develop and check analysis methods

[S-32 — task details, acceptance, and status](<../../backlog/tasks/s-32 - Develop-and-check-analysis-methods.md>) (original S32).

## Stage 4 — Keep answers current

### Invoke from an event or schedule

[S-20 — task details, acceptance, and status](<../../backlog/tasks/s-20 - Invoke-from-an-event-or-schedule.md>) (original S20).

### Handle changes without losing the last useful answer

[S-21 — task details, acceptance, and status](<../../backlog/tasks/s-21 - Handle-changes-without-losing-the-last-useful-answer.md>) (original S21).

### Collect incremental changes and refresh the result

[S-24 — task details, acceptance, and status](<../../backlog/tasks/s-24 - Collect-incremental-changes-and-refresh-the-result.md>) (original S24).

## Stage 5 — Coordinate systems and agents at scale

### Use documents alongside structured information

[S-27 — task details, acceptance, and status](<../../backlog/tasks/s-27 - Use-documents-alongside-structured-information.md>) (original S27).

### Coordinate specialist agents around one objective

[S-33 — task details, acceptance, and status](<../../backlog/tasks/s-33 - Coordinate-specialist-agents-around-one-objective.md>) (original S33).

### Connect findings across business systems

[S-34 — task details, acceptance, and status](<../../backlog/tasks/s-34 - Connect-findings-across-business-systems.md>) (original S34).

### Support multiple users without crossing boundaries

[S-30 — task details, acceptance, and status](<../../backlog/tasks/s-30 - Support-multiple-users-without-crossing-boundaries.md>) (original S30).

### Meet sustained workload and freshness targets

[S-36 — task details, acceptance, and status](<../../backlog/tasks/s-36 - Meet-sustained-workload-and-freshness-targets.md>) (original S36).

## Stage 6 — Demonstrate independent use and value

### Operate the autonomous workflow independently

[S-35 — task details, acceptance, and status](<../../backlog/tasks/s-35 - Operate-the-autonomous-workflow-independently.md>) (original S35).

### Measure usefulness in an agreed pilot

[S-31 — task details, acceptance, and status](<../../backlog/tasks/s-31 - Measure-usefulness-in-an-agreed-pilot.md>) (original S31).

## Supporting work — Recover and qualify the toolkit alpha

### Recover and reconcile the existing alpha

[S-02 — task details, acceptance, and status](<../../backlog/tasks/s-02 - Recover-and-reconcile-the-existing-alpha.md>) (original S02).

### Install the toolkit from a clean environment

[S-03 — task details, acceptance, and status](<../../backlog/tasks/s-03 - Install-the-toolkit-from-a-clean-environment.md>) (original S03).

### Complete the commerce analysis

[S-07 — task details, acceptance, and status](<../../backlog/tasks/s-07 - Complete-the-commerce-analysis.md>) (original S07).

### Complete the support analysis

[S-08 — task details, acceptance, and status](<../../backlog/tasks/s-08 - Complete-the-support-analysis.md>) (original S08).

### Verify findings and ask a follow-up

[S-09 — task details, acceptance, and status](<../../backlog/tasks/s-09 - Verify-findings-and-ask-a-follow-up.md>) (original S09).

### Reproduce the examples independently

[S-10 — task details, acceptance, and status](<../../backlog/tasks/s-10 - Reproduce-the-examples-independently.md>) (original S10).

### Review and release the qualified alpha

[S-11 — task details, acceptance, and status](<../../backlog/tasks/s-11 - Review-and-release-the-qualified-alpha.md>) (original S11).

## Selectable implementation options

### Use another agent framework

[S-25 — task details, acceptance, and status](<../../backlog/tasks/s-25 - Use-another-agent-framework.md>) (original S25).

### Process information near its source

[S-28 — task details, acceptance, and status](<../../backlog/tasks/s-28 - Process-information-near-its-source.md>) (original S28).

## Development workflow — Preserve work and keep Git manageable

### Preserve BackIntel work and clean up Git

[S-37 — story, acceptance criteria, and goal prompt](<../../backlog/tasks/s-37 - Preserve-BackIntel-work-and-clean-up-Git.md>)

## Shared delivery contract

These defaults apply to every story. Story-specific refinements add only what its outcome and risk require.

**Source and destination:** Parent destination is BackIntel and the product stage mapped above. Acceptance sources are the [canonical roadmap](README.md), the relevant [autonomous workflow concept](../research/autonomous-workflow-concept.txt), and the recovered toolkit contract when available. The separate [five-domain goal](analysis-workspace-testing-goal.md) retains its own acceptance and original authority; its blocked Credit case is not automatically a dependency of a two-example alpha.

**Ownership and readiness:** Owner and final integrator are unassigned. The product owner confirms priorities and consequential scope choices. Assign each story a bounded session scope, precise owned files/interfaces, applicable prerequisites, and an independent expected result before Ready. Unselected enterprise sources, document formats, privacy policies, and capacity targets stay in refinement. No sprint dates or point estimates are invented.

**Dependencies and parallel work:** Native task dependencies identify blocked-by relationships. Use the CLI dependency graph for reverse and transitive relationships; conditional alternatives remain explicit until refinement selects the applicable prerequisite. Create verified native relations when authorized tracker records exist, retaining textual relationships if native readback is unavailable. No parallel implementation across shared interfaces or overlapping files. Name an integration owner before combining separate work.

**Invariants:** Preserve raw inputs and accepted evidence; enforce permissions and spending limits; do not leak credentials; do not duplicate accepted results or uncertain paid operations; keep synthetic, replayed, and actual execution distinct; do not silently substitute datasets, providers, or evaluation criteria; keep unsupported claims and material uncertainty visible.

**Testing and demo:** Use a bounded permitted input with an independent expected result and the stated negative case. Run the smallest appropriate correctness, workflow, access, cost, recovery, or visual check for the changed behavior; mandatory repository checks still apply. Bind material results to the relevant candidate and inputs. Reuse unchanged evidence only where it remains applicable; rerun affected behavior after a material change. The demo record states the actor, starting state, actual result, limitation, relevant time/cost, and cleanup. Fixtures never establish a required live outcome.

**Implementation delivery:** Resolve exact files against the selected available source; candidate recovery is required only for work on the missing alpha. Use a suitable isolated checkout when needed, the `codex/` branch prefix, one bounded story per PR where practical, and the dependency order above. Record candidate, prerequisite branch, shared-file conflicts, integration owner, and authorized publication steps at refinement. Creating a local Backlog task does not authorize product implementation, external tracker writes, live calls, publication, merge, or deployment.

**Done and stop:** Done requires the story's stated result, required direct checks, and meaningful demonstration, including applicable human acceptance. Required missing inputs or authority produce a specific blocked disposition; demonstrated failures require a scoped fix. A missing required check is not a pass. Stop when the stated outcome exists and required checks pass; unrelated improvements become separately accepted follow-up work. If publication is part of the story, retain the actual publication result separately from qualification and source merge.

**Scope boundary:** Autonomous discovery, unfamiliar-data preparation, method development, continuous operation, coordinated agents, cross-system work, and scale are core product scope, delivered in bounded stories. The toolkit exposes reusable capabilities and the platform delivers the managed business workflow; shared work has one implementation and task record. Historical toolkit-alpha qualification retains its separate candidate and recovery boundary. Full five-domain acceptance, production readiness, deployment, and measured customer value retain their own completion conditions. Product autonomy does not authorize an autonomous Codex development scheduler.

## Current planning focus

Refine [S-12](<../../backlog/tasks/s-12 - Define-the-business-question-and-operating-limits.md>) into one Databricks business question and operating contract. The task owns its current state and prerequisites. [S-02](<../../backlog/tasks/s-02 - Recover-and-reconcile-the-existing-alpha.md>) owns toolkit recovery; [S-03](<../../backlog/tasks/s-03 - Install-the-toolkit-from-a-clean-environment.md>) depends on that recovery. Independent work on current source retains its own dependencies.

The [roadmap sources](README.md#source-decisions-and-supporting-plans) retain the earlier decisions and the October 14 scope clarification.
