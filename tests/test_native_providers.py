"""Native provider contracts; all HTTP is intercepted, with no account calls."""

import json

import anthropic
import httpx
import httpx2
import pytest
from langsmith import tracing_context
from openai import OpenAI

from backintel.bench.usage import BudgetExceeded, NativeRunBudget, RunBudget, UsageTracker
from backintel.models import build_model
from backintel.settings import Settings


def test_native_defaults_and_explicit_override():
    settings = Settings.from_env({})
    assert settings.model == "openai/gpt-6-luna"
    assert settings.judge_model == "anthropic/claude-haiku-5-5"
    assert settings.analysis_model == "chatgpt-plan/gpt-6.1-sol"
    explicit = Settings.from_env({"BACKINTEL_MODEL": "openrouter/openai/gpt-6-luna"})
    assert explicit.model == "openrouter/openai/gpt-6-luna"


@pytest.mark.parametrize("provider,key", [("openai", "OPENAI_API_KEY"), ("anthropic", "ANTHROPIC_API_KEY")])
def test_native_credentials_do_not_fall_back_to_openrouter(provider, key):
    with pytest.raises(RuntimeError, match=key):
        build_model(f"{provider}/test-not-invoked", env={"OPENROUTER_API_KEY": "test"})


@pytest.mark.parametrize("native_accounting", [False, True])
def test_openai_native_endpoint_limits_and_usage(monkeypatch, native_accounting):
    monkeypatch.setenv("OPENAI_BASE_URL", "https://unwanted.example/v1")
    model = build_model(
        "openai/gpt-6-luna",
        env={
            "OPENAI_API_KEY": "test",
            "BACKINTEL_MAX_COMPLETION_TOKENS": "256",
            "OPENAI_PROJECT_ID": "test-project",
        },
        first_party_only=True,
        max_retries=0,
        timeout_s=30,
    )
    assert str(model.root_client.base_url) == "https://api.openai.com/v1/"
    assert model.max_retries == 0
    assert model.default_headers["OpenAI-Project"] == "test-project"
    requests = []

    def handle(request):
        assert request.url.host == "api.openai.com"
        assert request.url.path == "/v1/chat/completions"
        payload = json.loads(request.content)
        requests.append(payload)
        assert payload["max_completion_tokens"] == 256
        assert payload["service_tier"] == "default"
        assert "provider" not in payload
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-native-test",
                "object": "chat.completion",
                "created": 1,
                "model": "gpt-6-luna",
                "choices": [
                    {"index": 0, "message": {"role": "assistant", "content": "OK"}, "finish_reason": "stop"}
                ],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 2,
                    "total_tokens": 12,
                    "prompt_tokens_details": {"cached_tokens": 5},
                    "completion_tokens_details": {"reasoning_tokens": 1},
                },
            },
        )

    budget_type = NativeRunBudget if native_accounting else RunBudget
    tracker = UsageTracker(budget_type(0.05, 2, 0.01), model_id="openai/gpt-6-luna")
    with (
        OpenAI(
            api_key="test",
            http_client=httpx.Client(transport=httpx.MockTransport(handle)),
            base_url="https://api.openai.com/v1",
        ) as client,
        tracing_context(enabled=False),
    ):
        monkeypatch.setattr(model, "client", client.chat.completions)
        assert model.invoke("Check native routing", config={"callbacks": [tracker]}).content == "OK"
        if not native_accounting:
            with pytest.raises(BudgetExceeded):
                model.invoke("Do not send", config={"callbacks": [tracker]})
    assert len(requests) == 1
    assert tracker.report()["input_tokens"] == 10
    assert tracker.report()["usage_complete"]
    assert tracker.report()["cost_usd"] is None
    assert not tracker.report()["cost_complete"]
    assert tracker.budget.can_admit() is native_accounting
    if native_accounting:
        assert tracker.report()["estimate_complete"]
        assert tracker.report()["estimated_cost_usd"] == pytest.approx(0.0000065)


@pytest.mark.parametrize("native_accounting", [False, True])
def test_anthropic_native_structured_output_and_usage(monkeypatch, native_accounting):
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://unwanted.example")
    model = build_model(
        "anthropic/claude-haiku-5-5",
        env={
            "ANTHROPIC_API_KEY": "test",
            "BACKINTEL_MAX_COMPLETION_TOKENS": "256",
            "ANTHROPIC_WORKSPACE_ID": "test-workspace",
        },
        max_retries=0,
        timeout_s=30,
        first_party_only=True,
    )
    assert str(model._client.base_url) == "https://api.anthropic.com"
    assert model.max_retries == 0
    assert model.default_headers["anthropic-workspace-id"] == "test-workspace"
    schema = {
        "title": "test_rubric",
        "description": "Test grading",
        "type": "object",
        "properties": {"rating": {"type": "integer"}},
        "required": ["rating"],
    }
    requests = []

    def handle(request):
        assert request.url.host == "api.anthropic.com"
        assert request.url.path == "/v1/messages"
        payload = json.loads(request.content)
        requests.append(payload)
        assert payload["max_tokens"] == 256
        assert payload["service_tier"] == "standard_only"
        assert payload["model"] == "claude-haiku-5-5"
        assert payload["tools"][0]["name"] == "test_rubric"
        assert "provider" not in payload
        return httpx2.Response(
            200,
            json={
                "id": "msg_native_test",
                "type": "message",
                "role": "assistant",
                "model": "claude-haiku-5-5",
                "stop_reason": "tool_use",
                "stop_sequence": None,
                "content": [
                    {"type": "tool_use", "id": "toolu_test", "name": "test_rubric", "input": {"rating": 2}}
                ],
                "usage": {
                    "input_tokens": 20,
                    "output_tokens": 8,
                    "cache_creation_input_tokens": 10,
                    "cache_read_input_tokens": 5,
                },
            },
        )

    budget_type = NativeRunBudget if native_accounting else RunBudget
    tracker = UsageTracker(budget_type(0.05, 2, 0.01), model_id="anthropic/claude-haiku-5-5")
    with (
        anthropic.Anthropic(
            api_key="test",
            base_url="https://api.anthropic.com",
            http_client=httpx2.Client(transport=httpx2.MockTransport(handle)),
        ) as client,
        tracing_context(enabled=False),
    ):
        monkeypatch.setattr(model, "_client", client)
        result = model.with_structured_output(schema).invoke("Grade this", config={"callbacks": [tracker]})
    assert result == {"rating": 2}
    assert len(requests) == 1
    assert tracker.report()["input_tokens"] == 35
    assert tracker.report()["output_tokens"] == 8
    assert tracker.report()["usage_complete"]
    assert tracker.report()["cost_usd"] is None
    assert not tracker.report()["cost_complete"]
    assert tracker.budget.can_admit() is native_accounting
    if native_accounting:
        assert tracker.report()["estimate_complete"]
        assert tracker.report()["estimated_cost_usd"] == pytest.approx(0.000055)


def test_anthropic_does_not_silently_ignore_openai_options():
    with pytest.raises(ValueError, match="Messages API"):
        build_model("anthropic/claude-haiku-5-5", responses_api=True)
    with pytest.raises(ValueError, match="reasoning effort"):
        build_model("anthropic/claude-haiku-5-5", reasoning_effort="minimal")
