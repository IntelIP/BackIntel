# Revised candidate qualification — 2026-11-14 UTC

The revised candidate passed its original and development gates, then failed one mandatory fresh reserved case. Its 46 new responses are valid and retained; 45 are fully supported. The 17 fresh baseline responses did not run, so the paired reserved comparison is incomplete and no release acceptance is claimed.

| Stage | Retained baseline | Revised candidate | Outcome |
| --- | ---: | ---: | --- |
| Original regressions, two trials | 9/12 | 12/12 | Accepted for review; three improved slots, no deterministic regression |
| Development | 15/17 | 17/17 | Accepted for review; two improved cases, no deterministic regression |
| Fresh reserved generation 2 | Not run | 16/17 | Candidate rejected; paired comparison incomplete |

The 29 reused baselines retain their actual unchanged source, data, reference, model and evaluator identities; no historical output was relabeled. This covers 75 of 92 paired response slots for this comparison. The initial [92-response campaign](reliability-native-20261114.md) remains a separate rejected experiment. Its generation-1 held-out data is different; the aggregate percentages are not a paired comparison between those generations.

## Measured outcomes

The numeric-unit and unavailable-required-metric cases passed in generation 2. The remaining failure was the stable-period report: all seven reported facts were correct, but SQL returned a numeric status value while placing the reported label in its unit column. The independent evidence check correctly failed that explicit metric/value association. The second, correct checking query did not repair the contradictory cited output. Its score remains zero; no retry was selected for a pass.

The next implementation checks explicit associations in SQL and structured Python JSON/JSON-lines output. It uses no hidden reference values and changes no frozen grading rules. That implementation is separate from the measured source below and needs new qualification with generation 3.

## LangSmith evidence

Each linked experiment contains one revised response and its six feedback values. Reused baseline experiment links remain in the initial reports.

### Originals

| Case | Trial | Supported / trace |
| --- | ---: | --- |
| olist-l1-01 | 1 | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/d1971880-b87c-4b8b-9201-0fb7856e5f56) |
| olist-l1-01 | 2 | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/843d1f69-b75e-490b-b6ab-e940a6f4e59c) |
| olist-l3-07 | 1 | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/1b0bc6d8-dec4-4f29-859c-bbe7bb7c3c55) |
| olist-l3-07 | 2 | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/6e7ebf91-e4cb-4945-811b-33171ee82706) |
| olist-l5-01 | 1 | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/e73d30c1-f9a4-4d48-8cd6-3e13a216633b) |
| olist-l5-01 | 2 | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/876cfd7e-7b17-403b-8f04-2659f503ecbc) |
| olist-l5-02 | 1 | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/263a57df-32c0-43a6-b493-bfec6b620b39) |
| olist-l5-02 | 2 | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/eb0c5260-e658-4b89-9749-ea9431e2bf17) |
| olist-l6-2018-03 | 1 | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/20144271-1dd3-4f52-8d40-c3c5d269d0e3) |
| olist-l6-2018-03 | 2 | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/f9541a18-3d31-4093-a4a0-d0d1f6aeca86) |
| olist-l6-repeat-2017-09 | 1 | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/ca7ace60-68dd-4a65-a0f0-3d8dfdbf3c91) |
| olist-l6-repeat-2017-09 | 2 | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/95821f73-4403-49d1-870d-f20c3e900b6e) |

### Development

| Case | Trial | Supported / trace |
| --- | ---: | --- |
| acceptance-v1-development-delivery-causality | 1 | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/9d2a3654-ddb0-4f24-a565-500220e4af22) |
| acceptance-v1-development-delivery-report | 1 | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/e8d07833-6eeb-4e33-88e4-6c5ebf34bc12) |
| acceptance-v1-development-profit-complete | 1 | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/b01a2f2a-253d-465f-907f-9f1089b6b346) |
| acceptance-v1-development-profit-missing | 1 | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/e92d07eb-1711-4240-9cbb-fd616ea3c9b9) |
| acceptance-v1-development-profit-partial | 1 | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/3510c21b-9ca3-4615-9292-c5ea6304078c) |
| acceptance-v1-development-profit-zero | 1 | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/9e16f798-f9e8-4dc8-949c-ef05ff8845ae) |
| acceptance-v1-development-repeat-report | 1 | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/2c5fcb37-7b26-43a8-9f67-a0ad0ced393a) |
| acceptance-v1-development-replay-duplicate-export | 1 | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/7e7e925a-1b85-4d2f-8e39-d232041bd384) |
| acceptance-v1-development-replay-late-observations | 1 | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/52b1e136-dbe1-43f1-85d7-f338c4819adf) |
| acceptance-v1-development-replay-late-observations-followup | 1 | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/e6807ae8-980a-40ad-91b2-45e6d3242077) |
| acceptance-v1-development-replay-price-mix-only | 1 | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/71c08b00-e521-4222-8232-9f9413578b73) |
| acceptance-v1-development-replay-price-shift | 1 | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/ce7c5cac-54ac-4ee9-8702-ccf9c41983e4) |
| acceptance-v1-development-replay-shift | 1 | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/4c916a1d-b22e-4b7a-a851-6ebafc971567) |
| acceptance-v1-development-replay-stable | 1 | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/45c710f6-d191-48f0-8e0d-a8763ac34009) |
| acceptance-v1-development-replay-unobserved-period | 1 | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/563252a7-f057-4dda-91d8-e846a9f8da6b) |
| acceptance-v1-development-revenue | 1 | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/75e4cdcb-b150-48de-84d0-c135f2ed2b11) |
| acceptance-v1-development-revenue-duplicates | 1 | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/95896104-8d71-4c61-bb19-9b378615ab86) |

