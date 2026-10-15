# BackIntel roadmap

Updated October 14, 2026. This is the product-priority entry point. The [detailed roadmap](roadmap/README.md) owns milestone criteria and decisions. [Backlog.md tasks](../backlog/tasks) own story details, dependencies, and current status; the [task index](roadmap/agile-backlog.md) preserves the original story mapping and shared delivery contract.

## Product outcome

A business owner gives BackIntel a question, the business measures and targets that matter, permitted connections, and operating limits. BackIntel discovers the relevant information, builds the collection and preparation steps, cleans and classifies the data, develops and checks analysis and prediction methods, explains the result, and keeps it current.

The user should not need to write an importer, specify every transformation, choose every analytical tool, split a workload into manual batches, or leave BackIntel to commission each new pipeline. Coordinated agents, communication between permitted business systems, continuous operation, and processing complete workloads at an agreed scale are core product scope.

Automating work usually performed by data engineers and data scientists is the intended outcome. Reduced human effort, better decisions, and replacement of particular tasks must be demonstrated in a real pilot; the current demonstrations do not establish those benefits.

## What exists today

The repository provides known-dataset adapters, a bounded agent that selects approved tools, classification and prediction comparisons, source-linked evidence, permissions, spending controls, durable jobs, and refresh/recovery. A separate script produces a fresh support-queue report from a specified CSV.

These are reusable foundations. They do not yet provide autonomous Databricks discovery, unfamiliar-data pipelines, new analytical methods, coordinated specialist agents, or measured operation at scale. The current text tool processes at most 20 selected messages per invocation. See the [system design](SYSTEM_DESIGN.md#current-foundations-and-gaps).

## Delivery stages

Build one bounded story at a time. Each stage has a useful result; all six belong to the intended product. Shared permission, cost, evidence, and recovery controls apply from the first runnable pipeline.

| Stage | Business result | Observable completion |
| --- | --- | --- |
| 1. Understand the objective and find permitted data | The owner supplies a question and access; BackIntel identifies the data and proposes the work. | One saved objective, source-discovery result, business definitions, operating limits, and a revisable plan. Routine extraction setup is performed by the agent. |
| 2. Complete one business-system pipeline | The owner receives a checked answer from a complete selected workload without writing preparation code. | With Databricks as the reference source, the agent collects, profiles, cleans, classifies where needed, joins, checks, analyzes, and saves a reusable workflow. It reports coverage and resumes an interrupted run. |
| 3. Develop and compare methods | The owner receives an appropriate method and a defensible prediction or analysis. | The agent proposes and implements bounded analytical methods, compares them fairly with a baseline, checks evidence and uncertainty, and retains or rejects each candidate with a reason. |
| 4. Keep answers current | The owner sees changing business measures and progress toward targets without rebuilding the pipeline. | Events or schedules trigger updates; the system handles source changes, checks freshness, repairs routine failures, and escalates material uncertainty while preserving the last useful answer. |
| 5. Coordinate agents and business systems at scale | Several specialist agents complete work across permitted sources and deliver results to authorized destinations. | Shared work and evidence remain consistent; complete workloads and concurrent users meet agreed correctness, freshness, time, resource, and cost targets. Selected systems exchange only permitted information. |
| 6. Demonstrate independent use and value | Another user can operate the system and judge whether it replaces their manual workflow. | A reproducible installation and a real pilot show task completion, remaining human intervention, errors, operating costs, and usefulness against the agreed alternative. |

Detailed acceptance and story mappings are in [milestones and observable completion](roadmap/README.md#milestones-and-observable-completion). Stages do not require all enterprise connectors or unlimited capacity. Source coverage and operating targets must be explicit, and each expansion gets its own bounded task.

## Toolkit and platform work

The toolkit and agent platform are two delivery surfaces over shared capabilities. The toolkit gives developers and other agents reusable, installable capabilities. The platform turns business objectives into coordinated, continuously maintained work. Collection, preparation, analysis, evidence, controls, and recovery should be implemented once where both can use them.

The [execution split and sequence](roadmap/README.md#toolkit-and-platform-delivery) maps the 36 product-roadmap stories to toolkit, platform, or shared-core work. Product tasks use `toolkit`, `platform`, and `shared-core` labels; shared tasks belong to both delivery surfaces. Repository-maintenance stories are tracked separately in the task index. The first integrated target is one complete workflow callable through the shared interface and usable through the platform. Historical alpha qualification keeps its own recovery dependency and does not block unrelated work on available source.

## Next small deliverable

Refine [S-12 — define the business question and operating limits](<../backlog/tasks/s-12 - Define-the-business-question-and-operating-limits.md>) into one executable Databricks reference scenario. Record the question, metric and target, relevant population and period, available access, complete workload boundary, expected answer checks, freshness, resource/spending limits, and material escalation conditions. Unknown values remain open inputs rather than invented numbers.

Done for this planning slice means the first implementation story can be selected without guessing the business result or access needed. A live Databricks connection is not established by this plan. Hudson still selects and starts each development task.

[S-02 — recover the existing alpha](<../backlog/tasks/s-02 - Recover-and-reconcile-the-existing-alpha.md>) remains a separate preservation task. [S-03 — toolkit installation](<../backlog/tasks/s-03 - Install-the-toolkit-from-a-clean-environment.md>) depends on recovery. Missing candidate access does not block independent work on the available source. Preserve the completed support script and the earlier toolkit decisions as scoped history.

## Local development workflow pilot

The development pilot is separate from the autonomous product. Hudson manually chooses a task and starts Codex. Planning alignment and the migration of all 36 stories into Backlog.md are complete. Task checkout, verified execution restrictions, an interruption/resume trial, and a management-effort comparison remain separate later stages. Product schedules and coordinated agents do not authorize an autonomous development scheduler.

## Maintaining alignment

Before implementation, identify the business outcome, selected story, dependencies, expected result, and completion check. At review, state what users can actually do and what remains missing. Keep current status in the authoritative task record and dated results in the relevant review.

The [system design](SYSTEM_DESIGN.md) separates current source from proposed capabilities. The [earlier issue-review plan](roadmap/v0.1.0-development-roadmap.md) remains historical. This roadmap does not grant access, spending, external-write, publication, merge, or deployment authority.
