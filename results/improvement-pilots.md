# BackIntel improvement pilots

Completed pilots and explicitly invalid attempts are reported separately here. Raw answers and traces remain in the ignored data directories and LangSmith. The owner waived human calibration; **all method-judge scores below are uncalibrated**.

**Known reported model charges: $0.03842068725 across 108 observed calls, including two unpriced requests. A complete dollar total is unavailable.** The completed pilots/control account for $0.02372800815; two invalid attempts add $0.01469267910 in known charges. Both completed improvement gates rejected their candidates because no previously failed case improved; the separate negative control was rejected for a deliberate correctness regression. The invalid attempts support no quality conclusion. These small runs are not full acceptance, and neither candidate was promoted.

Both provider-error runs now have LangSmith **`evaluation_valid=0` correction feedback**. Exclude runs with that feedback from capability, regression and acceptance comparisons; their original immutable traces and zero scores are preserved. Provider account reconciliation matches the known charges to rounding, while the two rejected requests remain individually unpriced.

## Runtime pilot: no regression, no demonstrated improvement

`runtime-pilot-01` compared the `cb963fd` runtime with the frozen current runtime on two original development cases, once per case per arm. Both scored **2/2 fully supported**. The previously observed evidence failure did not recur in the fresh baseline. The frozen policy returned **`reject` — “no previously failed case improved.”** There were no deterministic regressions, no improved cases and no invalid runs.

This is a completed small pilot, not full acceptance. The observation does not establish statistical significance, generalization, or a durable time/cost improvement. Reserved cases were not evaluated.

| Experiment | LangSmith | Fully supported | Model calls, including judge | Model API cost (USD) |
| --- | --- | ---: | ---: | ---: |
| Baseline | [backintel_original_regression_v1-sqlite-gpt-6-luna-L16-20261111-0311-6736f32d](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/ec19dc38-5424-47c4-b633-124636f91dcb) | 2/2 | 20 | $0.00704665665 |
| Current runtime | [backintel_original_regression_v1-sqlite-gpt-6-luna-L16-20261111-0312-09e96dca](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/d7ed273d-b4f1-4627-967e-ef6119631402) | 2/2 | 16 | $0.00597538260 |

**Total provider-reported model API cost: $0.01302203925 across 36 calls (32 analyst and 4 judge).** All reported request usage and costs were complete. The pilot used a $0.05 application allowance, $0.01 per-call reservation and an 80-call limit. These totals exclude LangSmith charges and local compute.

### Paired case scores

Each cell shows baseline → current. Deterministic scores are 0/1; the method judge is on a 0–1 scale.

| Case | Correct | Evidence reproduces | Answer/refusal decision | Fully supported | Method judge (uncalibrated) |
| --- | ---: | ---: | ---: | ---: | ---: |
| `olist-l1-01` | 1 → 1 | 1 → 1 | 1 → 1 | 1 → 1 | 0.75 → 0.75 |
| `olist-l6-repeat-2017-09` | 1 → 1 | 1 → 1 | 1 → 1 | 1 → 1 | 0.375 → 0.625 |

The first case is the ordinary delivered-order count control; the second is the September 2017 repeat-purchase report with a historical evidence failure. The count binds `sqlite:olist`; the report binds `sqlite:olist_asof_2017-09`. The count’s question and report were evaluated from the frozen scenario manifest, not from historical model answers.

The runtime report also exposed a judge limitation: it penalized the lack of an explicit SQL as-of filter even though the manifest binds an already-truncated September 2017 snapshot, and it speculated about missing joins without data-profile evidence. The judge lacks validated environment/data-profile context and may penalize valid snapshot use. Numerical correctness and evidence reproduction remain separate scores. No regrade was performed; human calibration was waived.

### Usage including evaluators

| Arm | Role | Calls | Input tokens | Output tokens | Reported cost (USD) |
| --- | --- | ---: | ---: | ---: | ---: |
| Baseline | Analyst | 18 | 122,824 | 5,579 | $0.00601091865 |
| Baseline | Judge | 2 | 4,907 | 1,111 | $0.00103573800 |
| Current runtime | Analyst | 14 | 92,933 | 4,396 | $0.00506685960 |
| Current runtime | Judge | 2 | 4,397 | 956 | $0.00090852300 |

