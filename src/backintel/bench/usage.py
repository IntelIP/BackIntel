"""Provider-reported usage, including failed agent graphs and evaluator calls.

Dollar admission uses an operator-declared per-call reservation. It is not a provider
billing guarantee: a response above its reservation is recorded and stops further calls.
Use the provider's key limit when an absolute monetary ceiling is required.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from threading import Lock
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler

from backintel.models import message_token_usage, normalize_token_usage


class BudgetExceeded(RuntimeError):
    pass


@dataclass
class RunBudget:
    limit_usd: float
    max_calls: int
    reservation_usd: float
    spent_usd: float = 0.0
    reserved_usd: float = 0.0
    calls: int = 0
    uncertain: bool = False
    breached: bool = False
    _lock: Lock = field(default_factory=Lock, repr=False)

    def __post_init__(self):
        if not all(math.isfinite(x) and x > 0 for x in (self.limit_usd, self.reservation_usd)):
            raise ValueError("Dollar limit and per-call reservation must be finite and positive")
        if self.max_calls < 1:
            raise ValueError("max_calls must be positive")

    def _available(self) -> bool:
        return (
            not self.uncertain
            and not self.breached
            and self.calls < self.max_calls
            and self.spent_usd + self.reserved_usd + self.reservation_usd <= self.limit_usd + 1e-12
        )

    def can_admit(self) -> bool:
        """Snapshot for scheduling; reserve checks atomically again before a model call."""
        with self._lock:
            return self._available()

    def reserve(self) -> None:
        with self._lock:
            if not self._available():
                raise BudgetExceeded("Evaluation call admission stopped by the approved budget")
            self.calls += 1
            self.reserved_usd += self.reservation_usd

    def settle(self, cost: float | None) -> None:
        with self._lock:
            if (
                isinstance(cost, bool)
                or not isinstance(cost, (int, float))
                or not math.isfinite(cost)
                or cost < 0
            ):
                self.uncertain = True
                return  # Keep the reservation; unknown charges are never treated as free.
            self.reserved_usd -= self.reservation_usd
            self.spent_usd += cost
            self.breached |= cost > self.reservation_usd or self.spent_usd > self.limit_usd

    def report(self) -> dict:
        return {
            "limit_usd": self.limit_usd,
            "max_calls": self.max_calls,
            "reservation_usd": self.reservation_usd,
            "reported_spent_usd": self.spent_usd,
            "reserved_usd": max(0.0, self.reserved_usd),
            "calls": self.calls,
            "unknown_charge": self.uncertain,
            "reservation_breached": self.breached,
            "scope": "application call admission; provider retries and billing are not a hard dollar cap",
        }


@dataclass
class PlanRunBudget:
    """Bound subscription work by calls; never manufacture a dollar charge."""

    max_calls: int
    calls: int = 0
    stopped_reason: str | None = None
    _lock: Lock = field(default_factory=Lock, repr=False)

    def __post_init__(self):
        if isinstance(self.max_calls, bool) or not isinstance(self.max_calls, int) or self.max_calls < 1:
            raise ValueError("max_calls must be a positive integer")

    def can_admit(self) -> bool:
        with self._lock:
            return self.stopped_reason is None and self.calls < self.max_calls

    def reserve(self) -> None:
        with self._lock:
            if self.stopped_reason is not None or self.calls >= self.max_calls:
                raise BudgetExceeded("ChatGPT subscription call admission stopped")
            self.calls += 1

    def settle(self, usage: dict | None) -> None:
        if not usage or not all(key in usage for key in ("prompt_tokens", "completion_tokens")):
            with self._lock:
                self.stopped_reason = "A request failed or did not report complete token usage."

    def report(self) -> dict:
        return {
            "billing_mode": "chatgpt_plan",
            "max_calls": self.max_calls,
            "calls": self.calls,
            "stopped_reason": self.stopped_reason,
            "scope": "application call limit; subscription availability is enforced by OpenAI",
        }


class UsageTracker(BaseCallbackHandler):
    """Use one tracker per answer/judge call; optional shared budget spans the experiment."""

    raise_error = True
    run_inline = True

    def __init__(self, budget: RunBudget | PlanRunBudget | None = None):
        self.budget = budget
        self.started: set[UUID] = set()
        self.finished: dict[UUID, dict | None] = {}
        self._lock = Lock()

    def on_chat_model_start(self, serialized, messages, *, run_id, **kwargs):
        del serialized, messages  # Callback protocol; the ledger never retains prompts.
        with self._lock:
            if run_id not in self.started:
                if self.budget:
                    self.budget.reserve()
                self.started.add(run_id)

    def on_llm_end(self, response, *, run_id, **kwargs):
        value = normalize_token_usage((response.llm_output or {}).get("token_usage"))
        for generations in response.generations:
            for generation in generations:
                message = getattr(generation, "message", None)
                reported = message_token_usage(message)
                if reported:
                    # LLM output may be empty for Responses or omit standard token counts.
                    # Combine metadata once; never sum duplicate representations of one call.
                    value = {**reported, **value}
                    break
            if value:
                break
        self._finish(run_id, value or None)

    def on_llm_error(self, error, *, run_id, **kwargs):
        del error  # Error text may contain sensitive provider details; usage remains unknown.
        self._finish(run_id, None)

    def _finish(self, run_id, value):
        with self._lock:
            if run_id in self.finished:
                return
            self.finished[run_id] = value
            if self.budget and run_id in self.started:
                self.budget.settle(
                    value if isinstance(self.budget, PlanRunBudget) else value.get("cost") if value else None
                )

    def report(self) -> dict:
        values = [v for v in self.finished.values() if v is not None]
        costs = [v.get("cost") for v in values]
        priced = [
            float(c)
            for c in costs
            if not isinstance(c, bool) and isinstance(c, (int, float)) and math.isfinite(c) and c >= 0
        ]
        incomplete = self.started - self.finished.keys()
        report = {
            "llm_calls": len(self.started | self.finished.keys()),
            "input_tokens": sum(v.get("prompt_tokens", 0) for v in values),
            "output_tokens": sum(v.get("completion_tokens", 0) for v in values),
            "cost_usd": sum(priced) if priced or not (self.started | self.finished.keys()) else None,
            "unpriced_llm_calls": len(self.started | self.finished.keys()) - len(priced),
            "usage_complete": (
                not incomplete
                and len(values) == len(self.started | self.finished.keys())
                and all("prompt_tokens" in v and "completion_tokens" in v for v in values)
            ),
            "cost_complete": not incomplete and len(priced) == len(self.started | self.finished.keys()),
            "scope": "provider-reported API usage; failed unreported requests remain unknown",
        }
        if isinstance(self.budget, PlanRunBudget):
            report.update(
                billing_mode="chatgpt_plan",
                cost_usd=None,
                cost_complete=False,
                cost_applicable=False,
                scope="ChatGPT subscription token usage; no per-request dollar charge reported",
            )
        return report
