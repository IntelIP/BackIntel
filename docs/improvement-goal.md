# BackIntel analytical reliability and supervised improvement

Task specification for the owner's 2026-11-10 instruction to execute the complete
improvement goal. The owner approved the business scope and explicitly waived human
calibration on 2026-11-10. Linear owns task status.

## Owner decision recorded on 2026-11-10

The owner instructed: “all are approved continue without human calibrtion”. This approves
the [business definitions and acceptance scope](acceptance-spec.md), the proposed $5 total
experiment allowance, and commit/push publication of this implementation after required
checks. It explicitly waives human calibration as a completion requirement for this goal.
Required implementation checks, independent references, mandatory cases, regression checks,
cost accounting and CI requirements remain in force. The allowance covers analyst, coding
worker and judge calls together; it does not authorize purchasing credits or deploying.

No human ratings or calibration result are claimed. The historical
[calibration report](../results/human-review-20261110/calibration-initial.json) retains its
original `awaiting_human_review` status, blank labels and zero rated criteria. That report
describes the packet when generated; this dated owner decision records the later waiver.
Method-judge scores remain uncalibrated against human labels and must be described as such.

## Outcome

Deliver a trustworthy benchmark, demonstrated improvements in analytical reliability,
and a working supervised improvement loop. Preserve the original experiments and make
every claimed improvement reproducible in LangSmith. The handoff supports an informed
decision about a controlled pilot; it does not establish production reliability.

## Team and ownership

The lead integrates three development workstreams. The evaluated analyst remains one
Deep Agents lead with bounded read-only tools and isolated Python.

- Data/benchmark: data suitability, business conventions, independent references,
  development and reserved acceptance cases, temporal replay.
- Analyst reliability: data sufficiency, stopping, tool errors, executable evidence,
  and report consistency. The worker does not change acceptance criteria.
- Evaluation/improvement: grading, calibration tooling, versioned comparisons, budget
  accounting, isolated candidate workspace, and acceptance/rejection decisions.
- Lead: CLI integration, owner review, real experiment execution, roadmap, publication
  preparation, and final acceptance. Shared-tree edits have explicit file ownership.

## Required work

1. Define the intended first business use case, required data, and mandatory acceptance
   criteria before optimizing against them. Distinguish revenue from profit and
   association from causation. Obtain actual owner review of consequential definitions.
2. Preserve all 73 existing scenarios and historical results. Inspect relevant source
   provenance, transformations, grain, missingness, duplicates, joins, units and time
   cutoffs. Add meaningful cases for observed failures and data gaps. Reserve cases not
   used to tune fixes and keep answers outside evaluated-agent and candidate-worker access.
3. Independently verify important reference calculations. Challenge graders with valid
   alternatives, wrong values, misleading methods, broken evidence and inappropriate
   refusals. Preserve the human-review packet; human calibration is waived by the owner for
   this goal, so do not infer human agreement from automated grading.
   Version grader changes independently of agent changes and retain original experiments.
4. Fix the observed missing-cost query loop, broken cited programs and duplicate metrics
   using general runtime changes. Test missing-data and sufficient-data counterparts,
   original failures, reserved variants and healthy baseline cases. Repeat cases only
   when observed variability could materially change acceptance.
5. Extend historical replay with relevant changes, no-change periods, late observations
   and data disruptions. Measure detections, false alarms, evidence and report consistency.
   Each replay sees only information available at its observation time.
6. Build a supervised loop: select a recorded failure; classify its layer; assign one
   bounded coding task; create an isolated candidate; compare baseline and candidate on
   fixed data/scoring; report quality, regressions, costs and duration; present a passing
   candidate for review and retain the previous revision when it fails. Protect graders
   and reserved truth from the candidate worker.
7. Demonstrate one real failure-to-candidate-to-LangSmith cycle and rejection of a
   regressing candidate. Verify affected storage paths and repository checks. Prepare
   finished changes under the recorded publication approval; verify hosted CI after push.
8. Reconcile Linear and deliver commands, experiment links, data-quality findings,
   reference checks, the calibration waiver and limitation, comparisons and operating instructions.

## Acceptance

Completion requires all of the following, with concrete linked evidence:

- Reviewed intended capabilities, consequential definitions, and acceptance criteria.
- Data limitations and important references understood for the intended use.
- All mandatory cases pass; no unresolved regression materially changes the intended use.
- The three observed failure classes have demonstrated general fixes.
- Reserved cases and relevant repeat trials support the claims.
- The owner calibration waiver is recorded; blank labels remain blank, and uncalibrated
  method scores are not presented as human-validated judgments.
- Comparisons pin dataset/reference/scorer/judge identity independently of the candidate.
- A real improvement cycle and a regressing-candidate rejection are demonstrated.
- Required local checks and hosted CI after authorized publication pass.
- Reproducible artifacts explain remaining limitations and pilot requirements.

Missing data can make a question legitimately unanswerable. A proper explanation of that
gap is success for a declared refusal case; a crash or fabricated answer is failure.
Exploratory failures remain visible. No completion by summary, elapsed time, or budget
exhaustion. Reopen completed work only for information that can change the result.

## Authority and operating limits

Reuse the approved model/provider configuration, LangSmith, local services and existing
credentials. No new dependency or model selection without required provenance checks.
Never purchase credits or create cloud resources implicitly. Paid evaluations require
bounded batches within the approved $5 total allowance and complete cost reporting including judges.
Do offline work while required owner input is pending. Owner input cannot be fabricated.

Repository AGENTS.md requires owner approval before commits, pushes or deployment.
The 2026-11-10 owner instruction above supplies commit/push approval for this implementation
in addition to the earlier publication of cb963fd and CI repair.
Production deployment, runtime scheduling and customer integrations remain separate.

## Guidance

- [Existing benchmark](benchmark.md), [measured results](results.md), and
  [project knowledge](../.agents/skills/backintel-benchmark-world/SKILL.md).
- Skills: Analyze Data Quality and Eval Engineering for data/cases; Deep Agents Core,
  Diagnosing Bugs and Ponytail for runtime; Evaluation and Advanced Evaluation for grading.
  Read the applicable SKILL.md and its task-relevant references, not every workflow.
- Shared engineering knowledge: the curated AgenticEngineering production-template.md
  self-improvement loop and technology-selection-policy.md.
- [LangSmith datasets](https://docs.langchain.com/langsmith/manage-datasets),
  [comparisons](https://docs.langchain.com/langsmith/compare-experiment-results),
  [human feedback](https://docs.langchain.com/langsmith/improve-judge-evaluator-feedback).
- [Deep Agents skills](https://docs.langchain.com/oss/python/deepagents/skills) and
  [tools](https://docs.langchain.com/oss/python/deepagents/tools).

Match APIs to uv.lock and installed source. Documentation examples do not authorize
stack replacement. Dataset splits organize examples; they do not enforce access isolation.