Analyst: `openrouter/openai/gpt-6-luna`. Judge: `openrouter/anthropic/claude-haiku-5.5`. Both arms used the same evaluator and Docker sandbox. Lower observed calls, cost and analyst latency in the current arm are descriptive observations from this one run; they are not established performance gains.

### Frozen identities and evidence

| Identity | Value |
| --- | --- |
| Baseline runtime commit | `cb963fdefc6e5d2daf9779f6726a2c199ed195ee` |
| Baseline source | `645a4b51759f6fad` |
| Current source | `40cf15514d4670f7` |
| Dataset | `backintel_original_regression_v1` |
| Data fingerprint | `a4ed0a7916f7d6c64b806cf1bb2a6f29ea3adf648856955f1f74e7f9f415e318` |
| Reference fingerprint | `ff8ec2d2417b412f` |
| Scorer implementation | `74186fb62c27e2ce` |
| Judge rubric | `fca43a717d4f` |
| Plan manifest | `cd2e0718e6a0c01c795fe46eb154a39aef6c654243dba19eeda09bf21f899499` |
| Comparison policy | `3b384b1df5789822e855861fd5fcf0a4fcc6c7184402e01b29c8c539e7c9a351` |
| Runner | `63ecc2198cfd9a1dfcfc5eafb028eb45b55e9264e8b99b416529be0670880855` |

The [compact JSON summary](improvement-pilots.json) also contains method, scenario-manifest, comparison-implementation and raw-record fingerprints, per-case LangSmith run IDs, complete usage totals and source artifact paths.

Local evidence: [manifest](../data/improvement/runtime-pilot-01/manifest.json), [frozen policy](../data/improvement/runtime-pilot-01/policy.json), [comparison verdict](../data/improvement/runtime-pilot-01/comparison.json), [baseline result](../data/improvement/runtime-pilot-01/baseline-result.json), [current result](../data/improvement/runtime-pilot-01/candidate-result.json). These local raw evidence files are intentionally ignored by Git.

## Coding pilot: real proposal, no demonstrated quality improvement

`coding-pilot-01` ran a fresh baseline, one real coding-model invocation, and a fresh candidate on the complete-cost versus missing-cost development pair. The worker changed only `src/backintel/agent_files/lead.md`, adding general data-sufficiency and stopping guidance. It received the sanitized brief and allowlisted prompt text, with no tools, shell or filesystem access. The orchestrating agent inspected the proposal and found no case answers or permission expansion; the change remains isolated and unpromoted.

Both baseline and candidate scored **2/2 fully supported**: they answered the complete-data case and declined the missing-cost case. There were no deterministic regressions, improvements or invalid runs. The frozen policy returned **`reject` — “no previously failed case improved.”** This demonstrates that the proposal/evaluation loop executed, not that it improved answer quality.

| Experiment | LangSmith | Fully supported | Calls including judge | Model API cost (USD) |
| --- | --- | ---: | ---: | ---: |
| Baseline | [backintel_acceptance_v1_development-sqlite-gpt-6-luna-L3-20261111-0314-3d87b867](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/8ca2c495-b768-4062-8f14-277640fa02ee) | 2/2 | 16 | $0.00539125290 |
| Worker candidate | [backintel_acceptance_v1_development-sqlite-gpt-6-luna-L3-20261111-0316-a5045a16](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/e8110d2b-7e5b-41fb-abe9-b7c154ad7df9) | 2/2 | 12 | $0.00423796725 |

**Coding-cycle total: $0.01039639590 across 29 calls**, including the worker’s **$0.00076717575** single call. All reported costs and usage were complete. The invocation had a $0.04 allowance, $0.01 reservation and an 80-call limit.

### Paired coding-pilot scores

| Case | Correct | Evidence reproduces | Answer/refusal decision | Fully supported | Method judge (uncalibrated) |
| --- | ---: | ---: | ---: | ---: | ---: |
| `acceptance-v1-development-profit-complete` | 1 → 1 | 1 → 1 | 1 → 1 | 1 → 1 | 0.5 → 0.875 |
| `acceptance-v1-development-profit-missing` | 1 → 1 | N/A → N/A | 1 → 1 | 1 → 1 | 0.833 → 0.833 |

Evidence reproduction is not applicable to the correct refusal. Method scores are uncalibrated and were not an improvement gate. Lower observed calls, latency and cost are single-run observations; they do not establish significance or general improvement. Reserved cases were not evaluated.

### Coding-cycle usage

