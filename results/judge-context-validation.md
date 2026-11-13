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
