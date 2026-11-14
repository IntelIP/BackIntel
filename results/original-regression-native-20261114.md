# Native original-regression comparison — 2026-11-14 UTC

The recovered original-regression comparison returned **accept for review**. The current analyst produced **12/12 fully supported responses**, versus **9/12** for the historical analyst. All three failed case/trial results improved, all mandatory cases passed, and no frozen correctness/evidence/refusal gate regressed.

This completes **24 of the planned 92 responses**: six original scenarios, two trials per arm. It does not complete the 34-response development or 34-response reserved-acceptance batches. Those remain frozen and unstarted. No merge, release, human calibration or production-reliability claim follows from this result.

| Measure | Baseline | Candidate |
| --- | ---: | ---: |
| Fully supported responses | 9/12 | 12/12 |
| Numerically correct / correct refusal | 11/12 | 12/12 |
| Reproducible evidence, applicable answered cases | 8/10 | 10/10 |
| Correct answer/refusal decision | 12/12 | 12/12 |
| Model calls, including judges | 107 | 105 |
| Conservative estimate for completed responses | $0.4965415 | $0.48980675 |
| Summed analyst latency, excluding judges | 644.17 s | 790.69 s |

The candidate took longer in these measured answers. Recovery also changed job boundaries, so this is not a clean throughput comparison. Method ratings remain advisory and uncalibrated; the frozen policy contains no method-score or latency threshold.

## Case coverage

| Scenario | Baseline supported | Candidate supported | Candidate evidence |
| --- | ---: | ---: | --- |
| olist-l1-01 | 2/2 | 2/2 | [Trial 1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/ea92d11b-ac1f-4b47-81e7-28c6f2c460fa), [trial 2](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/b8042aa6-789f-40c7-86e2-8e0afb0e8288) |
| olist-l3-07 | 2/2 | 2/2 | [Trial 1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/5102ef6f-d9d6-4521-8c4c-88ebac5f4b23), [trial 2](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/42c6d206-d5d6-4564-97d4-0c261f7089c0) |
| olist-l5-01 | 1/2 | 2/2 | [Trial 1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/c38db789-3b02-4d85-bc9b-70f2be596078), [trial 2](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/d58a4813-72d4-4701-a537-bc102d0c63ab) |
| olist-l5-02 | 0/2 | 2/2 | [Trial 1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/22a8a8d8-b7ae-4092-9513-735e4f76245a), [trial 2](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/08687b79-74dc-40c4-9760-0339be19fbef) |
| olist-l6-2018-03 | 2/2 | 2/2 | [Trial 1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/5102ef6f-d9d6-4521-8c4c-88ebac5f4b23), [trial 2](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/dec62ea4-53a7-444c-bf33-64a1670d017d) |
| olist-l6-repeat-2017-09 | 2/2 | 2/2 | [Trial 1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/f1d7c41a-36fe-4cb7-8af8-8b0b87f5b0c8), [trial 2](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/111ef755-1732-4acd-9641-f2788d349845) |

The baseline delivery report missed two required facts in one trial and supplied syntactically broken evidence in the other. The baseline repeat-purchasing report had correct facts but broken evidence in its first trial. The candidate supplied correct, reproducible results for all three slots. The missing-cost refusal remained correct in both arms; this run does not show an improvement where the baseline already passed.

[Baseline trial 1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/6b9e6bbd-9093-4c58-a17d-9ddbcdedb650), [baseline trial 2](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/dea9c5e6-75f4-4a38-b74f-e71e6bb89a94). Read-back verified **24 run outputs and 144 feedback values**, including source/data/evaluator identities and judge usage.

## Recovery and spending

The original execution stopped inside `run_python`. No process exit receipt survived, so the exact termination cause is unknown. One completed candidate record was local; LangSmith retained a second complete answer and all six grades. Both were preserved without new model calls. The third attempt had seven observed completed model calls but no final answer. Its trace remains retained and has an operator recovery annotation pointing to one explicit replacement. Nine other slots had never started. No completed unfavorable result was discarded.

Recovery used one case per job with disk-flushed reservations before dispatch and settlements after responses. Pending or unpriced calls stop subsequent jobs. The sandbox preflight passed with public networking blocked. The recovery script reused the unchanged frozen analyst, grader and comparison functions; it added no prompts, model selection, reference answers or scoring tolerance changes.

- New recovery usage: **$0.4056835**, 86 model calls, within its separate $1 cap; complete estimated accounting and no reservation breach.
- Observed usage for the full comparison plus the abandoned partial attempt: **$1.01544625**.
- The interrupted batch’s full original $1 allowance remains encumbered. Its unverified remainder of **$0.39023725** is retained separately rather than treated as free.
- Including prior goal usage/reserves, **$1.71356956225** is used or encumbered against the original $5 authorization. That leaves **$3.28643043775**, including the $2 allocated to the unstarted development/reserved batches.

These are conservative native token estimates and retained reservations, not provider invoices or account credit balances.

## Frozen identities and retained evidence

- Analyst: native `openai/gpt-6-luna`; judge: native `anthropic/claude-haiku-5-5`, high effort, 8192-token cap; sandbox: SmolVM.
- Baseline analyst revision: `cb963fdefc6e5d2daf9779f6726a2c199ed195ee`, overlaid on the same current evaluator/runtime as the candidate.
- Candidate implementation commit: `b0569942267e9530f0ff77fbd80263111085dbe5`; source `1812b58dfccbd6f9`; baseline source `368cd43ab7c6df81`.
- Judge `b44929467d85`; scorer `c100f51adc12873d`; accounting `a0cc73ec381e4778`.
- Comparison policy `6fe8128a0e410aac0b46e3bac769e67ea285cb3c2470b0776d8311dfe247a0b7`.
- Baseline records fingerprint `1a4835f5d226fbaf9f18e4c8c9204f4cfc421e373d3e928baa349732b3ba5fda`.
- Candidate records fingerprint `64db657835df8b14eb9a23722f1196911cabf19e0ae81ac8e04233d32ee52d27`.

Canonical local evidence: `data/output/reliability-native-20261114/originals/recovery/`. It retains the recovery plan/script, original LangSmith trees and feedback, recovered records, per-case receipts, spending journal, `candidate-records.jsonl`, `comparison.json`, `comparison-readback.json`, `reconciliation.json` and `final-accounting.json`. The original batch files and all other frozen plans remain unchanged.

See the [campaign contract](../docs/reliability-campaign.md) for the remaining development and reserved-acceptance work.