| Arm | Role | Calls | Input tokens | Output tokens | Reported cost (USD) |
| --- | --- | ---: | ---: | ---: | ---: |
| Baseline | Analyst | 14 | 76,369 | 4,041 | $0.00434848590 |
| Baseline | Judge | 2 | 3,643 | 1,378 | $0.00104276700 |
| Worker candidate | Analyst | 10 | 52,881 | 2,895 | $0.00341349525 |
| Worker candidate | Judge | 2 | 3,748 | 916 | $0.00082447200 |
| Proposal | Coding worker | 1 | 1,164 | 1,259 | $0.00076717575 |

The analyst and worker used `openrouter/openai/gpt-6-luna`; the judge used `openrouter/anthropic/claude-haiku-5.5`. The worker candidate began as the old baseline runtime; it is distinct from the human-developed current runtime in the first pilot.

### Coding-pilot identities

| Identity | Value |
| --- | --- |
| Baseline source | `645a4b51759f6fad` |
| Worker candidate source | `fa6196e1a67c4996` |
| Dataset | `backintel_acceptance_v1_development` |
| Data fingerprint | `0b65012dc6217c5a77b8e8b5f64f84b6ebd53b3a85e7cd73faa17da7bc60c741` |
| Reference fingerprint | `ed3e5f6f1b001583` |
| Scorer implementation | `74186fb62c27e2ce` |
| Plan manifest | `c14d15cad09a52da7961eb0d95efd7b5a36d8589e8d7296d078dfdb6580c6d94` |
| Comparison policy | `3ca3c821e331ff56074cab707e3fec0d06fb4f4f82e1844382e9af54b0db47fe` |

The [JSON summary](improvement-pilots.json) records worker input/base/proposal hashes, changed-file identity, method versions, per-case run IDs and full model usage. Raw model answers and replacement text remain in ignored data artifacts.

Local evidence: [manifest](../data/improvement/coding-pilot-01/manifest.json), [comparison](../data/improvement/coding-pilot-01/comparison.json), [worker result](../data/improvement/coding-pilot-01/worker-result.json), [proposal](../data/improvement/coding-pilot-01/worker/cycle-results/proposal.json), [baseline result](../data/improvement/coding-pilot-01/baseline-result.json), [candidate result](../data/improvement/coding-pilot-01/candidate-result.json).

## Controlled rejection demo: mandatory correctness failure rejected

`rejection-demo-01` is a **controlled-negative-fixture**, not an analyst-model response. A deterministic target deliberately returned a zero count with reproducible evidence. It reused the compatible passing count baseline unchanged and ran one real method-judge call through LangSmith. The gate returned **`reject`** because mandatory correctness and full support regressed. This demonstrates the rejection path; it is not evidence that an LLM regressed.

Experiment: [backintel_original_regression_v1-sqlite-wrong-zero-no-analyst-model-L1-20261111-0321-9ab101f4](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/559b4ac4-e0e9-4a95-936c-8408023d82c1).

| Case | Correct | Evidence reproduces | Answer/refusal decision | Fully supported | Method judge (uncalibrated) |
| --- | ---: | ---: | ---: | ---: | ---: |
| `olist-l1-01`, reused baseline → controlled target | 1 → 0 | 1 → 1 | 1 → 1 | 1 → 0 | 0.75 → 0.125 |

**New spend: $0.000309573, one judge call, zero analyst calls.** The judge used 1,412 input tokens and 343 output tokens; usage and cost were complete. The previously reported baseline cost of $0.0019752381 and its eight model calls are excluded from this demo’s new spend, because they are already counted in `runtime-pilot-01`. The invocation had a $0.005 allowance and reservation and a one-call limit.

| Identity | Value |
| --- | --- |
| Scorer implementation | `74186fb62c27e2ce` |
| Policy | `b2b1f1bb162340ff12e851ac439d2630f065d454063ea8a478fd5faaf281b230` |
| Control source | `120bd957195dbafd724f6fcef66ce66803f572edb2e7d7f34c4f833f97925840` |
| Baseline record | `eee6d125d6a938f2746b30c3e992c42869dce2c8fdd3f9138c3beeaed844d1c4` |
| Candidate records | `44648b86c366c876919e0116aa08f7c9ec4c58f2499030c209a8ea0910d4a84e` |

