# Native v0.0.1 reliability campaign — 2026-11-14 UTC

All **92 responses completed**, with valid evaluation and complete conservative native-estimate accounting. The frozen candidate is **rejected for release acceptance**: original regressions and development passed, but two mandatory reserved cases regressed. No score, tolerance, reference, model or completed answer was changed to obtain a pass.

| Batch | Baseline supported | Candidate supported | Frozen verdict |
| --- | ---: | ---: | --- |
| originals | 9/12 | 12/12 | accept_for_review |
| development | 15/17 | 17/17 | accept_for_review |
| reserved | 17/17 | 15/17 | reject |

| All completed responses | Baseline | Candidate |
| --- | ---: | ---: |
| Fully supported | 41/46 | 44/46 |
| Correct value or correct refusal | 44/46 | 45/46 |
| Correct answer/refusal decision | 45/46 | 45/46 |
| Reproduced evidence, answerable cases | 33/36 | 35/36 |
| Model calls including judges | 342 | 336 |
| Summed analyst latency, seconds | 1590.28 | 1663.1300000000003 |
| Estimated USD, completed responses | 1.41156375 | 1.37437675 |

The aggregate supported score improved, but it does not override a mandatory regression. These are 40 distinct cases, with six originals repeated twice per arm, plus 17 development and 17 reserved generated worlds. They are not 92 independent domains or a production-reliability estimate. Original recovery changed process boundaries, so the aggregate latency is not a clean throughput comparison. Method-judge ratings are advisory and not human-calibrated.

## What failed and what improved

- Original comparison: the candidate corrected three case/trial slots with missing delivery facts or broken cited Python; baseline 9/12 versus candidate 12/12. The missing-cost refusal passed both arms. [Original results and recovery evidence](original-regression-native-20261114.md).
- Development: baseline 15/17 versus candidate 17/17. The baseline stable-period SQL put the status label in the unit column; the unavailable-period answer acknowledged missing observations but used answered rather than cannot_answer. Both passed in the candidate.
- Reserved profit: the candidate gave the correct major-currency value, but both cited SQL outputs stayed in minor units. Runtime execution-only validation accepted it; the independent value-reproduction check correctly rejected it.
- Reserved unavailable period: the candidate acknowledged that the current-period comparison could not be computed, yet returned answered with null required metrics. The baseline correctly declined. The correct-number and refusal contract checks rejected the candidate.
- The reserved baseline passed 17/17; the candidate passed 15/17. Five metric-level regression entries refer to these two case-level failures. They remain valid measured failures, not infrastructure exclusions.

## Development and reserved LangSmith evidence

Each linked experiment contains one preselected response and its six feedback values. Both arms used native `openai/gpt-6-luna`; native `anthropic/claude-haiku-5-5` supplied advisory method assessments. The judge retained high reasoning effort and the 8192-token cap.

### Development

| Case | Baseline supported / trace | Candidate supported / trace |
| --- | --- | --- |
| delivery-causality | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/bb4e60da-3074-45ac-8efc-cfa3baccf1ff) | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/1c91caf2-05ea-4d62-bb9c-2082291b8930) |
| delivery-report | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/0f2464da-ee59-4156-a6e4-33ec70f40502) | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/e377b467-7594-4f55-b820-068e91cf0769) |
| profit-complete | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/b37228be-cea1-4a45-88e0-f6e952ea88ed) | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/b593a72e-5302-4227-9762-6987d6052998) |
| profit-missing | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/366e7b00-5da4-4a23-9c3d-fb815383029f) | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/093b536f-72aa-4d63-a432-ea6e3bcc204a) |
| profit-partial | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/8688f9e4-59e1-4710-96f1-83d2ed6f0fa8) | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/ca4e6c47-cbec-40c2-b34c-82e704e11145) |
| profit-zero | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/9d07818d-e35d-44b1-bcfb-f6515c07a190) | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/4c4746c6-5e90-430b-b3f7-9a247cba4646) |
| repeat-report | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/89050312-2f9b-4c2e-8914-785cdf10eeb1) | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/51d4b9e6-3a0d-4cd0-aab2-6cd5a9b5d780) |
| replay-duplicate-export | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/c54fc274-d2ff-46a8-b832-f9a9d419aaf2) | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/607b216d-ff15-43a7-93f4-0e2e15b8982b) |
| replay-late-observations | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/dd775030-032d-41d1-8162-16018d12ae9d) | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/d3fc1356-37a1-480b-997e-696deff3262e) |
| replay-late-observations-followup | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/2c31210a-35af-48e9-87f3-664c021735b0) | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/f573bc1b-a5dc-4740-afce-7973704bf07a) |
| replay-price-mix-only | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/b18d8b7f-c122-4898-b6db-b2482294ec54) | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/73cd8df7-0170-4d4d-97e1-1dce826f125e) |
| replay-price-shift | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/fbbfb8da-d8b5-4c87-8a67-84789837e212) | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/8cf43d49-7626-4830-85d1-cf06c014b2ed) |
| replay-shift | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/13d6481a-942b-4027-ab1c-c6cf8c3ecd93) | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/7f0e8ae8-98b3-4016-9763-6eb07103616d) |
| replay-stable | [0/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/9ffde7b3-ebc2-4197-a0f6-64f6d7d1fe83) | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/e758f8a1-5a1b-4856-842b-58b73c15544d) |
| replay-unobserved-period | [0/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/4658ca8e-758a-49fc-9910-aa8848441f30) | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/8d623838-945d-4e68-a658-2963e37b4058) |
| revenue | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/047a350d-c159-4c61-8515-c548bb90af25) | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/5bb29429-880c-40cc-9a3e-e8daaa167511) |
| revenue-duplicates | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/cbb95730-9d94-4769-a167-96991874208b) | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/6b3c7293-0518-420a-8164-6b03ae581087) |