### Reserved

| Case | Trial | Supported / trace |
| --- | ---: | --- |
| acceptance-v1-reserved-2-acceptance-delivery-causality | 1 | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/1a35363b-d1c4-493a-b2cb-18679c940a63) |
| acceptance-v1-reserved-2-acceptance-delivery-report | 1 | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/6194a5df-7aa2-4e19-8dfd-802892679c79) |
| acceptance-v1-reserved-2-acceptance-profit-complete | 1 | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/fee5d21f-89ab-459b-95f2-eb73e9eb0824) |
| acceptance-v1-reserved-2-acceptance-profit-missing | 1 | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/813c5a30-e6cc-4e0b-b646-815c1e13d4e5) |
| acceptance-v1-reserved-2-acceptance-profit-partial | 1 | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/9df0da83-58ae-4d86-a1c1-5b744c0f220c) |
| acceptance-v1-reserved-2-acceptance-profit-zero | 1 | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/a793ee35-9cc0-4245-b1d5-e6cc1d6f7aae) |
| acceptance-v1-reserved-2-acceptance-repeat-report | 1 | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/7df2523b-d183-435f-a224-8c46e4ed219c) |
| acceptance-v1-reserved-2-acceptance-replay-duplicate-export | 1 | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/cf28f9da-3448-408f-bd4b-907731b6a339) |
| acceptance-v1-reserved-2-acceptance-replay-late-observations | 1 | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/3afe7cec-f774-44b8-9a69-5ea32b42a36a) |
| acceptance-v1-reserved-2-acceptance-replay-late-observations-followup | 1 | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/81293e9b-edb8-4d45-b105-ab725d97e8cf) |
| acceptance-v1-reserved-2-acceptance-replay-price-mix-only | 1 | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/fe463e9f-58e4-46ec-8c26-bc6d078f9f92) |
| acceptance-v1-reserved-2-acceptance-replay-price-shift | 1 | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/0a2fde89-7457-432c-82f3-55de08b61e02) |
| acceptance-v1-reserved-2-acceptance-replay-shift | 1 | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/b507bc2b-3ebb-483e-b584-0c6eb0a0bfc2) |
| acceptance-v1-reserved-2-acceptance-replay-stable | 1 | [0/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/d52a79fd-9a05-4a01-89fe-628375586dab) |
| acceptance-v1-reserved-2-acceptance-replay-unobserved-period | 1 | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/71bc8345-a2bb-4818-af37-8936dfecaba4) |
| acceptance-v1-reserved-2-acceptance-revenue | 1 | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/8b7b57de-900f-4ec7-b80c-51e1907091dd) |
| acceptance-v1-reserved-2-acceptance-revenue-duplicates | 1 | [1/1](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/d8d2d0ca-6741-432d-8a77-e794e9024837) |

## Accounting and limits

New candidate usage was **$1.413655** across **353** model calls including judges: original $0.469803, development $0.45989625, fresh reserved candidate $0.48395575. Reused baseline usage is not charged again. All stage ledgers settled with no uncertainty or reservation breach.

Cumulative goal usage and retained reservations is **$4.92681681225 of $5**, leaving **$0.07318318775**. The earlier interrupted run's unknown remainder remains reserved: both provider billing panes require sign-in, so no reconciliation or release of that reservation was assumed. These are conservative estimates and reservations, not provider invoices or balances.

The original/development stages and the fresh candidate-only arm were separately admitted within the existing $5 allowance. Continuation was not treated as approval for a higher cap. The earlier $6 request is superseded by the new candidate revision: a proposed shared $2.05 follow-up allowance requires a $7 cumulative cap. No next-revision inference is authorized by this report.

## Reproducibility and release boundary

Measured candidate: `d0d476e04fc7f378` at `661646fe8842e67e6734c2eb887dc056843cbffb`; retained baseline `368cd43ab7c6df81`; scorer `c100f51adc12873d`; judge `b44929467d85`; native accounting `a0cc73ec381e4778`. Analyst: native `openai/gpt-6-luna`; advisory judge: native `anthropic/claude-haiku-5-5`, high effort, 8192-token cap. Sandbox: unchanged SmolVM profile. No human calibration, model training, merge or release is claimed.

Local evidence is retained under `data/output/reliability-native-refresh-20261114-r2/`: immutable plans and source snapshots, staged admissions, exact reused baseline records, all new answers, per-job receipts, LangSmith IDs and disk-flushed usage journals. [Machine-readable report](reliability-revision-20261114.json) retains comparison policies and fingerprints.
