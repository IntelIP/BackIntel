"""Model factory. A model id is `<provider>/<model>`:

- `openrouter/<vendor>/<model>`: OpenRouter with OPENROUTER_API_KEY. Only OpenAI, Anthropic and
  Google models are allowed, per the technology-selection policy of 2026-10-30.
- `chatgpt-plan/<model>`: the operator's ChatGPT plan after `backintel chatgpt login`.
- `openai/<model>`: OpenAI directly with OPENAI_API_KEY.
"""

from __future__ import annotations

import os

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

OPENROUTER_URL = "https://openrouter.ai/api/v1"
ALLOWED_OPENROUTER_VENDORS = ("openai", "anthropic", "google")


class ModelPolicyError(ValueError):
    """The model or vendor is outside the approved set."""


def parse_model_id(model_id: str) -> tuple[str, str]:
    provider, _, name = model_id.partition("/")
    if not name:
        raise ValueError("Model ids look like '<provider>/<model>', e.g. 'openrouter/openai/gpt-6-luna'.")
    return provider, name


def build_model(
    model_id: str, *, env: dict[str, str] | None = None, temperature: float | None = None
) -> BaseChatModel:
    env = os.environ if env is None else env
    provider, name = parse_model_id(model_id)
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
        return ChatOpenAI(
            model=name,
            api_key=key,
            base_url=OPENROUTER_URL,
            max_retries=2,
            max_tokens=int(env.get("BACKINTEL_MAX_COMPLETION_TOKENS", "8192")),
            timeout=300,
            # OpenRouter returns the request's cost with usage when asked; it lands in
            # response_metadata so the benchmark can record spend per run.
            extra_body={"usage": {"include": True}},
            default_headers={
                "HTTP-Referer": "https://github.com/IntelIP/BackIntel",
                "X-Title": "BackIntel v2 benchmark",
            },
            **kwargs,
        )
    if provider == "chatgpt-plan":
        from backintel.providers.chatgpt_plan import plan_model

        return plan_model(name)
    if provider == "openai":
        key = env.get("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("OPENAI_API_KEY is not set.")
        return ChatOpenAI(model=name, api_key=key, max_retries=2, timeout=300)
    raise ValueError(f"Unknown provider {provider!r}; use openrouter, chatgpt-plan or openai.")


def usage_from_message(message) -> dict:
    """Tokens and (when the provider reports it) cost for one model message."""
    usage = dict(getattr(message, "usage_metadata", None) or {})
    meta = getattr(message, "response_metadata", None) or {}
    token_usage = meta.get("token_usage") or {}
    cost = token_usage.get("cost")
    if cost is None and isinstance(token_usage.get("cost_details"), dict):
        cost = token_usage["cost_details"].get("upstream_inference_cost")
    return {
        "input_tokens": usage.get("input_tokens", 0),
        "output_tokens": usage.get("output_tokens", 0),
        "total_tokens": usage.get("total_tokens", 0),
        "cost_usd": cost,
    }
