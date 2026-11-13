# Native API credits

The owner requested native OpenAI and Anthropic API routing on 2026-11-13 to use
the API credits on those accounts. This is a provider change for future runs, not
a change to historical experiment records or permission to spend the entire balance.

| Role | Default route | Credential |
| --- | --- | --- |
| Benchmark analyst (`ask`, benchmark harness) | `openai/gpt-6-luna` | `OPENAI_API_KEY` |
| Optional improvement coding worker | Configured analyst model, unless explicitly overridden | Same native key by default |
| Method judge | `anthropic/claude-haiku-5-5` | `ANTHROPIC_API_KEY` |
| Report specialist (`analyze`) | `chatgpt-plan/gpt-6.1-sol`, medium reasoning | Existing BackIntel OAuth cache |

The native routes explicitly target `api.openai.com` and `api.anthropic.com`.
Anthropic uses the installed `langchain-anthropic` integration and native Messages
API, including structured output. It does not pass through the OpenAI compatibility
layer. Both routes honor completion-token, timeout and retry limits. Missing native
credentials fail visibly; there is no fallback to OpenRouter or the plan connection.
OpenRouter remains an explicit route for reproducing historical comparisons.

## Account setup

Use Doppler project `backintel`, configuration `dev`. Store the two native keys
there, never in source, `.env`, chat or a VM mount. A browser sign-in alone does not
configure an API key. The key must belong to the organization that receives the
credit grant; a key from a different organization does not inherit that benefit.

Optional selectors are `OPENAI_ORG_ID`, `OPENAI_PROJECT_ID`, and
`ANTHROPIC_WORKSPACE_ID` (required for some Anthropic account-scoped keys).
Reuse existing keys when available. Verify with each provider's read-only model
catalog before inference, including access to the exact model IDs above.

Once credentials are verified, set the existing Doppler model overrides to:

```text
BACKINTEL_MODEL=openai/gpt-6-luna
BACKINTEL_JUDGE_MODEL=anthropic/claude-haiku-5-5
```

Explicit environment values take precedence over built-in defaults. Changing the
code alone does not override an existing OpenRouter selection in Doppler.

## Accounting and experiments

Provider credits, gross API usage and cash paid are different quantities. A credit
benefit confirmation is not proof of the current remaining balance. Native responses
provide token counts, not the account's net dollar debit after credits.

The usage tracker preserves native input/output tokens and reports unknown `cost_usd`
with `cost_complete=false`. `NativeRunBudget` separately admits calls against a
**conservative usage-cost estimate**, with `estimated_cost_usd`, `estimate_complete`
and an accounting version. It never relabels that estimate as an invoice or a credit
balance. Native budgets always report `unknown_charge=true`; continuation instead
requires complete estimated accounting (`accounting_uncertain=false`). The original
`RunBudget` still requires provider-reported charges for OpenRouter.

The qualified policy is frozen from official standard-service prices on **2026-11-13**:

| Native model | Input per million tokens | Output per million tokens |
| --- | ---: | ---: |
| `openai/gpt-6-luna` | $0.50 | $0.75 |
| `anthropic/claude-haiku-5-5` | $1.00 | $2.50 |

These deliberately use each model's highest standard long-context cache-write input
rate and long-context output rate for every request. They overestimate ordinary short
prompts and cache hits. All cached input and all output, including reasoning tokens,
are included exactly once; discounts and credits are excluded. Each call rounds up
to one billionth of a dollar. The policy, source URLs and model limits live in
`src/backintel/bench/native_costs.py`; its hash is frozen into comparison plans.

The native factory pins OpenAI `service_tier=default` and Anthropic
`service_tier=standard_only` at their global endpoints. This policy covers these two
model IDs and dated snapshots, text and local tools, up to their declared context and
output limits. Unknown models, missing or inconsistent token counts, audio usage,
unexpected service tiers and Anthropic paid server-tool requests cannot settle an
estimate. An unsuccessful or unaccounted request retains its reservation and stops
later calls. Per-call reservation overruns also stop continuation. These remain
application admission limits, not provider-enforced billing caps.

Prepare a fresh improvement campaign with native routes in both arms. Preparation
locks the accounting basis and policy hash; execution and comparison reject changed
or incomplete accounting. Mixed OpenRouter/native campaigns are rejected. The old
OpenRouter dollar-complete campaign cannot be resumed by swapping keys/model IDs.
Keep historical manifests, reported charges and unpriced-call reservations unchanged.

Retain the original **$5 combined reliability allowance** across analyst, worker and
judge calls, subtracting historical reported usage and outstanding reservations before
setting the new run's `--max-cost-usd`. Revalidate the judge through the native adapter
before the 92-response campaign. Available account credit does not increase that
allowance. SDK mock tests establish adapter/accounting behavior; they do not establish
live judge quality or actual account billing.

## References

- [OpenAI API credits for ChatGPT subscribers](https://developers.openai.com/api/docs/guides/chatgpt-api-credits)
- [Anthropic Haiku 5.5 and API credit announcement](https://www.anthropic.com/claude-haiku-5-5)
- [Native Haiku 5.5 model ID](https://platform.claude.com/docs/en/models/overview)
- [LangChain ChatAnthropic integration](https://docs.langchain.com/oss/python/integrations/chat/anthropic)
- [Anthropic OpenAI compatibility limitations](https://platform.claude.com/docs/en/cli-sdks-libraries/libraries/openai-sdk)
- [OpenAI native prices](https://developers.openai.com/api/docs/pricing)
- [Luna long-context rates and limits](https://developers.openai.com/api/docs/models/gpt-6-luna)
- [Haiku 5.5 prices and limits](https://platform.claude.com/docs/en/models/haiku-5-5/overview)

The integration reuses the already locked LangChain/Anthropic packages, with
`langchain-anthropic` now declared as a direct dependency. This preserves the
selected OpenAI/Anthropic model families and uses their own endpoints.

## Live adapter evidence — 2026-11-13

Native Anthropic completed six authored evaluator controls with complete token estimates
and no budget uncertainty or reservation breach. Conservative usage estimate: **$0.028152**.
The judge matched only four of six frozen criteria, so this proves the native transport
and accounting path, not judge reliability. The larger campaign remains held pending that
separate quality issue. [Retained LangSmith experiment](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/e2832945-3a35-43b1-b445-44f7b6f7c80a).

Native OpenAI then completed one structured-output adapter smoke with 55 input and 13
output tokens. Its conservative estimate was **$0.00003725**. This was a transport check,
not an analytical question. Combined new estimates: **$0.02818925**. Actual invoice
amounts and remaining credit balances are unknown. Evidence is retained in the canonical
checkout under `data/output/judge-native-validation-20261113/` and
`data/output/native-openai-smoke-20261113/`; accounting version `a0cc73ec381e4778`.

The native-only working tree passed 232 tests with 15 optional skips. Integration with
current main and the PR8 evaluator passed 247 tests with 15 optional skips, Ruff lint and
format, Vulture and whitespace checks. The six-call trial used the same model-factory,
usage-tracker and native-accounting bytes. Shared Doppler selectors have not been changed;
activate native routes only after the native-capable implementation is adopted.
