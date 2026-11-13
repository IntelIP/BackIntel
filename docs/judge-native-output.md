# Native judge output transport

The 2026-11-13 native control run completed six valid calls with complete conservative
usage estimates. It matched all four method controls, but only four of six combined
control expectations. The caveat failures were a small-extract penalty despite the
bounded requested population, and treating partial scope disclosure as wholly absent.
These are evaluator findings, not analyst capability failures. Original cases, labels,
judgments and account records are unchanged.

Inspection found a concrete transport constraint before another rubric revision:
`judge_answer` called `ChatAnthropic.with_structured_output(schema)`. The installed
`langchain-anthropic==1.7.10` defaults to function calling and emits
`tool_choice={"type":"tool","name":"rubric"}` for Haiku 5.5. The native factory
does not override thinking or effort. Haiku otherwise defaults to adaptive thinking
and medium effort, but accepted forced tool use begins directly with the tool call
and has no initial thinking block. See the official
[Haiku model configuration](https://platform.claude.com/docs/en/models/haiku-5-5/overview)
and [thinking/tool compatibility](https://platform.claude.com/docs/en/build-with-claude/thinking#response-prefill-and-forced-tool-use).

The prospective fix selects `method="json_schema"` for native Anthropic judges. This
uses the provider's JSON response format and removes the forced tool call, allowing
adaptive thinking before the structured assessment. The existing SDK already supports
this mode; no package, model, effort, rate, budget, rubric, score mapping or expectation
changes are needed. Other providers retain their previous transport. See
[LangChain structured output](https://docs.langchain.com/oss/python/integrations/chat/anthropic#structured-output)
and [Anthropic JSON outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs).

The existing rubric already distinguishes the requested population from unsupported
generalization, and partial explanation from an omitted or denied limitation. Keeping
it fixed isolates the transport change; increasing effort or revising wording at the
same time would obscure which change affected the judgments. A transport constraint
is established; it is not proof that reasoning configuration caused both semantic
failures or that medium effort will now be sufficient.

Offline tests intercept the actual native SDK request for answered and declined
responses. They check JSON schema, absence of forced tools, unchanged standard tier
and token limit, parsing of a response containing a thinking block plus JSON, retained
assessments, and callback/accounting completeness. The partial fixture remains 0.5.
Raw response metadata is retained internally so a non-completed response is rejected,
even if LangChain's JSON parser could repair it. The tests cover a token-limit stop
with otherwise parseable assessments; its usage remains accounted, but it is not graded.
These mocks establish wiring, not model quality. Existing caveat mappings and source
context tests also remain required.

Before adoption, rerun the same frozen six controls once with this judge identity,
retaining the prior results. Keep the 2048-token output limit and bounded native
budget; thinking shares that limit, so truncation must invalidate the judgment rather
than produce a substitute score. Additional thinking and initial schema compilation
may increase cost and latency. The live result determines whether this candidate
addresses the observed semantic errors; no live success is claimed here.

The subsequent unchanged-control run completed all six judgments and matched **5/6**
expectations (previous native transport: 4/6). It fixed the bounded-extract penalty in
this sample, but the partial-disclosure control still disagreed. Estimated usage was
$0.0329345; no invoice cost or general reliability rate is inferred. The
[validation record](../results/judge-context-validation.md#native-json-output-contrast--2026-11-13)
retains the exact outcome. The campaign remains unstarted; this candidate is still draft.
