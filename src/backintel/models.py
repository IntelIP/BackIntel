"""Model factory. A model id is `<provider>/<model>`:

- `openrouter/<vendor>/<model>`: OpenRouter with OPENROUTER_API_KEY. Only OpenAI, Anthropic and
  Google models are allowed, per the technology-selection policy of 2026-10-30.
- `chatgpt-plan/<model>`: the operator's ChatGPT plan after `backintel chatgpt login`.
- `openai/<model>`: OpenAI directly with OPENAI_API_KEY.
"""

from __future__ import annotations

import math
import os

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langchain_openai.chat_models.base import _construct_lc_result_from_responses_api, _is_pydantic_class

OPENROUTER_URL = "https://openrouter.ai/api/v1"
ALLOWED_OPENROUTER_VENDORS = ("openai", "anthropic", "google")


class ModelPolicyError(ValueError):
    """The model or vendor is outside the approved set."""


def normalize_token_usage(value: dict | None) -> dict:
    """Use one token naming convention without estimating missing provider charges."""
    value = value or {}
    result = {}
    for key, alternative in (
        ("prompt_tokens", "input_tokens"),
        ("completion_tokens", "output_tokens"),
        ("total_tokens", "total_tokens"),
    ):
        count = value.get(key, value.get(alternative))
        if isinstance(count, int) and not isinstance(count, bool) and count >= 0:
            result[key] = count
    if "cost" in value:
        cost = value["cost"]
        result["cost"] = (
            cost
            if not isinstance(cost, bool)
            and isinstance(cost, (int, float))
            and math.isfinite(cost)
            and cost >= 0
            else None
        )
    return result


def message_token_usage(message) -> dict:
    meta = getattr(message, "response_metadata", None) or {}
    return {
        **normalize_token_usage(getattr(message, "usage_metadata", None)),
        **normalize_token_usage(meta.get("token_usage")),
    }


class OpenRouterResponsesChatOpenAI(ChatOpenAI):
    """Preserve gateway billing through langchain-openai's pinned Responses parser.

    That parser retains standard reasoning/tool items but drops nonstandard usage.cost.
    Only terminal, non-streaming responses are supported here; callbacks settle the
    complete reported charge before admitting the next model turn. Compatibility tests
    exercise the actual OpenAI SDK parser and this private LangChain conversion hook.
    """

    disable_streaming: bool = True

    def _response_result(self, raw_response, schema=None):
        response = raw_response.parse()
        usage = response.usage.model_dump(exclude_none=True) if response.usage else {}
        token_usage = normalize_token_usage(usage)
        metadata = {"token_usage": token_usage, "responses_usage": usage, "gateway": "openrouter"}
        # Keep what the gateway actually reports; requested routing is not endpoint evidence.
        for field in ("provider", "provider_name", "endpoint_id"):
            if (value := getattr(response, field, None)) is not None:
                metadata[field] = value
        if request_id := raw_response.headers.get("x-request-id"):
            metadata["gateway_request_id"] = request_id
        result = _construct_lc_result_from_responses_api(
            response, schema=schema, metadata=metadata, output_version=self.output_version
        )
        result.llm_output = {"token_usage": token_usage, "model_name": response.model}
        return result

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        payload = self._get_request_payload(messages, stop=stop, **kwargs)
        payload.pop("stream", None)
        schema = kwargs.get("response_format")
        endpoint = self.root_client.responses.with_raw_response
        raw = endpoint.parse(**payload) if _is_pydantic_class(schema) else endpoint.create(**payload)
        return self._response_result(raw, schema=schema)

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        payload = self._get_request_payload(messages, stop=stop, **kwargs)
        payload.pop("stream", None)
        schema = kwargs.get("response_format")
        endpoint = self.root_async_client.responses.with_raw_response
        raw = (
            await endpoint.parse(**payload)
            if _is_pydantic_class(schema)
            else await endpoint.create(**payload)
        )
        return self._response_result(raw, schema=schema)


