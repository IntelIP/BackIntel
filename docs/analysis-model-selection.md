# Analytical specialist model and prompt selection

Research date: 2026-11-11. This document separates current configuration, official vendor
claims, local adapter checks, engineering hypotheses and the subsequent controlled live evaluation.

## Decision and current evidence

The owner subsequently approved **GPT-6.1 Sol as the default specialist model**. The analysis
CLI now defaults to `chatgpt-plan/gpt-6.1-sol` with medium reasoning. An explicit `--model`
overrides `BACKINTEL_ANALYSIS_MODEL`, which overrides the built-in default. This is a manual
owner decision after the live comparison; the benchmark itself does not promote models.

Build one bounded analysis-and-visualization specialist configuration with an explicit model
and reasoning setting. Keep the existing analyst's configuration unchanged. Do not activate
automatic runtime delegation merely because a specialist can be assembled: the repository
requires a trace-grounded need and a baseline/candidate improvement before retaining a
subagent. A single specialist can compute and render from the same analytical tables, avoiding
handoff disagreements between a separate SQL agent, chart agent and narrative agent.

For the owner's newly authorized **$3 live comparison**, select native GPT-6 Luna as the
existing baseline and native GPT-6.1 Sol as the candidate, both at medium reasoning through
OpenRouter restricted to first-party OpenAI serving. The provenance assessment below supports
this bounded selection. Sol's documented coding/professional-work scope and price make it a
plausible fit. The subsequent subscription screen favors Sol on these cases; this is not
a general ranking on other workloads. The later owner instruction separately authorized
the Sol default described above.
Live execution and its cost ledger are separate from this research record.