Local evidence: [execution result](../data/improvement/rejection-demo-01/execution-result.json), [manifest](../data/improvement/rejection-demo-01/manifest.json), [frozen policy](../data/improvement/rejection-demo-01/policy.json), [comparison](../data/improvement/rejection-demo-01/comparison.json), [control source](../data/improvement/rejection-demo-01/control-source.py). The JSON summary keeps controlled demos separate from the model-development pilots and records the reused baseline and control hashes.

## Invalid runtime attempt: provider credit rejection

`runtime-failures-01` attempted the original missing-cost case and March 2018 delivery report. The fresh baseline completed both cases successfully; the current runtime completed the missing-cost case, then the provider rejected the March request with **402 / `payment_required`**. The candidate stage was invalid and the comparison did not run. **No capability, improvement or regression conclusion can be drawn from this batch.**

| Arm | LangSmith | Observed status | Known reported cost (USD) |
| --- | --- | --- | ---: |
| Baseline | [backintel_original_regression_v1-sqlite-gpt-6-luna-L36-20261111-0320-4d889702](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/648f3079-aff6-416b-beaa-3df7024ec399) | Two valid passing cases | $0.00633890565 |
| Current runtime | [backintel_original_regression_v1-sqlite-gpt-6-luna-L36-20261111-0322-4128a2a8](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/7899f3fe-16c3-4ce2-a308-d57ca8910208) | One valid passing case; one invalid provider request | $0.00143985600 |

**Known batch charges: $0.00777876165; total cost incomplete.** There were 25 observed model calls, including one unpriced analyst request. No paid judge call was made for that failed request. Its unknown charge is not treated as zero. The invocation had a $0.025 allowance, a $0.005 reservation and an 80-call limit.

The frozen runner initially misclassified the provider envelope because LangChain raised it as a plain `ValueError`. Its raw March row therefore says `failure_class=agent`, `evaluation_status=valid` and zero quality scores. Those raw scores are **not model-capability evidence**. The accounting fields correctly remained incomplete and stopped comparison. The original raw records and frozen snapshots are preserved unchanged.

The source classifier now recognizes the observed structured 402/payment-required envelope as infrastructure failure, skips the judge and returns null quality grades; ordinary `ValueError` remains an agent failure. This changes the source/scorer identity for future runs. The old batch is documented as invalid, not silently rescored.

| Case | Baseline | Current runtime |
| --- | --- | --- |
| `olist-l3-07` | Valid correct refusal | Valid correct refusal |
| `olist-l6-2018-03` | Valid, fully supported report | Invalid provider credit rejection; no quality grade |

| Arm | Role | Observed calls | Reported input tokens | Reported output tokens | Known cost (USD) | Unpriced calls |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Baseline | Analyst | 16 | 106,978 | 5,046 | $0.00537147765 | 0 |
| Baseline | Judge | 2 | 4,547 | 1,045 | $0.00096742800 | 0 |
| Current runtime | Analyst | 6 | 28,706 | 727 | $0.00114602400 | 1 |
| Current runtime | Judge | 1 | 1,188 | 356 | $0.00029383200 | 0 |

Frozen plan: `0e5474be2cdfb810c3e10b28a17cc0e0a4c0fbe2a01b03d27e4277b7f8c4cb59`. Policy: `072866d1d7a545a3e8ab0a923b6c7831dc90e6cb33a14653943d768d64364a39`. The executed scorer was `74186fb62c27e2ce`; the classification fix is for subsequent evaluations and does not change those historical identities.

Local evidence: [manifest](../data/improvement/runtime-failures-01/manifest.json), [baseline result](../data/improvement/runtime-failures-01/baseline-result.json), [invalid candidate result](../data/improvement/runtime-failures-01/candidate-result.json), [retained unknown-charge accounting](../data/improvement/runtime-failures-01/allowance-after-candidate.json). The JSON summary preserves the initial misclassification alongside the infrastructure assessment.

## Invalid report retry: upstream credit failure

`runtime-report-retry-01` retried the March 2018 report with a fresh baseline and current-runtime snapshot. The baseline passed. The candidate made progress but then received **502 / `provider_unavailable`**, with a provider message stating that upstream credits were exhausted. The candidate stage was invalid and comparison did not run. This is an infrastructure failure, not evidence of a quality regression.