def parse_model_id(model_id: str) -> tuple[str, str]:
    provider, _, name = model_id.partition("/")
    if not name:
        raise ValueError("Model ids look like '<provider>/<model>', e.g. 'openrouter/openai/gpt-6-luna'.")
    return provider, name


def build_model(
    model_id: str,
    *,
    env: dict[str, str] | None = None,
    temperature: float | None = None,
    max_retries: int = 2,
    reasoning_effort: str | None = None,
    responses_api: bool = False,
    first_party_only: bool = False,
    timeout_s: float = 300,
) -> BaseChatModel:
    if max_retries < 0:
        raise ValueError("max_retries must be non-negative")
    env = os.environ if env is None else env
    provider, name = parse_model_id(model_id)
    if timeout_s <= 0:
        raise ValueError("timeout_s must be positive")
    if reasoning_effort not in {None, "none", "minimal", "low", "medium", "high", "xhigh"}:
        raise ValueError("Unsupported reasoning effort; check the selected model's capabilities")
    transport = {}
    if responses_api:
        transport = {
            "use_responses_api": True,
            "output_version": "responses/v1",
            "store": False,
            "include": ["reasoning.encrypted_content"],
        }
        if reasoning_effort is not None:
            transport["reasoning"] = {"effort": reasoning_effort}
    elif reasoning_effort is not None:
        transport["reasoning_effort"] = reasoning_effort
    if provider == "openrouter":
        vendor = name.split("/")[0]
        if vendor not in ALLOWED_OPENROUTER_VENDORS:
            raise ModelPolicyError(
                f"OpenRouter vendor {vendor!r} is not approved; allowed: {ALLOWED_OPENROUTER_VENDORS}"
            )
        key = env.get("OPENROUTER_API_KEY")
        if not key:
            raise RuntimeError("OPENROUTER_API_KEY is not set (run under Doppler).")
        kwargs = {"temperature": temperature} if temperature is not None else {}
        # Responses includes usage automatically and has no usage.include parameter.
        # https://openrouter.ai/docs/cookbook/administration/usage-accounting
        extra_body = {} if responses_api else {"usage": {"include": True}}
        if first_party_only:
            extra_body["provider"] = {"only": [vendor], "allow_fallbacks": False, "require_parameters": True}
        model_class = OpenRouterResponsesChatOpenAI if responses_api else ChatOpenAI
        return model_class(
            model=name,
            api_key=key,
            base_url=OPENROUTER_URL,
            max_retries=max_retries,
            max_tokens=int(env.get("BACKINTEL_MAX_COMPLETION_TOKENS", "8192")),
            timeout=timeout_s,
            # Preserve account charges; never infer them from upstream cost or token prices.
            extra_body=extra_body,
            default_headers={
                "HTTP-Referer": "https://github.com/IntelIP/BackIntel",
                "X-Title": "BackIntel v2 benchmark",
            },
            **kwargs,
            **transport,
        )
    if provider == "chatgpt-plan":
        from backintel.providers.chatgpt_plan import plan_model

        if first_party_only:
            raise ValueError("first_party_only routing applies to OpenRouter, not the plan adapter")
        return plan_model(
            name, reasoning_effort=reasoning_effort or "medium", max_retries=max_retries, timeout_s=timeout_s
        )
    if provider == "openai":
        key = env.get("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("OPENAI_API_KEY is not set.")
        return ChatOpenAI(model=name, api_key=key, max_retries=max_retries, timeout=timeout_s, **transport)
    raise ValueError(f"Unknown provider {provider!r}; use openrouter, chatgpt-plan or openai.")


def usage_from_message(message) -> dict:
    """Tokens and (when the provider reports it) cost for one model message."""
    usage = message_token_usage(message)
    return {
        "input_tokens": usage.get("prompt_tokens", 0),
        "output_tokens": usage.get("completion_tokens", 0),
        "total_tokens": usage.get("total_tokens", 0),
        "cost_usd": usage.get("cost"),
    }