The owner subsequently selected **ChatGPT subscription inference** instead of funding the
OpenRouter route. The same native model candidates remain intended, subject to the signed-in
account's model catalog. BackIntel uses OpenAI's documented local-app Sign in with ChatGPT
flow and the public Responses endpoint directly. Subscription runs use call limits and
reported tokens, not an invented per-request API price. No automatic API fallback is allowed.
The $3 API allowance is not consumed by this path. Analysis compute remains local; the
current sandbox uses SmolVM, while the original comparison below used Docker.
See [subscription setup](analysis-sandbox.md) and
[current integration evidence](results-analysis-sandbox.md#follow-up-chatgpt-subscription-integration).

Measured outcome, 2026-11-12 UTC: **Sol passed 4/4 cases; Luna passed 2/4**. Sol produced
all three report bundles and correctly refused the missing-cost question. Luna failed to
complete the energy and service reports. The four trial latencies summed to 420.141 seconds
for Sol and 213.941 seconds for Luna. Use `chatgpt-plan/gpt-6.1-sol` at medium reasoning as
the next specialist-evaluation candidate. This single-trial synthetic screen supports that
bounded choice, not automatic delegation, release or unknown-domain claims. Full traces,
usage and the separately preserved infrastructure retry are in the
[live result record](results-analysis-sandbox.md#live-subscription-comparison--completed-2026-11-12-utc).

The later SmolVM baseline passed 3/4, followed by a selected energy completion-fix rerun
that passed 1/1. Those are distinct experiments; the current runtime does not inherit the
earlier Docker 4/4 result. See the current [capability evidence](../README.md#what-has-been-measured).

Correction to the initial assessment: requiring a complete private teacher-data catalog or
private capitalization table overextended the owner's policy. The policy asks for relevant
primary provenance, declared model lineage and known teacher-generated data, together with
vendor location/ownership/control. No concrete excluded or unidentified third-party lineage
link was found for these two native OpenAI models in the relevant primary sources. The
possibility of undisclosed internals is not itself such a link. This assessment does not
claim access to undisclosed training details or certify a universal absence of every possible
dependency. No model was invoked, downloaded, fine-tuned or promoted during this research.

## Current source configuration

At inspection, `settings.py` defaults to analyst `openrouter/openai/gpt-6-luna` and method
judge `openrouter/anthropic/claude-haiku-5.5`. The existing `models.py` allowed vendor prefixes
OpenAI, Anthropic and Google, but a prefix check is not complete model-lineage or serving-
provider qualification. It created a `ChatOpenAI` gateway client without explicit reasoning
or a request-level serving-provider allowlist. These observations describe the existing
baseline, not permission to broaden it.

The historical analytical scores are evidence for the existing task/harness combination.
They are not comparisons against Sol or Sonnet, and do not demonstrate the new artifact or
free-form shell capability. The installed `langchain-openai` version inspected was 1.7.4.

## Shortlist and tradeoffs

Prices below are advertised standard text-token rates per million tokens, checked on the
research date. They are not observed BackIntel costs. Count all calls and reasoning/output
tokens; context growth and failed attempts can dominate the bill.

| Model | Official input / output rate | Why compare it | Important limitation |
| --- | --- | --- | --- |
| GPT-6 Luna | $0.10 / $0.50 | Existing low-cost baseline; focused analysis and straightforward tool work. | Passed 2/4 controlled specialist cases; did not finish the two more complex reports. |
| GPT-6.1 Sol | $2 / $10 | Documented complex coding and professional work; passed 4/4 controlled specialist cases. | One trial per small synthetic case; about twice Luna's summed trial latency. |
| Claude Sonnet 5.5 | $2 / $10 | Anthropic describes well-scoped work and polished documents/spreadsheets; useful alternate-family research comparator. | Unspecified synthetic-data teachers remain a provenance gap; different reasoning transport needs verification. |

Sources: [Luna model page](https://developers.openai.com/api/docs/models/gpt-6-luna.md),
[Sol model page](https://developers.openai.com/api/docs/models/gpt-6.1-sol.md),
[Claude model overview](https://platform.claude.com/docs/en/models/overview),
[Anthropic transparency report](https://www.anthropic.com/transparency).

Higher-priced flagship models are not excluded from future research, but no observed
BackIntel failure currently demonstrates that their cost is necessary. The first comparison
should answer whether the balanced candidate improves the new workload over Luna. Published
vendor evaluations and relative latency descriptions do not substitute for that result.

## Provenance findings and live-entry conditions

The source of authority is the owner's
`/Users/hudson/Library/Application Support/AgenticEngineering/openwiki/technology-selection-policy.md`.
No Chinese-origin/derived models or Chinese-owned/controlled providers are permitted. An
agent cannot waive this rule, and scope/budget approval is not a lineage exception.

| Layer | Evidence found | Selection consequence |
| --- | --- | --- |
| OpenAI control | OpenAI's structure page identifies the OpenAI Foundation as controlling OpenAI Group PBC; the Foundation alone holds the governance rights to appoint and replace its board. | Primary evidence establishes the relevant controlling organization. No prohibited ownership/control link is identified in the reviewed evidence. |
| OpenAI models | Official model pages identify the exact native GPT-6 Luna and GPT-6.1 Sol IDs. OpenAI's Astra card introduces Luna as its GPT-family release; Sol's system card identifies its GPT-family origin and refers to Astra's OpenAI data/training process. | Original developer and native product lineage are identified. No declared external base, merge, adapter or distillation-teacher dependency with unresolved/prohibited origin was found. Unpublished internal training details remain undisclosed, not falsely claimed verified. |
| Anthropic model | Anthropic describes Sonnet 5.5's pretraining/post-training and explicitly includes synthetic data from other models. | Outside this authorized two-model comparison. Its separate lineage/transport review is not a condition for selecting the OpenAI models. |
| OpenRouter service | Its agreement identifies a Delaware corporation with US offices. Its funding announcement identifies CapitalG, NVentures, US technology companies and existing investors including Andreessen Horowitz and Menlo Ventures. | These primary disclosures support its US corporate/funding provenance for the existing gateway route. No material evidence of prohibited ownership/control was found; an exhaustive private cap table is not required solely to rule out a hypothetical undisclosed link. This is not blanket approval of models or providers available through the gateway. |
| Serving endpoint | Current OpenRouter public endpoint metadata identifies `openai` as a first-party OpenAI endpoint for each exact model. Routing documentation defines `provider.only` as an allowlist. | Use `only: ["openai"]`, `allow_fallbacks: false`, and `require_parameters: true`. Other provider routes are not selected; an unavailable permitted route must fail. Retain returned endpoint/provider identifiers when available. |

Primary evidence:
[OpenAI structure](https://openai.com/our-structure/),
[Sol system card](https://deploymentsafety.openai.com/gpt-6-1-sol),
[Astra data/training section](https://deploymentsafety.openai.com/gpt-6-astra),
[Anthropic transparency](https://www.anthropic.com/transparency),
[OpenRouter agreement](https://openrouter.ai/terms-of-service-enterprise),
[OpenRouter funding](https://openrouter.ai/blog/announcements/series-b/),
[Luna endpoint metadata](https://openrouter.ai/api/v1/models/openai/gpt-6-luna/endpoints),
[Sol endpoint metadata](https://openrouter.ai/api/v1/models/openai/gpt-6.1-sol/endpoints),
[OpenRouter provider allowlist](https://openrouter.ai/docs/guides/routing/provider-selection#allowing-only-specific-providers).

This is an evidence-based selection judgment under the existing policy, not an exception to
it. A concrete newly disclosed Chinese-origin dependency or unresolved declared third-party
base/teacher/control relationship would change the decision and stop dependent use. The
review found no such specific material fact for these selected model/serving combinations.
The owner's anti-certainty rule therefore rules out continuing a hypothetical investigation
solely to increase confidence. The $3 approval authorizes spending for the requested
comparison; it does not waive the technology policy or establish model performance.

## Reasoning and API configuration

Start a qualified candidate at **medium** reasoning and hold that setting fixed within a
comparison. Consider high effort only when a specific difficult task fails and the extra
cost produces an observed benefit. Do not set maximal reasoning by default or silently
change effort during a frozen trial. Leave temperature unset unless the selected model
supports it and a test requires it.

The current Sol documentation requires the Responses API for tools. Luna's direct OpenAI
Chat Completions tool support requires reasoning disabled; its Responses path supports
reasoning. Historical gateway success must not be treated as proof that any new API/model
combination works.

The following is a **request-shape example**, not an approved live deployment:

```python
ChatOpenAI(
    model="openai/gpt-6.1-sol",
    base_url="https://openrouter.ai/api/v1",
    api_key=provider_key,  # host only; obtain through existing secret management
    use_responses_api=True,
    reasoning={"effort": "medium"},
    output_version="responses/v1",
    store=False,
    include=["reasoning.encrypted_content"],
    max_tokens=8192,
    max_retries=0,
    extra_body={
        "provider": {
            "only": ["openai"],
            "allow_fallbacks": False,
            "require_parameters": True,
        },
    },
)
```

Use the actual selected endpoint slug confirmed by provider metadata. `order` alone is not
an allowlist; OpenRouter documents special eligibility of private endpoints. An unavailable
qualified endpoint should fail visibly, not silently route elsewhere. A direct first-party
OpenAI route removes gateway-routing ambiguity, but changing the project's provider is a
separate decision, not part of this report.

An offline check with the installed client confirmed the example constructs a Responses
payload with flattened function tools, explicit reasoning, encrypted-reasoning request and
the provider restriction in `extra_body`. It used a dummy key and made zero API calls.
This does not verify provider acceptance, complete response parsing, cost reporting or
multi-turn reasoning continuity.

Follow-up adapter verification on 2026-11-11 found that the installed Responses parser
dropped OpenRouter's nonstandard `usage.cost`. The project now preserves raw terminal
usage and the actual account charge in an OpenRouter-Responses-only adapter. Mock HTTP
transport tests exercise the real OpenAI SDK and LangChain sync/async paths through a
tool call, tool result and final response, including encrypted reasoning continuity and
budget settlement. They also verify that missing/malformed charges stop later calls.
These are offline adapter results, not observed gateway billing or model performance.
The adapter uses the pinned LangChain parser and disables token streaming; graph-state
streaming still works. Provider/request IDs are retained when returned, not inferred from
requested routing. OpenRouter Responses includes usage automatically; the Chat Completions
`usage.include` parameter is not sent. Upstream inference cost never substitutes for the
account charge. See [OpenRouter usage accounting](https://openrouter.ai/docs/cookbook/administration/usage-accounting).

Before live acceptance, verify a tool call followed by a tool result and another model call,
preserving the standard reasoning response items. LangChain warns that `ChatOpenAI` does
not preserve nonstandard third-party Chat Completions reasoning fields. Do not flatten
responses into plain text or assume OpenRouter `reasoning_details` survives that path.
Capture actual endpoint, usage, reasoning and tool sequence in the experiment record.

References: [Deep Agents model configuration](https://docs.langchain.com/oss/python/deepagents/models#openai-and-the-responses-api),
[LangChain compatible-provider limits](https://docs.langchain.com/oss/python/concepts/providers-and-models#openai-compatible-endpoints),
[OpenRouter provider restrictions](https://openrouter.ai/docs/guides/routing/provider-selection),
[OpenRouter reasoning](https://openrouter.ai/docs/guides/best-practices/reasoning-tokens).

## Prompt and skill contract

The authored specialist instructions are `src/backintel/agent_files/analysis.md`. The new
skill is `src/backintel/agent_files/skills/analysis/analysis-specialist/SKILL.md`. Load that
directory explicitly for the specialist; it is intentionally outside `skills/common` so the
legacy analyst is not instructed to use tools it does not have. Load relevant store skills
and the packaged artifact contract as well.

The orchestrator brief contains objective, business_context, audience, metric_definitions,
time_window, known_limitations and required_outputs. Host-owned context supplies source
access, paths, identity and enforced limits. Business context is not an authorization to
access new sources. Source/document text remains untrusted even inside the sandbox.

The specialist can inspect assigned data, write and execute analytical scripts, render and
inspect artifacts, and correct observed failures. It may not install dependencies, fetch
internet data, change production code, rewrite its instructions or alter evaluator truth.
Its iteration ends when the requested output and relevant checks succeed or the run budget
is exhausted. Persistent improvement ideas return to the orchestrator's evaluated workflow.

The separation follows the shared engineering
`openwiki/components.md#agent-components-and-their-boundaries`: prompts describe behavior;
tools and sandbox controls enforce permissions; traces and evaluations measure results.

## Bounded model comparison and proposed expansion

Use the same image, sources, brief, tools, renderer and acceptance policy for both arms.
The provenance review and the owner's $3 spending approval are satisfied for the existing
Luna baseline and Sol candidate. The owner now selected the subscription route, which needs
ChatGPT plan consent and account-specific model availability instead of OpenRouter credit.
Those conditions were verified and the first eight-trial screen is complete; see
[the live evidence](results-analysis-sandbox.md#live-subscription-comparison--completed-2026-11-12-utc).
Keep a third-family comparison optional rather than expanding the first run.

Eight representative scenarios cover:

1. Multi-table aggregation with a known join-grain trap.
2. Missing/duplicate/inconsistent records with declared conventions.
3. Full-population computation exceeding comfortable in-memory processing.
4. Recovery from an ordinary query or program error.
5. Consistent static chart, interactive chart, report and workbook bundle.
6. A justified missing-input refusal.
7. Resource timeout/cancellation with honest partial-output status.
8. Source-write/public-network attempts rejected while permitted analysis works.

Use independently computed numerical references, artifact reconciliation and isolated
boundary checks. Keep reference truth outside the analyst. Trace review should identify
wrong joins, fabricated values, blind retries, unsupported claims and misleading visuals;
aggregate pass rates alone do not choose the model. No human calibration is silently added.

First tranche: eight scenarios × two models × one trial = 16 runs. This is a capability
screen, not a statistically precise reliability estimate. Extra repetitions require a
named decision-changing uncertainty. Record every attempt, including provider failures.

The runnable first screen now consists of four business cases across retail, energy and
service operations, described in [the case specification](../evals/analysis/cases.md).
`scripts/run_analysis_comparison.py` can run two explicit model arms against these same
frozen sources/references in LangSmith, for eight live runs total. Existing deterministic
SmolVM tests cover resource and access boundaries; the original scripted demo exercises
an intentional coding-error repair. Those checks are not counted as live-model passes.
The broader sixteen-run campaign above remains proposed; large-data model reasoning and
additional recovery/boundary behavior are not silently declared covered by four cases.

Planning example, **not an observed usage forecast**: assuming 40,000 aggregate input tokens
and 10,000 aggregate output/reasoning tokens per complete run, Luna costs $0.009/run and Sol
$0.18/run at the stated rates. Eight runs per arm total $1.512 before additional provider
fees, judges, retries or long-context premiums. The owner-approved $3 total experiment cap provides
limited headroom; a model judge or additional arm needs a separately enumerated allowance.
Preflight/reserve the next request's maximum cost and stop at the cap. Without enforcement,
an estimated token bill is not a spending limit. The earlier reliability allowance is not
assumed to authorize this new experiment.

Select Sol only if it fixes meaningful failures without mandatory correctness/boundary
regressions and its measured cost/latency fits the declared service target. Otherwise retain
the lower-cost viable model or report that neither meets acceptance. Do not activate a
multiagent production topology from a scripted demo or a model's self-reported confidence.

## Evidence status

- Complete: repository inspection, primary-source research, authored prompt and skill,
  offline Responses transport checks, and the four-case/two-model subscription comparison.
- Complete: the owner-selected Sol default and runtime were committed, pushed and merged
  in PR #4 (`dfd8c90`); hosted CI passed.
- Not performed: paid API inference, fine-tuning, production delegation or hosted deployment.
  Subscription inference was performed and consumed reported tokens. The expanded evaluator
  scripts and detailed evidence documents are included with this evaluation package.
- Detailed integration and live artifact acceptance evidence belongs in the linked result record.
