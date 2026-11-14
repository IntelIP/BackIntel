# Method-judge context and caveat validation

These are authored evaluator controls, not analyst-model accuracy estimates or human
calibration. Each case was judged once per evaluator. Original feedback and failed attempts
remain unchanged. The evaluator never received private numerical reference answers.

## Context validation — 2026-11-13 05:15 UTC

PR #8 at `029da01995c259bf10a6bea2171aed0eb64eb959` was compared with the judge from
`51846a48e52e203eabefd7354182a1bd49ba72b6`. Both used
`openrouter/anthropic/claude-haiku-5.5`, Anthropic-only routing, no fallback and no SDK retries.

| Control | Expected method score | Previous evaluator | Context evaluator |
| --- | ---: | ---: | ---: |
| Valid pre-truncated snapshot | 1 | 0.5 | 1 |
| Actual future observations included | 0 | 0.5 | 0 |
| Mathematically equivalent calculation | 1 | 0.5 | 1 |
| Flat source requiring no join | 1 | 1 | 1 |

The context evaluator matched all four method expectations, versus one previously.
Its caveat rating remained 0.5 on all three valid controls, including demands for small-sample
or unverified-cutoff warnings that were not material to the bounded questions.

Eight calls cost $0.004787244 with complete provider accounting. LangSmith read-back
verified eight runs and 16 feedback records.
[Baseline](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/803f70fc-6730-4369-9b3b-9aeb7ba0643f)
and [context evaluator](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/b57ef9bd-932e-4280-afb7-40e3dcb9fcd2).
Judge versions: `fca43a717d4f` and `2f4c4a230fb7`; context `dd44858434c4`.
Raw plan, controls, answers, runner and receipt:
`data/output/judge-validation-pr8-20261113T051402Z/` in the canonical developer checkout.

## Caveat prompt experiment — 2026-11-13 18:16 UTC

A separately frozen prompt revision (`b636a99bf3e3`) tied caveats to demonstrated material
limitations and explicitly rejected irrelevant small-sample/cutoff penalties. It retained
the original four controls and added a pending-delivery disclosure pair. The six-call plan
had a $0.008 cap, $0.002 call reservation, 2048 output-token cap and no retry/fallback.

| Control | Frozen caveat expectation | Observed caveat score | Finding |
| --- | ---: | ---: | --- |
| Pre-truncated snapshot | 1 | 0.5 | Reason says no material omission, but rating still deducts |
| Future-data leakage | 0 | 0 | Correctly identifies the material undisclosed cutoff violation |
| Equivalent calculation | 1 | 1 | Accepts disclosed cohort scope |
| Flat extract total | 1 | 1 | No irrelevant snapshot caveat required |
| Pending deliveries, explanation omitted | 0 | 0.5 | Frozen expected label is ambiguous: text/method already partly scopes the answer |
| Pending deliveries, limitation disclosed | 1 | Not graded | Provider HTTP 402; no usage or charge returned |

All four original method scores remained at their expected values. The pre-truncated
reason/rating mismatch is a real evaluator defect. The pending-omitted answer says
"among delivered" and its method excludes nulls; partial credit is defensible under the
rubric. That expectation remains preserved as frozen, with this qualification rather than
a post-hoc score or label overwrite. A future unambiguous zero control should explicitly
claim that the observed mean measures eventual delivery for all purchases.

Five judgments completed; the sixth was infrastructure-invalid and paid execution stopped.
Known charges were **$0.003763881**; one request's charge is unknown, so total accounting
is incomplete. The read-only account check returned $0.007308928 remaining. This positive
balance does not negate the observed billing rejection or establish readiness for the full
campaign. LangSmith read-back verified six outputs and 12 feedback records.
[Experiment](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/43cd1f76-f059-4d01-9437-7dbc59b1e59e).
Evidence: `data/output/judge-caveat-validation-20261113/`; frozen cases SHA-256
`dc3f8acfd73ecc2f5a1233b9b087005140799fc60cecceacb47898a163e8c56e`.

## Prospective categorical candidate

The next evaluator (`94a36eb150da`) removes the separate numeric choice for caveats.
The model supplies a reason and one verdict; a fixed mapping determines the criterion score:

| Verdict | Score |
| --- | ---: |
| `none_established` | 1 |
| `adequately_disclosed` | 1 |
| `materially_incomplete` | 0.5 |
| `omitted_or_denied` | 0 |

Missing/unknown verdicts fail rather than defaulting to a favorable score. Other criteria
and refusal scoring keep their numeric contracts. The original verdict and reason are
retained in local records and LangSmith feedback metadata. Numerical/reference scores
and all historical feedback remain unchanged.