### Reserved

| Case | Baseline supported / trace | Candidate supported / trace |
| --- | --- | --- |
| delivery-causality | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/818ef1a9-6470-4b3e-813a-1038cae1818b) | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/a8d7172a-d995-4fe5-b830-6a8efc1c16ed) |
| delivery-report | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/4d0c9838-e985-4a16-9e77-efb416a01a5d) | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/ecfd8241-e758-432d-805f-5b15e3a6da19) |
| profit-complete | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/577ae637-5057-404c-9877-9a71d54747d1) | [0/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/aad9c59d-17ad-431e-87b5-c7ffe1537c3f) |
| profit-missing | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/1508ac69-1113-4c46-9d6c-6a7cc794729a) | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/a67b37cc-7861-44f9-af75-e4adf9abd7b4) |
| profit-partial | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/aa675a13-a093-4775-a2e4-f3e43fa43978) | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/9518ca10-e4cb-4fd5-a844-6503b521ace5) |
| profit-zero | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/c7e3b509-84a4-4d0c-baef-32cb7319ac61) | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/362479bd-de5a-4a97-8a59-a736b7358435) |
| repeat-report | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/dbb4fe85-d75b-4916-8147-01463fbe20c9) | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/65891999-2b85-4dc2-9632-138ac833b7dd) |
| replay-duplicate-export | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/2a51b9ce-55ee-45d2-9955-e5fa15fe4459) | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/52940388-152b-40e4-ad09-681195a7db81) |
| replay-late-observations | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/b5930d81-d8f2-4481-8901-89c8d9de947c) | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/3a6c50bb-cf0a-443f-bb55-acc5bf0c693c) |
| replay-late-observations-followup | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/0c9aba73-b7c5-4606-bb1f-70b17e44f301) | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/4c83e067-782d-4442-a426-b92195da80f8) |
| replay-price-mix-only | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/27e87773-953a-46d9-a581-681fc8c5724b) | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/08596f62-78b3-4a48-ae9a-5dd0a8f08704) |
| replay-price-shift | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/123e68ea-d2a1-4c07-9964-610fb6b35518) | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/b710129a-309f-4a47-8285-59c7e6bf7b51) |
| replay-shift | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/256d8eb8-55a8-40c2-9b5b-1ba3b8e2aaa2) | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/db1b8603-fa85-4229-83ab-cd387c31bd2d) |
| replay-stable | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/f7601783-1aef-4409-8976-631adc65f324) | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/7342cb46-9071-495b-bcc7-57c0da87a1d6) |
| replay-unobserved-period | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/f514d8ca-99ec-4991-a572-6c12eb30adb5) | [0/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/77544ebc-76dc-41b8-a1e4-c1efe42821dd) |
| revenue | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/f09c66f3-ac93-4351-9317-ada9b77e68b3) | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/c5e7f1c7-379c-45f4-8c42-3fb7f258a97c) |
| revenue-duplicates | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/85c84162-7e84-450e-99f3-c55e7223f04f) | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/ed4c885e-95c9-4990-b8e3-11a0ee90753d) |

## Cost and retained attempts

Development used **$0.927989** across 245 calls. Reserved used **$0.87160325** across 221 calls. Each completed under its separate $1 allocation, with no unsettled usage or reservation breach. All 92 completed responses total **$2.78594050** in conservative token estimates.

Total goal usage and retained reservations is **$3.51316181225** against the existing **$5** authorization, leaving **$1.48683818775**. This includes the original interrupted attempt and retained unknown remainder as documented in the original report. Estimates are not invoices or provider balances; remaining credits do not expand authorization.

## Revision and release boundary

The numeric-evidence and unavailable-report gaps have local fixes in [PR13](https://github.com/IntelIP/BackIntel/pull/13) on `codex/numeric-evidence-completion`. They preserve independent scoring and return validation feedback through the existing structured-output repair path. The old candidate and all 92 results stay intact. The revised candidate has no live acceptance result yet.

A separate proposed comparison retains the 29 unchanged original/development baseline records under their actual source identities, runs all 46 revised candidate responses, and runs 17 baseline responses on fresh reserved worlds: 63 new responses total. The new reserved generation changes periods, amounts, report distributions and world IDs; it has 13 independently checked answerable references and four refusal cases. It remains a controlled synthetic suite, not domain-transfer evidence.

The proposed $2.15 allocation exceeds the remaining $5 envelope; an increase to $6 cumulative has been requested. The earlier zero-call proposal was superseded before execution when the second reserved failure was found. No revised paid call, merge, release or deployment follows from this report. The release qualification goal remains unfinished.

Frozen source: candidate `1812b58dfccbd6f9` at `b0569942267e9530f0ff77fbd80263111085dbe5`, baseline `368cd43ab7c6df81`, scorer `c100f51adc12873d`, judge `b44929467d85`, accounting `a0cc73ec381e4778`. [Machine-readable comparisons](reliability-native-20261114.json) preserve each policy and record fingerprint.

Local original evidence remains under `data/output/reliability-native-20261114/`: immutable plans, isolated source snapshots, per-job receipts, raw records, LangSmith run IDs and durable reserve/settle journals. The revised proposal is separate; old artifacts were not overwritten.
