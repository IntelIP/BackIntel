import asyncio
import json

import httpx
import pytest
from langchain_core.messages import HumanMessage, ToolMessage
from langsmith import tracing_context
from openai import AsyncOpenAI, OpenAI

from backintel.bench.usage import BudgetExceeded, RunBudget, UsageTracker
from backintel.models import ModelPolicyError, build_model, parse_model_id, usage_from_message


def test_parse_model_id():
    assert parse_model_id("openrouter/openai/gpt-6-luna") == ("openrouter", "openai/gpt-6-luna")
    with pytest.raises(ValueError):
        parse_model_id("gpt-6-luna")


def test_openrouter_vendor_policy():
    env = {"OPENROUTER_API_KEY": "test"}
    assert build_model("openrouter/openai/gpt-6-luna", env=env).model_name == "openai/gpt-6-luna"
    with pytest.raises(ModelPolicyError):
        build_model("openrouter/z-ai/glm-5.2", env=env)
    with pytest.raises(ModelPolicyError):
        build_model("openrouter/deepseek/deepseek-v4", env=env)


def test_budgeted_model_can_disable_provider_retries():
    model = build_model("openrouter/openai/gpt-6-luna", env={"OPENROUTER_API_KEY": "test"}, max_retries=0)
    assert model.max_retries == 0
    with pytest.raises(ValueError, match="non-negative"):
        build_model("openrouter/openai/gpt-6-luna", max_retries=-1)


def response_fixture(index, cost=0.002):
    """OpenRouter terminal Responses shape, parsed by the real OpenAI SDK in these tests."""
    result = {
        "id": f"resp_test_{index}",
        "object": "response",
        "created_at": 1,
        "status": "completed",
        "error": None,
        "incomplete_details": None,
        "instructions": None,
        "model": "openai/test-model-not-invoked",
        "parallel_tool_calls": False,
        "temperature": 1,
        "tool_choice": "auto",
        "tools": [],
        "top_p": 1,
        "provider": "OpenAI",
        "endpoint_id": "openai/test-endpoint",
        "usage": {
            "input_tokens": 10,
            "output_tokens": 4,
            "total_tokens": 14,
            "input_tokens_details": {"cached_tokens": 2},
            "output_tokens_details": {"reasoning_tokens": 2},
            "cost_details": {"upstream_inference_cost": 0.012},
        },
        "output": (
            [
                {"id": "rs_test", "type": "reasoning", "summary": [], "encrypted_content": "opaque"},
                {
                    "id": "fc_test",
                    "type": "function_call",
                    "call_id": "call_test",
                    "name": "read_metric",
                    "arguments": "{}",
                    "status": "completed",
                },
            ]
            if index == 1
            else [
                {
                    "id": "msg_test",
                    "type": "message",
                    "role": "assistant",
                    "status": "completed",
                    "content": [{"type": "output_text", "text": "Done", "annotations": []}],
                }
            ]
        ),
    }
    if cost is not None:
        result["usage"]["cost"] = cost
    return result


def responses_model():
    return build_model(
        "openrouter/openai/test-model-not-invoked",
        env={"OPENROUTER_API_KEY": "test-placeholder"},
        responses_api=True,
        reasoning_effort="medium",
        first_party_only=True,
        max_retries=0,
    )