| Arm | LangSmith | Observed status | Known reported cost (USD) |
| --- | --- | --- | ---: |
| Baseline | [backintel_original_regression_v1-sqlite-gpt-6-luna-L6-20261111-0327-73274f3c](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/424c5bb1-7534-4f7d-bafd-be898e1a3d72) | One valid fully supported report | $0.00446291505 |
| Current runtime | [backintel_original_regression_v1-sqlite-gpt-6-luna-L6-20261111-0328-9d194d5d](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/1479dbd9-aee9-4878-a0e1-fe3681bb7143) | Invalid provider failure; one request unpriced | $0.00245100240 |

**Known retry charges: $0.00691391745 across 17 observed calls; total cost incomplete.** One analyst request has no reported price. No judge call was made for the failed candidate answer. The invocation had a $0.02 allowance, $0.005 reservation and a 60-call limit.

The prior narrow classifier handled 402/payment-required errors but missed this 502/provider-unavailable envelope. The retained raw candidate row again says `agent`, `valid` and zero scores; those scores are excluded from capability interpretation. The incomplete-cost guard still stopped comparison. Raw records and frozen snapshots remain unchanged.

The classifier now recognizes the structured provider-error contract: a `ValueError` carrying a dictionary with a string message, an integer HTTP error code from 400 to 599, and a nonempty `metadata.error_type` string. Such failures produce infrastructure-invalid records with null grades and no judge; ordinary `ValueError` remains an agent failure. Both observed envelopes are covered by focused offline regression tests. **No further paid retries should run until funding/upstream credit is available.**

| Arm | Role | Observed calls | Reported input tokens | Reported output tokens | Known cost (USD) | Unpriced calls |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Baseline | Analyst | 10 | 74,001 | 4,480 | $0.00385703505 | 0 |
| Baseline | Judge | 1 | 3,210 | 582 | $0.00060588000 | 0 |
| Current runtime | Analyst | 6 | 32,243 | 2,339 | $0.00245100240 | 1 |
| Current runtime | Judge | 0 | 0 | 0 | $0.00000000000 | 0 |

Executed scorer: `c686b7f4cf1e0b67`. Frozen plan: `4a056d3049183ccaad7d106ab3c5a1f10bf758738902425b0694c974a6bdf5d6`. Policy: `fbfe5878973de5a4b8a17458d4b11cd4fe56ba9089afaff3215e0a40c827d8f3`. The broader error-classification fix has a new scorer identity and does not rewrite these historical identities.

Local evidence: [manifest](../data/improvement/runtime-report-retry-01/manifest.json), [baseline result](../data/improvement/runtime-report-retry-01/baseline-result.json), [invalid candidate result](../data/improvement/runtime-report-retry-01/candidate-result.json), [unknown-charge accounting](../data/improvement/runtime-report-retry-01/allowance-after-candidate.json).

## Provider reconciliation and validity corrections

The read-only provider account observations reconcile the aggregate balance movement with the recorded known charges:

| Observation | Initial | Latest |
| --- | ---: | ---: |
| Total purchased credits (USD) | $395.000000000 | $395.000000000 |
| Provider-reported cumulative usage (USD) | $394.938511806 | $394.976932453 |
| Available credit (USD) | $0.061488194 | $0.023067547 |

Credit decreased by **$0.038420647**, versus **$0.03842068725** in known reported model charges: a difference of **$0.00000004025** (about 4.0 × 10⁻⁸ dollars). The aggregate movement matches to rounding; no unexplained debit was observed. Individual usage remains missing for the two rejected requests, so **request-level cost completeness remains false**.

The latest key metadata reports no configured limit and `byok_usage_daily=0`. These provider errors do not establish that the owner’s personal OpenAI key needs funding. Further paid retries depend on resolution of the provider/upstream-credit condition.

| Invalid attempt | LangSmith run ID | Correction feedback ID | `evaluation_valid` |
| --- | --- | --- | ---: |
| `runtime-failures-01` | `01a1c8a1-0663-7a96-bf81-3ad4529872a9` | `dc28aff9-b9f7-5939-bd75-62fe41232ab0` | 0 |
| `runtime-report-retry-01` | `01a1c8a6-1e98-744e-a668-e99abbadedb6` | `d71465ba-73ab-51db-b0f6-0ce4cae49d5f` | 0 |

Exclude these two runs when interpreting quality or acceptance scores. The correction is additional validity feedback; it preserves the original completed traces and their recorded zero scores rather than rewriting history. The receipt files are [runtime-failures correction](../data/improvement/runtime-failures-01/provider-error-annotation.json) and [report-retry correction](../data/improvement/runtime-report-retry-01/provider-error-annotation.json).