Offline checks cover all mappings, invalid verdict rejection, unchanged other/refusal
scores and preservation through the harness. The candidate suite passed 167 tests with
14 optional skips; Ruff lint/format and Vulture passed. Source identity `2ccaa2f068afb33b`;
scorer `ba972f36ad0d9f1c`. These are working-source identities, not a new published commit.

**This candidate has not passed live validation.** A categorical schema removes one redundant
rating decision but cannot guarantee semantic agreement between verdict and reason. Funded
live controls and the fresh paired analyst campaign remain necessary. No release or broad
reliability claim follows from these checks.

## Native categorical validation — 2026-11-13 23:32 UTC

The unchanged six controls were executed through native Anthropic
`anthropic/claude-haiku-5-5`, standard service, with judge `94a36eb150da` and source
context `dd44858434c4`. This prospective run retained the already-declared partial-credit
expectation for the partly scoped pending-order answer; earlier labels were not changed.
Cases SHA-256: `cb2630cf80f88f91a044cf75ccf36c4ef929b30e5d6a2d30deb33c3048dd0560`.

| Control | Frozen caveat expectation | Observed caveat score |
| --- | ---: | ---: |
| Pre-truncated complete extract | 1 | 0.5 |
| Future-data leakage | 0 | 0 |
| Equivalent calculation | 1 | 1 |
| Flat extract total | 1 | 1 |
| Pending deliveries, partly scoped answer | 0.5 | 0 |
| Pending deliveries, limitation disclosed | 1 | 1 |

All four targeted method controls matched. Overall **four of six** controls met every
frozen expectation. The pre-truncated case was incorrectly penalized for small row count
as though the answer claimed representativeness beyond the supplied extract. The pending
case was described as wholly omitted despite its partial scope statement. These are
retained evaluator failures, not analyst failures or grounds for retrospective relabeling.
The candidate is not qualified; the 92-response campaign remains held.

All six requests completed with complete conservative native token accounting, no retries
and no reservation breach. Estimated usage was **$0.028152** within the $0.12 admission
limit. This estimate is not an invoice amount; `cost_usd` remains null. Accounting version:
`a0cc73ec381e4778`. LangSmith read-back matched all six output records and twelve feedback
values. [Native experiment](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/e2832945-3a35-43b1-b445-44f7b6f7c80a).

Plan, exact controls/source copies, script, full assessments, usage and read-back remain
at `data/output/judge-native-validation-20261113/` in the canonical checkout. The working
source identity was `ac5cb1b7de4701b1` (PR8 plus native adapter/accounting integration).
No human calibration, broad accuracy or release claim follows from this six-case check.

## Native JSON-output contrast — 2026-11-13

A prospective transport-only revision (`f3b3a2c216f8`) replaced native Anthropic's
forced-tool structured output with JSON-schema output, allowing its default adaptive
thinking. The rubric, labels, six case bytes, model, default effort, rates, 2048-token
output cap and six-call allowance remained fixed. Incomplete native responses are rejected
even when their JSON can be repaired. See [transport rationale](../docs/judge-native-output.md).

All six requests completed. **Five of six** matched every frozen expectation, compared
with four of six through forced-tool output. The complete pre-truncated extract now
received full caveat credit; future leakage still failed correctly; equivalent calculations,
flat extract totals and explicit pending-order disclosure retained their expected grades.
The partly scoped pending-order answer still received 0 rather than the frozen 0.5.
Its reason notes the unanswered request to explain pending orders, but does not credit the
already-stated delivered-only population. This remaining partial-credit boundary is not
resolved. No label is changed and no 6/6 qualification is claimed; the full campaign remains
unstarted. One run per configuration cannot establish a general improvement rate or causality.

Estimated native usage was **$0.0329345**, with complete token accounting and no reservation
breach. Actual invoice amount remains unknown. Combined new native adapter/control checks
cost an estimated **$0.06112375** across 13 calls. Historical reported charges and unpriced
reservations are preserved separately. No further retries were made to seek a favorable grade.

LangSmith read-back matched six runs and twelve feedback values.
[JSON-output experiment](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/05be35c5-121a-4c1f-92a7-a83579608965).
Plan, source copies, complete assessments and receipts are retained under
`data/output/judge-native-jsonschema-validation-20261113/` in the canonical checkout.
Source `f3ea32af0037c625`; scorer `47ceaa277246ba19`; context `dd44858434c4`;
accounting `a0cc73ec381e4778`. The unchanged working-source suite passed 252 tests with
15 optional skips; lint, formatting, Vulture and diff checks passed.

## Partial-disclosure clarification — 2026-11-13