@pytest.mark.parametrize("asynchronous", [False, True])
def test_responses_tool_turns_preserve_billing_reasoning_and_budget_admission(monkeypatch, asynchronous):
    model = responses_model()
    requests = []

    def handle(request):
        assert request.url.path == "/api/v1/responses"
        requests.append(json.loads(request.content))
        return httpx.Response(
            200,
            json=response_fixture(len(requests), 0.002 if len(requests) == 1 else 0.003),
            headers={"x-request-id": f"gateway-{len(requests)}"},
        )

    bound = model.bind_tools(
        [{"type": "function", "function": {"name": "read_metric", "parameters": {"type": "object"}}}]
    )
    budget = RunBudget(0.05, 2, 0.01)
    tracker = UsageTracker(budget)
    config = {"callbacks": [tracker]}
    messages = [HumanMessage(content="Read the metric")]

    async def async_turns():
        async with AsyncOpenAI(
            api_key="test-placeholder",
            base_url="https://openrouter.ai/api/v1",
            http_client=httpx.AsyncClient(transport=httpx.MockTransport(handle)),
        ) as client:
            monkeypatch.setattr(model, "root_async_client", client)
            first = await bound.ainvoke(messages, config=config)
            second = await bound.ainvoke(
                [*messages, first, ToolMessage(content="135", tool_call_id="call_test")], config=config
            )
            with pytest.raises(BudgetExceeded):
                await bound.ainvoke(messages, config=config)
            return first, second

    with tracing_context(enabled=False):
        if asynchronous:
            first, second = asyncio.run(async_turns())
        else:
            with OpenAI(
                api_key="test-placeholder",
                base_url="https://openrouter.ai/api/v1",
                http_client=httpx.Client(transport=httpx.MockTransport(handle)),
            ) as client:
                monkeypatch.setattr(model, "root_client", client)
                first = bound.invoke(messages, config=config)
                second = bound.invoke(
                    [*messages, first, ToolMessage(content="135", tool_call_id="call_test")], config=config
                )
                with pytest.raises(BudgetExceeded):
                    bound.invoke(messages, config=config)
    assert len(requests) == 2
    assert all(request.get("stream") is not True and "usage" not in request for request in requests)
    assert first.tool_calls[0]["id"] == "call_test"
    assert any(item.get("encrypted_content") == "opaque" for item in requests[1]["input"])
    assert any(item.get("type") == "function_call_output" for item in requests[1]["input"])
    assert first.response_metadata["id"] == "resp_test_1"
    assert first.response_metadata["gateway_request_id"] == "gateway-1"
    assert first.response_metadata["provider"] == "OpenAI"
    assert first.response_metadata["endpoint_id"] == "openai/test-endpoint"
    assert first.response_metadata["responses_usage"]["cost_details"]["upstream_inference_cost"] == 0.012
    assert first.usage_metadata["output_token_details"]["reasoning"] == 2
    assert usage_from_message(second)["cost_usd"] == 0.003
    assert tracker.report()["input_tokens"] == 20
    assert tracker.report()["output_tokens"] == 8
    assert tracker.report()["cost_usd"] == pytest.approx(0.005)
    assert tracker.report()["usage_complete"] and tracker.report()["cost_complete"]
    assert budget.spent_usd == pytest.approx(0.005)
    assert budget.reserved_usd == pytest.approx(0)


@pytest.mark.parametrize("cost", [None, 0, "unknown", -1])
def test_responses_missing_account_charge_stays_unknown_despite_upstream_cost(monkeypatch, cost):
    model = responses_model()
    requests = []

    def handle(request):
        requests.append(request)
        return httpx.Response(200, json=response_fixture(2, cost))

    budget = RunBudget(0.05, 2, 0.01)
    tracker = UsageTracker(budget)
    with (
        OpenAI(
            api_key="test-placeholder",
            base_url="https://openrouter.ai/api/v1",
            http_client=httpx.Client(transport=httpx.MockTransport(handle)),
        ) as client,
        tracing_context(enabled=False),
    ):
        monkeypatch.setattr(model, "root_client", client)
        result = model.invoke("test", config={"callbacks": [tracker]})
        assert usage_from_message(result)["cost_usd"] == (0 if cost == 0 else None)
        assert tracker.report()["usage_complete"]
        assert tracker.report()["input_tokens"] == 10
        if cost == 0:
            assert tracker.report()["cost_usd"] == 0
            assert budget.can_admit()
        else:
            assert tracker.report()["cost_usd"] is None
            assert not tracker.report()["cost_complete"]
            with pytest.raises(BudgetExceeded):
                model.invoke("must not be sent", config={"callbacks": [tracker]})
    assert len(requests) == 1


def test_specialist_responses_payload_preserves_reasoning_and_restricts_endpoints():
    model = build_model(
        "openrouter/openai/gpt-6.1-sol",
        env={"OPENROUTER_API_KEY": "test"},
        max_retries=0,
        responses_api=True,
        reasoning_effort="medium",
        first_party_only=True,
    )
    payload = model._get_request_payload([{"role": "user", "content": "Analyze the assigned data"}])
    assert payload["reasoning"] == {"effort": "medium"}
    assert payload["store"] is False
    assert "reasoning.encrypted_content" in payload["include"]
    assert payload["extra_body"]["provider"] == {
        "only": ["openai"],
        "allow_fallbacks": False,
        "require_parameters": True,
    }
    assert model.max_retries == 0
    assert "usage" not in payload["extra_body"]
    assert model.disable_streaming is True
