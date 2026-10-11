# Sprint 2 — Recover the alpha and confirm clean installation

Prepared October 10, 2026. **Status: selected; execution blocked on the original alpha bundle.**

## Sprint goal

A developer can use the preserved toolkit alpha without relying on the team's private workspace. Recover and reconcile its source, then install that identified candidate in a clean environment and open its commerce and support examples.

Success requires recovery and clean installation. The locator, recorded demo, and historical test reports do not establish either result. Live analysis and broader alpha qualification follow in later stories.

**Owners:** Codex executes and records results. Hudson supplies the original candidate ZIP or an accessible download link.

**Planning timebox:** one focused working day after candidate access is available. This is a proposed capacity limit, not a measured delivery estimate. Start one story at a time. Record a blocking prerequisite and its next action; do not silently extend the sprint.

**Boundary:** $0 new provider or infrastructure spending. Use local inspection, installation, and relevant existing checks. Recover source separately from the canonical checkout and preserve the recorded demo. No live-model calls are needed for this sprint's acceptance.

## Ordered scope

| Order | Story | User issue | Current state | Start condition |
| --- | --- | --- | --- | --- |
| 1 | S02 — Recover and reconcile the alpha | Preserved work cannot be reused until its source is accessible and identified. | Blocked on candidate access | Original ZIP or an accessible source bundle is supplied. |
| 2 | S03 — Install from a clean environment | A developer needs complete setup instructions and usable example entry points. | Refine; conditional pull after S02 | Candidate identity, dependencies, inputs, and installation surfaces are known. |

These are local planning labels, not external issue IDs. S03 remains unstarted until S02 passes. Exact installation changes come from the recovered source, not chat summaries.

## S02 — Recover and reconcile the alpha

**User story:** As a maintainer, I need the original alpha source and relevant results, so that we continue preserved work instead of recreating it.

**Tasks, in order:**

1. Receive `backintel-agent-toolkit-0.1.0a2-candidate.zip`, or a download link this chat can access. The source lead is **“Review testing and demo workflows.”** The [Sprint 1 recovery record](sprint-1-review.md#s02-discovery--source-blocker-and-retrieval-action) contains its locator, expected commit, and expected archive hash.
2. Check the archive identity and list its contents before executing anything from it. Explain a source/version mismatch before reuse.
3. Preserve the candidate separately. Check its manifest and file hashes, source bundle, package, dependency record, commerce/support examples, and relevant run records. Keep credentials and private datasets out of recovery outputs.
4. Compare the recovered package and interfaces with canonical source. Identify reusable work, compatibility changes, and remaining gaps. Preserve the demonstration and historical source identity.
5. Record the integration decision and exact source, package, examples, and quickstart surfaces available for S03.

**Done when:** The candidate is preserved and identified; required contents are checked; source comparison and integration decision are recorded; S03 has a known installation target. Historical results retain their original scope. A filename or chat report alone cannot close S02.

**Failure case:** For a missing, inconsistent, or incomplete bundle, record the exact dependency, owner, and retrieval or correction action. Do not reconstruct the alpha from summaries or substitute the older resume package.

**Demo/output:** Recovery record with source identity, preserved package, both examples, relevant evidence, reuse decision, and installation handoff. Candidate access is missing; recovery has not run.

## S03 — Install the identified candidate from a clean environment

**User story:** As an agent developer, I need reliable installation and a complete quickstart, so that I can begin without undocumented steps or the team's private workspace.

**Tasks, in order, after S02:**

1. Read the package's supported Python version, dependencies, example configuration, and required inputs. Choose a matching isolated environment.
2. Install the identified package and dependencies. Reconcile only packaging or setup defects that prevent this outcome.
3. Open the commerce and support example entry points. Show supported agent configuration and explicit inputs, including separately configured credentials for a later live run. No model or saved-work variable should be left for the developer to guess.
4. Exercise one material missing-input or missing-dependency case. Confirm the instructions identify the remedy. Installation and example setup must not silently discover credentials or initiate paid analysis.
5. Save exact commands, Python/package versions, observed results, and remaining prerequisites in the sprint review. Retain only synthetic example inputs.

**Done when:** The identified candidate installs in a clean environment, both example entry points are usable, and the selected setup failure gives a specific remedy. Required inputs are documented and no paid analysis occurs. This does not prove completed live analyses or release readiness.

**Demo/output:** Installation receipt, runnable setup instructions, both example entry points, and the observed failure remedy. Exact files and commands follow source recovery; S03 has not started.

## First handoff and inspection commands

Supply the original candidate ZIP or an accessible download link. The historical cloud path is inaccessible from this local chat. Committing this plan does not resolve candidate access.

After the ZIP is supplied, set its actual local path and inspect it:

```sh
backintel_alpha_zip="/absolute/path/backintel-agent-toolkit-0.1.0a2-candidate.zip"
shasum -a256 "$backintel_alpha_zip"
unzip -Z1 "$backintel_alpha_zip"
```

Compare the hash with the expected value in the recovery record. These are inspection instructions, not commands that have already passed. Use the actual manifest and quickstart for subsequent steps.

## Sprint review and stop condition

Show the identified source and integration decision, then clean installation and both example entry points. Record S02 and S03 as Done, Blocked, or Cancelled from actual outcomes. Preserve useful evidence and stop only processes created for this sprint.

Do not close the sprint while source recovery or selected installation checks remain unfinished. Once both outcomes are demonstrated, select the next work on access, spending, and interrupted-work recovery: S04–S06.

## References

- [Ordered backlog](agile-backlog.md)
- [Product roadmap](README.md)
- [Archived Sprint 1 plan](sprint-1.md)
- [Accepted Sprint 1 results and source locator](sprint-1-review.md)
