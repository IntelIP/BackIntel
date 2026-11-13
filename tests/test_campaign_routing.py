"""The frozen comparison uses first-party routing for every OpenRouter role."""

import importlib.util
from pathlib import Path

import pytest

from backintel.bench import improvement, judge, run
from backintel.models import build_model


def runner():
    path = Path(__file__).parents[1] / "scripts/run_improvement_cycle.py"
    spec = importlib.util.spec_from_file_location("campaign_routing_runner", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_stage_pins_analyst_judge_and_worker_without_changing_factory(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "offline-test-no-requests")
    for module in (run, judge, improvement):
        monkeypatch.setattr(module, "build_model", module.build_model)
    cycle = runner()
    cycle.configure_stage_routing(cycle.MODEL_ROUTING)
    for module, model_id, vendor in (
        (run, "openrouter/openai/gpt-6-luna", "openai"),
        (judge, "openrouter/anthropic/claude-haiku-5.5", "anthropic"),
        (improvement, "openrouter/openai/gpt-6-luna", "openai"),
    ):
        model = module.build_model(model_id, max_retries=0)
        assert model.extra_body["provider"] == {
            "only": [vendor],
            "allow_fallbacks": False,
            "require_parameters": True,
        }
        assert model.max_retries == 0
    ordinary = build_model("openrouter/openai/gpt-6-luna", max_retries=0)
    assert "provider" not in ordinary.extra_body


def test_stage_rejects_missing_or_unknown_routing_before_model_construction():
    cycle = runner()
    for policy in (None, "fallback_allowed"):
        with pytest.raises(ValueError, match="first_party_only"):
            cycle.configure_stage_routing(policy)
