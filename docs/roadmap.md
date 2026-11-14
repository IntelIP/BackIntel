# Capability roadmap and next development increments

BackIntel starts at **v0.0.1, experimental**. Version numbers below describe acceptance
milestones, not released capability or delivery dates. The internal
[Linear project](https://linear.app/intelip/project/backintel-0287c22fe5a7) owns priority and
execution status. This public plan describes the work and its completion criteria without
requiring tracker access. Planning snapshot: 2026-11-13 UTC.

## Starting point

The agent can discover assigned schemas, execute bounded read-only native queries, run
Python/shell analysis in SmolVM and return executable evidence. Its opt-in specialist can
render reports, five chart families, CSV and XLSX through a separate clean VM. The runtime
uses one Deep Agents graph per request, with no automatic delegation or production scheduler.
GPT-6.1 Sol is the specialist default; the benchmark analyst remains separately configured.

Its strongest demonstrated capability is **bounded business analysis**. Data engineering
covers source access, profiling and temporary transformations, not production ETL. Data
science covers descriptive analysis and calculation checks; forecasting, causal inference
and general statistical-model validity remain unqualified. Native MongoDB deployments and
vector databases are not established by the FerretDB benchmark.

The original controlled SmolVM specialist baseline passed 3/4 cases, followed by a successful
targeted energy fix. A fresh eight-trial guidance comparison on 2026-11-13 passed 4/4 on both
versions, including the corrected grader. The candidate eliminated incorrect virtual-skill
shell lookups in all four cases, with no measured task regression. Both arms refused missing
costs without rendering a substitute report. These are small controlled trials; the broader
92-response reliability comparison completed with two mandatory reserved regressions,
so the measured candidate remains rejected and a revised qualification is required. See
the [revised checkpoint](../results/reliability-revision-20261114.md) for the subsequent
45/46 candidate result and remaining report-binding failure. Fresh generation-3
qualification of the latest implementation remains pending. See
[current capabilities and measured outcomes](../README.md#what-has-been-measured).

## Next achievable increments

Each item below is small enough to define a concrete development handoff. A role names the
work involved, not an assigned person or a new runtime sub-agent. The
[four-case evaluation package](../evals/analysis/cases.md) supplies its scripts and fixtures
in the checkout; publication and release evidence belongs in the linked Linear issues.

| Order | Deliverable | Completion criteria | Dependency / tracker |
| --- | --- | --- | --- |
| 1 | Reproducible foundation and evaluation handoff | Publish the reviewed SmolVM/completion candidate and docs; publish the four-case runner, case definitions, tests and reference generation as a separately reviewed change; verify a clean checkout can run the offline suite without private files | Engineering + evaluation; INT-451, INT-454 |
| 2 | Reliable finish, refusal and artifact claims | Clarify virtual skill reads versus shell paths; stop unsupported profit calculations without unnecessary report generation; never claim an unexported file exists; add regressions for these observed behaviors and retain the completion recovery/call-limit tests | Existing failure traces; INT-435, INT-454 |
| 3 | A measured reliability improvement | Freeze model, inputs, prompt/skills, graders, candidate and finite allowance; execute the 92-response comparison described below; improve mandatory historical failures without regressing controls; assess all development and reserved cases | Readiness and frozen comparison plan; INT-430–438, parent INT-429 |
| 4 | An unfamiliar-domain data package | Qualify three distinct non-retail sources, including terms, provenance, hashes, units, grain, nulls and joins; reserve one entire domain; define six challenge questions and one bounded discovery report per domain | Data + evaluation; INT-440, INT-441, INT-443 |
| 5 | First drop-in dataset run | Mount one qualified development folder and its ordinary documentation through configuration; discover its shape with bounded tools; produce a supported report without notebooks, hidden references or handcrafted answer hints | Item 4; runtime + analysis; INT-442 |
| 6 | Domain-transfer evidence | Record a first-pass baseline on development domains; make a justified general revision; freeze it before seven reserved-domain scenarios; report all 21 outcomes and independently checked discoveries by domain | Items 3–5; INT-444, parent INT-439 |
| 7 | Real large-data acceptance | Freeze a real corpus of at least 10 GiB, plus deterministic roughly 100 MiB and 1 GiB samples; run equivalent questions at each size with correctness, memory, latency, scan/spill and graceful-limit evidence | Qualified source and compatible host/runtime; INT-446, parent INT-398 |
| 8 | Reusable decision-report packs | Define metric grain, populations, units and required inputs; compose findings, evidence, charts and sheets for standing business questions; validate temporal consistency and supported conclusions | Reliable analysis and artifact delivery; INT-455–457 |

Items 1–3 are the immediate engineering iteration. Dataset qualification and task design can
proceed alongside them, but scored expansion waits for frozen criteria and its own authorized
allowance. This plan does not authorize those runs or provision new compute.

### Reliability comparison: what “done” means

The planned **92 responses** comprise 24 original-regression responses (six cases, two
trials per baseline/candidate arm), 34 development responses (17 cases per arm), and 34
reserved responses (17 cases per arm). A response may require many model calls.

- Keep the three historical failures and three healthy controls; require a demonstrated
  improvement on that comparison and no material control regression.
- Evaluate all 17 development cases and all 17 reserved variants against the frozen
  mandatory correctness, refusal, evidence and temporal-consistency criteria.
- Keep model/provider and input visibility comparable. A model change is a separate
  experiment, not an unexplained part of the candidate.
- Preserve failed and invalid attempts, token/cost accounting and the distinction between
  infrastructure failures, incorrect answers and unfinished delivery.
- Human calibration remains waived for the current work. Report method scores as
  uncalibrated; do not turn that waiver into fabricated business-user acceptance.

### Unfamiliar data: what “drop it in the sandbox” means

Transport, building energy and weather are **candidate domains**, not already qualified
or downloaded corpora. Kaggle pages, competition notebooks and public mirrors do not by
themselves establish permission or independent ground truth. The data package must record
its source rights, exact version, transformations, schema and limitations before use.

The evaluated agent receives the business brief, read-only data and ordinary source
metadata. Solutions, Kaggle notebooks, evaluator code, private references and reserved truth
remain outside its mounts. An open-ended discovery report may contain up to five supported
findings; fewer are acceptable when the data warrants them. Novel-sounding claims and long
narratives do not substitute for independently verified facts.

The two small synthetic energy/service fixtures do not satisfy this domain-transfer goal.
“Cold-start” means no BackIntel-specific tuning on the held-out domain; public pretraining
exposure cannot be excluded.

### Large-data prerequisite

The current SmolVM integration is qualified only on macOS ARM64. The earlier proposal to
use the Windows workstation for heavier workloads is a host candidate, not an implemented
SmolVM deployment there. Qualify a compatible host/runtime and available RAM, disk and spill
capacity before the full run. A 4 GiB VM profile, generated TPC-H SF1 or a small replicated
file does not fulfill the real 10 GiB target. Do not close this milestone from a sample alone.

## Version acceptance map

| Target | Capability delta | Required exit evidence |
| --- | --- | --- |
| v0.0.1 | Measured analytical foundation | Reproducible published source; reliable terminal behavior; frozen baseline/candidate reliability results and documented limitations |
| v0.0.2 | Unfamiliar-domain analysis | Three qualified domains, at least 21 scenarios, separate development/reserved results and independently supported findings |
| v0.0.3 | Large-data sandbox | Real 10 GiB acceptance with staged scale checks, bounded compute and graceful exhaustion |
| v0.0.4 | Verified visual artifacts | Reports, charts and workbooks agree with independently checked tables; delivery and refusal semantics hold across acceptance tasks |
| v0.0.5 | Business-analysis report packs | Reusable metric definitions and standing reports pass factual, evidence and temporal-consistency checks |
| v0.1.0 | Controlled business-analysis pilot | One named workflow, approved read-only data contract, representative development/reserved cases and an explicit pilot-entry decision |
| v0.2.0 | Durable background execution | Persisted jobs, schedule/data-ready triggers, cancellation, deadlines and bounded retries survive whole-job failure scenarios |
| v0.3.0 | Operational monitoring | Qualified connectors, freshness/missing-data handling, measured alert quality, deduplication and authorized delivery |
| v0.4.0 | Contextual/statistical analysis | Document retrieval and statistical/forecasting workflows improve held-out tasks with honest uncertainty; vector retrieval is optional |
| v0.5.0 | Managed background-intelligence beta | User controls, run history, artifact access and spending limits; sustained-operation evidence; bounded improvement proposals |
| v0.9.0 | Release candidate | Measured beta gaps resolved, operational/support boundaries defined, reproducible candidate and rollback plan |
| v1.0.0 | Supported background-analysis service | A declared workload and connector matrix, supported artifact delivery, operational objectives and verified recovery/rollback |

Renderer and artifact-contract components already exist ahead of their numbered milestone.
Implementation progress does not imply that the corresponding release criteria have passed.
Fine-tuning is an optional later experiment only if approved data and held-out results show
value beyond prompt/tool improvements. LangSmith provides measurement and comparison; it
does not automatically train or promote a model.

## Version development loop

1. Select the capability and its Linear acceptance issue; state the baseline, boundaries,
   mandatory/regression/reserved cases, candidate owner and finite experiment allowance.
2. Implement the smallest justified change; review the actual diff and run relevant code,
   runtime and artifact checks.
3. Compare frozen baseline and candidate in LangSmith. Diagnose the failed layer; retain
   the attempt and revise only the responsible behavior. Never rerun until a lucky pass.
4. Review the exact candidate, hosted CI and evaluation evidence. Record what improved,
   what regressed, usage and remaining uncertainty.
5. Publish a version only through its authorized release process, retain rollback identity,
   and feed observed failures into the next development cycle. Green CI alone is not
   analytical acceptance; `accept_for_review` is not deployment authority.

## What the current evidence establishes

The original 73 scenarios exercise historical Olist and Online Retail II data plus a
synthetic TPC-H workload. The [capability report](results.md) records measured model
results and their failures. The fresh demo also exposed variable refusal behavior: a
question that had passed in an earlier SQLite sweep later exhausted its execution limit.

The [data-quality assessment](data-quality.md) identifies consequential grain, coverage,
duplication and identity limitations. Twelve selected existing references matched separate
SQLite calculations, but both calculation paths share the acquisition and canonicalization
pipeline. That agreement does not certify source semantics or every business definition.

The [acceptance specification](acceptance-spec.md) adds 34 targeted controlled cases:
17 development cases and 17 reserved variants. Their deterministic construction and
independent SQL checks establish fixture readiness. They do not themselves establish that
the analyst passes them. The [improvement-loop guide](improvement-loop.md) distinguishes
offline orchestration checks from the real model runs needed to demonstrate a completed
improvement cycle. The owner [approved the business scope and waived human calibration](improvement-goal.md#owner-decision-recorded-on-2026-11-10)
on 2026-11-10. Method scores remain uncalibrated against human labels; the waiver does not
establish agreement with domain reviewers or population reliability.

These counts are not 107 independent observations drawn from a defined customer population.
The original cases share datasets and business assumptions; storage repetitions test
adapter behavior, not new customers. The controlled variants share generation patterns.
Millions of source rows measure data scale, while case coverage measures selected behaviors.
Neither the case count nor a single aggregate pass rate estimates population reliability.

## Evidence-driven decision sequence

| Decision | Evidence needed | Resulting action |
|---|---|---|
| Accept the initial business scope | Owner-approved metric definitions and required data for repeat purchasing, delivery/satisfaction, and seller/category revenue; approval recorded on 2026-11-10 | Freeze the intended populations, grains and exclusions. Obtain costs before expanding revenue claims to profit; obtain a defensible design before making causal claims. |
| Accept a reliability improvement for review | Baseline and candidate evaluated with the same frozen data and graders; mandatory cases pass; answerable controls do not regress; relevant variability and accounting are reported | Review the focused change. A failed candidate remains a useful finding and returns to development. |
| Enter a controlled pilot | A real improvement cycle and representative cases from the intended pilot workflow support the agreed acceptance criteria; disclose the current human-calibration waiver and its limits | Authorize a limited read-only pilot with a named audience, workload and feedback process. This is a separate owner decision; customer-derived feedback can subsequently support human calibration. |
| Add live scheduling | The pilot shows useful recurring analysis, realistic freshness handling, acceptable false alarms and stable reports across successive observations | Implement the required cadence and input-readiness checks, with bounded spend and clear handling of incomplete data. Historical replay alone does not establish this readiness. |
| Add customer integrations and production hosting | The pilot identifies actual source systems, access scope, workload, operational failures and service expectations | Implement only those integrations and operating requirements; obtain deployment/resource approval and verify the deployed behavior. |

A higher overall score cannot compensate for a material regression in a mandatory refusal,
evidence or business-definition case. Conversely, an infrastructure failure or exhausted
evaluation allowance invalidates that trial; it does not demonstrate that the analyst is
incapable. Review per-case results and unresolved limits before making the next decision.

## Bringing representative cases and human feedback into the benchmark

For an authorized pilot, collect actual business questions with their decision context,
approved read-only data snapshots, expected grain, observation time and required sources.
Preserve customer permissions and remove identifying details where appropriate. A domain
reviewer should validate the metric meaning and whether the available data can answer it;
an independently executable calculation should supply numerical truth where possible.

Assign each case to a purpose before using it:

- **Development:** representative examples and observed failures that implementation workers
  may inspect. Use them to diagnose and improve the analyst.
- **Reserved acceptance:** unseen questions, source/snapshot variants or business situations
  held outside the implementation worker's context. Freeze the candidate and comparison
  policy before running them. Related variants must be grouped deliberately so a near-copy
  of a development case is not presented as independent validation.
- **Regression:** previously resolved failures and important successful behaviors retained
  to catch later breakage. If an exposed reserved failure informs a fix, move it into this
  category and reserve a fresh independent case for the next acceptance decision.

Human feedback should identify the specific claim, definition, omission or unsupported
inference at issue. Separate business acceptance from numerical correctness and explanation
ratings. Resolve contradictory reviewer definitions before changing the oracle, and version
material rubric changes separately from agent changes. Preserve earlier judgments and
experiments instead of overwriting an unfavorable result.

This is proposed pilot feedback work, not an outstanding human-label requirement for the
current goal. The preserved blank review packet must not be counted as completed feedback.

Select coverage from the pilot's tasks and failure consequences: common requests, important
rare failures, missing-data boundaries, dirty joins, timing changes, and reasonable alternative
solutions. Choose repetitions where observed stochastic behavior could change the decision.
Set any operational quality, cost or latency thresholds from the agreed pilot requirements;
this roadmap does not invent a universal accuracy target or claim statistical significance
from the current controlled cases.

## Boundaries after acceptance

An improvement-loop result of `accept_for_review` remains a review recommendation. It does
not authorize a commit, merge, deployment, purchase, new provider or expanded data access.
Each execution campaign needs its own recorded authorization and allowance. Historical
allowances do not fund new domain/scale experiments. Deployment and purchases remain
separately authorized decisions.
Development subagents coordinate engineering; they do not imply runtime delegation inside
the analyst. Scheduling, customer integrations and production infrastructure remain separate
proposed work until the evidence and owner authorization support them.

The immediate value of the loop is repeatable learning from failures under fixed criteria.
Pilot observations should later feed that same development/reserved/regression process,
allowing the roadmap to follow demonstrated needs rather than accumulated features.
