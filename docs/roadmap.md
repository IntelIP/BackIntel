# From benchmark evidence to a controlled pilot

This document explains how evidence should guide BackIntel's next product decisions.
It is a proposed decision sequence, not a second status tracker. Linear owns delivery
status and priority, including [INT-429](https://linear.app/intelip/issue/INT-429).
The implementation retains one Deep Agents lead, bounded read-only queries, isolated
Python, the approved model/provider configuration, and LangSmith evaluation.

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
Commit/push authority for the current implementation comes separately from the recorded
owner approval; the approved experiment allowance is $5 total. Deployment and purchases
remain outside that approval.
Development subagents coordinate engineering; they do not imply runtime delegation inside
the analyst. Scheduling, customer integrations and production infrastructure remain separate
proposed work until the evidence and owner authorization support them.

The immediate value of the loop is repeatable learning from failures under fixed criteria.
Pilot observations should later feed that same development/reserved/regression process,
allowing the roadmap to follow demonstrated needs rather than accumulated features.