Judge `dbeb94634692` explicitly credited a relevant scope acknowledgment in the answer's
text or method even when its caveats list was empty. It distinguished that partial
disclosure from a raw query filter, generic boilerplate and a false broader-population
claim. All six prior cases and expectations remained unchanged. Four prospectively
authored sensor-coverage contrasts added partial disclosure, complete explanation,
explicit denial and boilerplate controls; these are public evaluator fixtures in
`benchmarks/judge/caveat-disclosure-controls.json`, not analyst training examples.

The clarification alone matched **8/10** controls: 5/6 original and 3/4 new. Both the
pending-delivery and sensor partial-disclosure answers still received zero instead of
0.5. The other eight controls passed. This cross-domain failure supports a problem with
the partial-credit boundary; the change alone is not a qualified fix.

All ten requests completed, costing **$0.0509685** in conservative native usage estimates,
with no accounting uncertainty or reservation breach. LangSmith read-back verified ten
outputs and twenty feedback records. [Clarification experiment](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/9b1ea8e2-785e-402a-83a6-79f8d0d871ab).
The frozen cases hash is `677ff5bffdee37934b9133b182a9b0f6612e973df2b7effcdfbb89cc1f644277`;
source `5b0bec7a68bb6dc8`. Plans, exact cases, source copies and raw results are retained
in `data/output/judge-disclosure-validation-20261113/` in the canonical checkout. No
historical expectation or result was overwritten.

## High effort at the prior token limit — 2026-11-14 UTC

The same ten controls ran once with native Haiku's effort explicitly set to `high`.
The partial-disclosure rubric, model, source context, expected grades and 2048-token
limit stayed fixed. Both partial-disclosure cases now received 0.5 with reasons that
identified the scope acknowledgment and missing consequence. All nine completed
assessments matched; the equivalent-calculation response exhausted 2048 output tokens
and was rejected as invalid rather than repaired or assigned a score. Therefore this
configuration did **not** pass the full ten-control gate.

Estimated usage was **$0.068746**, including the truncated call, with complete token
accounting and no reservation breach. LangSmith read-back matched ten outputs and twenty
feedback records. [High-effort experiment](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/b1d0781d-ed0d-423a-81e2-197b8feaa229).
Evidence: `data/output/judge-high-effort-validation-20261114/`; effective source
`1812b58dfccbd6f9`. The next configuration uses the benchmark factory's existing
8192-token limit, leaving room for thinking plus the JSON assessment. It retains all
cases and expectations and gets a fresh bounded plan; this is not a retry of unchanged
configuration or a retrospective repair of the truncated result.

## Benchmark-configuration validation — 2026-11-14 UTC

Judge `b44929467d85` passed **10/10** frozen controls with native Haiku 5.5 at high
effort and the benchmark's existing 8192-token output allowance. All responses completed
and all frozen expected criteria matched. The original six cases passed 6/6; the four
new sensor-coverage contrasts passed 4/4. Reasons credit the stated subset on both partial
answers while identifying the unexplained consequence. Full disclosure receives one;
false generalization, boilerplate and future-data leakage still receive zero.

Only the output-token allowance changed from the immediately preceding test. The
equivalent-calculation response used 2120 output tokens and completed. The truncated
2048-token result remains invalid in its original experiment. No expected grades,
numerical references, analyst code or scoring tolerances were altered.

All ten calls had complete conservative token accounting, zero retries and no reservation
breach. Estimated usage was **$0.068076**. LangSmith read-back verified ten identical
outputs and twenty feedback records. [Passing experiment](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/37a4b33b-7b2c-4fe8-93f1-1585356b9b33).
Evidence: `data/output/judge-benchmark-config-validation-20261114/`; cases hash remains
`677ff5bffdee37934b9133b182a9b0f6612e973df2b7effcdfbb89cc1f644277`; source
`1812b58dfccbd6f9`; scorer `c100f51adc12873d`; context `dd44858434c4`; accounting
`a0cc73ec381e4778`.

The working source passed all 252 local tests with 15 optional skips, lint, formatting,
Vulture, whitespace and Gitleaks checks. This passes the targeted evaluator gate for the
fresh paired campaign. It is not broad judge accuracy, human calibration or an analyst
release result. Human calibration remains waived; method scores remain advisory.

This fix's three prospective runs used **$0.1877905** in estimated native usage. All
native adapter/control checks now total **$0.24891425** across 43 calls. Historical
reported goal charges of $0.04697181225 and $0.012 retained unknown-call reservations
remain separate. Conservatively accounting for all three leaves $4.69211393775 of the
original $5 authorization before campaign allocation; this is not an account balance
or an invoice reconciliation. The campaign may allocate $1 to each of its three batches.
