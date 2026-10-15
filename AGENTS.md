# BackIntel working rules

## Start here

- [Roadmap](docs/ROADMAP.md): product outcome, current/next/later priorities, and the next task dependency.
- [System design](docs/SYSTEM_DESIGN.md): existing behavior, proposed capabilities, constraints, and decisions.
- [Backlog.md task index](docs/roadmap/agile-backlog.md): links to the authoritative tasks in `backlog/tasks/` and the shared delivery contract. Sprint reviews retain historical evidence.

## Keep work tied to the roadmap

- Hudson selects each development task and starts Codex manually. Keep one active task in the local workflow pilot. The BackIntel product is intended to operate autonomously and continuously within its granted limits; do not confuse these two workflows.
- Before product implementation, identify the selected backlog item, roadmap outcome, bounded deliverable, acceptance criteria, dependencies, owned files, and stop condition. Missing source or product decisions stay explicit blockers.
- Follow the selected story's dependencies. Toolkit installation requires recovery of that candidate; independent work on current source does not. Never recreate an unavailable candidate from chat summaries or repeat completed recovery searches without a new lead. Completed app or script demonstrations do not qualify the toolkit or the autonomous product.
- Save changes, checks, blockers, and the next step in the task record before an interruption. At review, compare the actual result with its acceptance criteria. Report scope changes for Hudson's decision.
- Backlog.md owns task details, acceptance criteria, dependencies, and current status for product and repository-maintenance stories. Keep roadmap documents as outcome guidance and links; do not maintain duplicate live status or create external tracker records without authorization.
- Classify product delivery scope with `toolkit`, `platform`, and `shared-core` labels. Shared tasks carry all three labels and have one implementation and task record. Follow the [delivery split](docs/roadmap/README.md#toolkit-and-platform-delivery); do not duplicate shared work, infer that the historical alpha was recovered, or require all proposed microservices before a useful workflow. Repository maintenance uses `development-workflow` and topical labels outside the product milestones.
- Planning alignment and Backlog.md setup are complete. Keep task checkout, verified execution restrictions, and the development trial as separate stages. Check actual permissions before claiming sandbox isolation; app and MCP permissions remain separate.
- Preserve the existing publication, merge, deployment, spending, production-data, and credential boundaries. A completed task does not grant those permissions.

## Use Backlog.md

- Use the Backlog.md CLI for task, draft, milestone, and metadata changes. Do not edit its generated task Markdown directly. Search/read the existing task before updating it; do not create a duplicate.
- Before task work, run `backlog instructions overview`, then the matching `task-creation`, `task-execution`, or `task-finalization` guide. Use `--json` for structured reads and `--plain` for concise human reads.
- The migrated roadmap uses S-01 through S-36; the index retains the old S01–S36 mapping. New stories receive their next native ID through the CLI. Statuses are To Do, In Progress, Review, and Done. `needs-refinement` and `blocked` are start gates; `optional` requires a selected need. Native dependency readiness alone does not authorize implementation.
- Record the researched implementation plan after task selection. Save progress, checks, blockers, and the next step through the CLI before interruption. Review and Done require the stated acceptance and applicable review; migration is not fresh product validation.
- All tasks are unassigned until selected. Keep one task active in this development pilot. S-25 has an alternative prerequisite: select the applicable interface, then set S-35 or S-11 as its native dependency; do not require both by default.
- Automatic commits, remote operations, and cross-branch checks are disabled for this local pilot. Commit and push still require the existing explicit authorization.

The pilot uses Backlog.md 1.53.0 installed outside the repository. From the BackIntel checkout:

```sh
BACKLOG_BIN=/Users/hudson/Documents/Codex/2026-10-13/localdevelopmentpilot/work/BacklogTool/node_modules/.bin/backlog
"$BACKLOG_BIN" instructions overview
"$BACKLOG_BIN" task view S-12 --plain
"$BACKLOG_BIN" browser --no-open
```

Here, `backlog` command examples mean that installed executable. For another machine, use the [official installation instructions](https://github.com/MrLesk/Backlog.md#installation). The repository contains the task files and configuration; the local executable path is a pilot convenience.

## Preserve the product scope

- The user supplies a business objective, measures/targets, permitted connections, and operating limits. BackIntel discovers data, creates and checks preparation and analysis, develops methods, coordinates agents, and keeps answers current. Databricks is the reference source; no live connection is assumed.
- Whole-workload processing, continuous operation, cross-system communication, coordinated agents, and agreed scale are core outcomes. Deliver them in bounded stages; do not reduce the product to manual CSV steps or a fixed analytical toolkit.
- Reuse current adapters, analytical tools, evidence, permissions, budgets, and recovery where suitable. Record generated pipelines, autonomous methods, and capacity as proposed until their actual completion checks pass. Internal batching is allowed; requiring users to repeatedly split workloads is not the target experience.

## Code cleanup

- Run `bash scripts/check-dead-code.sh` after removing code and before review.
- For cross-file changes, run `graphify update .`, inspect callers and dependencies, and verify findings in current source and framework registrations.
