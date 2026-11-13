"""Conservative native text-token accounting, never an invoice or credit balance.

All input tokens use the highest standard long-context cache-write rate, so caching
discounts and short-context pricing cannot make the allowance undercount. All output
tokens, including reasoning, use the long-context output rate. Frozen 2026-11-13.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from decimal import ROUND_CEILING, Decimal

NATIVE_RATES = {
    "openai/gpt-6-luna": {
        "input_per_million": "0.50",  # 12h cache write, long context
        "output_per_million": "0.75",
        "context_limit": 1_050_000,
        "output_limit": 128_000,
    },
    "anthropic/claude-haiku-5-5": {
        "input_per_million": "1.00",  # 1h cache write, >100k prompt
        "output_per_million": "2.50",
        "context_limit": 1_000_000,
        "output_limit": 128_000,
    },
}
NATIVE_POLICY = {
    "basis": "conservative_native_text_tokens",
    "date": "2026-11-13",
    "rates": NATIVE_RATES,
    "sources": [
        "https://developers.openai.com/api/docs/pricing",
        "https://developers.openai.com/api/docs/models/gpt-6-luna",
        "https://platform.claude.com/docs/en/models/haiku-5-5/overview",
    ],
    "scope": "native standard service, global endpoints, text and local tools only; no discounts",
    "actual_charge": "unknown until provider billing reconciliation; credits are not zero-cost usage",
    "rounding": "round each call upward to USD 0.000000001",
}


def native_accounting_version() -> str:
    return hashlib.sha256(json.dumps(NATIVE_POLICY, sort_keys=True).encode()).hexdigest()[:16]


def _count(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def native_estimate(model_id: str, message) -> float | None:
    """Use complete standardized totals; reject unqualified models/usage/service tiers."""
    if model_id not in NATIVE_RATES:
        raise ValueError(f"No qualified native accounting for {model_id!r}")
    usage = getattr(message, "usage_metadata", None) or {}
    meta = getattr(message, "response_metadata", None) or {}
    inp, out, total = (usage.get(k) for k in ("input_tokens", "output_tokens", "total_tokens"))
    if not all(_count(v) for v in (inp, out, total)) or total != inp + out:
        return None
    rates = NATIVE_RATES[model_id]
    if total > rates["context_limit"] or out > rates["output_limit"]:
        return None
    if meta.get("service_tier") not in {None, "default", "standard"}:
        return None
    name = model_id.partition("/")[2]
    actual_model = meta.get("model_name", meta.get("model"))
    if not isinstance(actual_model, str) or not re.fullmatch(
        re.escape(name) + r"(?:-\d{4}-\d{2}-\d{2})?", actual_model
    ):
        return None
    for field, limit in (("input_token_details", inp), ("output_token_details", out)):
        for key, value in (usage.get(field) or {}).items():
            if not _count(value) or value > limit or ("audio" in key and value):
                return None
    # LangChain adds both cache reads and writes to Anthropic's standardized input
    # total. Check against the raw response so a missing cache count isn't assumed zero.
    if model_id.startswith("anthropic/"):
        raw = meta.get("usage") or {}
        counts = [
            raw.get(k) for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")
        ]
        if not all(_count(v) for v in counts) or sum(counts) != inp or raw.get("output_tokens") != out:
            return None
        if raw.get("service_tier") not in {None, "standard"}:
            return None
        server_tools = raw.get("server_tool_use") or {}
        if any(v not in (None, 0) for v in server_tools.values()):
            return None
    value = (
        Decimal(inp) * Decimal(rates["input_per_million"])
        + Decimal(out) * Decimal(rates["output_per_million"])
    ) / Decimal(1_000_000)
    return float(value.quantize(Decimal("0.000000001"), rounding=ROUND_CEILING))


def valid_amount(value) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(value)
        and value >= 0
    )
