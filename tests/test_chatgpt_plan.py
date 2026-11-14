"""Subscription transport and accounting checks; no live provider requests."""

import asyncio
import json
import time
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

import httpx
import pytest
from langchain_core.messages import HumanMessage, ToolMessage
from langsmith import tracing_context
from openai import AsyncOpenAI, OpenAI

from backintel.bench.usage import BudgetExceeded, PlanRunBudget, UsageTracker
from backintel.providers import chatgpt_plan as plan


def credentials(tmp_path):
    saved = plan.PlanCredentials(tmp_path)
    saved.save(
        {
            "client_id": "test-client",
            "access_token": "test-token-not-live",
            "refresh_token": "test-refresh-not-live",
            "scopes": plan.SCOPES.split(),
            "expires_at": time.time() + 3600,
        }
    )
    return saved


def test_current_oauth_scopes_and_returning_registration_are_bound(tmp_path):
    saved = plan.PlanCredentials(tmp_path)
    url, attempt = plan.authorization_request(saved, "http://127.0.0.1:1456/auth/callback")
    query = parse_qs(urlsplit(url).query)
    assert url.startswith("https://auth.openai.com/api/accounts/authorize?")
    assert plan.TOKEN_URL == "https://auth.openai.com/api/accounts/oauth/token"
    assert {"chatgpt.tokens.use.direct", "resource.invoke", "offline_access"} <= set(
        query["scope"][0].split()
    )
    assert query["client_id"] == ["dynamic_agent_client"]
    assert query["ext_agent_host_id"] == [saved.host_id()]
    with pytest.raises(plan.SignInRequired, match="state"):
        plan.complete_sign_in(saved, attempt, {"state": "wrong"})
    saved = credentials(tmp_path)
    _, attempt = plan.authorization_request(saved, "http://127.0.0.1:1456/auth/callback")
    with pytest.raises(plan.SignInRequired, match="registration"):
        plan.complete_sign_in(saved, attempt, {"state": attempt["state"], "client_id": "other"})


def test_account_model_catalog_is_read_only_and_uses_saved_session(tmp_path, monkeypatch):
    saved = credentials(tmp_path)
    original = httpx.Client

    def handle(request):
        assert request.method == "GET" and str(request.url) == plan.RESOURCE + "/models"
        assert request.headers["Authorization"] == "Bearer test-token-not-live"
        return httpx.Response(
            200,
            json={
                "models": [
                    {"slug": "visible", "display_name": "Visible", "visibility": "list"},
                    {"slug": "hidden", "display_name": "Hidden", "visibility": "hidden"},
                ]
            },
        )

    monkeypatch.setattr(
        plan.httpx, "Client", lambda **kw: original(**kw, transport=httpx.MockTransport(handle))
    )
    assert saved.models() == [{"slug": "visible", "display_name": "Visible"}]


def test_analysis_cli_selects_subscription_budget_without_api_credentials(tmp_path, monkeypatch):
    from types import SimpleNamespace

    import backintel.analysis
    import backintel.models
    import backintel.stores
    from backintel.cli import main

    brief_path = tmp_path / "brief.json"
    brief_path.write_text(json.dumps({"objective": "Inspect assigned sales and build a report."}))
    observed = {}

    def model(model_id, **kwargs):
        observed.update(model_id=model_id, **kwargs)
        return object()

    async def run(brief, **kwargs):
        assert isinstance(kwargs["budget"], PlanRunBudget)
        assert kwargs["budget"].max_calls == 24
        return {"status": "completed", "usage": {"cost_usd": None}}

    monkeypatch.setattr(backintel.models, "build_model", model)
    monkeypatch.setattr(backintel.analysis, "run_analysis", run)
    monkeypatch.setattr(backintel.stores, "open_store", lambda *args: SimpleNamespace(close=lambda: None))
    monkeypatch.setenv("BACKINTEL_SANDBOX", "smolvm")
    monkeypatch.setenv("BACKINTEL_MODEL", "openrouter/openai/gpt-6-luna")
    monkeypatch.delenv("BACKINTEL_ANALYSIS_MODEL", raising=False)
    args = ["analyze", "--brief", str(brief_path), "--store", "test", "--output", str(tmp_path / "out")]
    main(args)
    assert observed["model_id"] == "chatgpt-plan/gpt-6.1-sol"
    assert observed["reasoning_effort"] == "medium"
    assert observed["first_party_only"] is False and observed["max_retries"] == 0

    monkeypatch.setenv("BACKINTEL_ANALYSIS_MODEL", "chatgpt-plan/gpt-6-luna")
    main(args)
    assert observed["model_id"] == "chatgpt-plan/gpt-6-luna"
    main(args + ["--model", "chatgpt-plan/gpt-6.1-sol", "--reasoning", "low"])
    assert observed["model_id"] == "chatgpt-plan/gpt-6.1-sol"
    assert observed["reasoning_effort"] == "low"
    with pytest.raises(ValueError, match="call limits"):
        main(args + ["--max-cost-usd", "3"])
    with pytest.raises(ValueError, match="requires"):
        main(args + ["--model", "openrouter/openai/test-not-invoked"])


@pytest.mark.parametrize("asynchronous", [False, True])
def test_real_sse_tool_turns_track_tokens_without_fake_dollar_cost(tmp_path, monkeypatch, asynchronous):
    requests = []

    def handle(request):
        assert request.url.path == "/v1/responses"
        body = json.loads(request.content)
        requests.append(body)
        index = len(requests)
        response = {
            "id": f"resp_plan_{index}",
            "object": "response",
            "created_at": 1,
            "status": "completed",
            "model": "test-model-not-invoked",
            "error": None,
            "incomplete_details": None,
            "usage": {"input_tokens": 10, "output_tokens": 4, "total_tokens": 14},
            "output": [
                {"id": "rs_test", "type": "reasoning", "summary": [], "encrypted_content": "opaque"},
                {
                    "id": "fc_test",
                    "type": "function_call",
                    "call_id": "call_test",
                    "name": "read_metric",
                    "namespace": "backintel",
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
            ],
        }
        event = {"type": "response.completed", "sequence_number": 1, "response": response}
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            text="event: response.completed\ndata: " + json.dumps(event) + "\n\n",
        )

    def client(**kwargs):
        return OpenAI(**kwargs, http_client=httpx.Client(transport=httpx.MockTransport(handle)))

    monkeypatch.setattr(plan, "OpenAI", client)
    monkeypatch.setattr(
        plan,
        "AsyncOpenAI",
        lambda **kw: AsyncOpenAI(**kw, http_client=httpx.AsyncClient(transport=httpx.MockTransport(handle))),
    )
    model = plan.plan_model("test-model-not-invoked", credentials(tmp_path), max_retries=0)
    bound = model.bind_tools(
        [
            {
                "name": "read_metric",
                "description": "Read a metric",
                "parameters": {
                    "type": "object",
                    "properties": {},
                },
            }
        ]
    )
    budget = PlanRunBudget(max_calls=2)
    tracker = UsageTracker(budget)
    messages = [HumanMessage(content="Read the metric.")]

    async def run():
        first = await bound.ainvoke(messages, config={"callbacks": [tracker]})
        messages.extend([first, ToolMessage(content="135", tool_call_id="call_test")])
        await bound.ainvoke(messages, config={"callbacks": [tracker]})

    with tracing_context(enabled=False):
        if asynchronous:
            asyncio.run(run())
        else:
            first = bound.invoke(messages, config={"callbacks": [tracker]})
            messages.extend([first, ToolMessage(content="135", tool_call_id="call_test")])
            bound.invoke(messages, config={"callbacks": [tracker]})
        with pytest.raises(BudgetExceeded):
            bound.invoke(messages, config={"callbacks": [tracker]})

    assert len(requests) == 2
    assert all(body["stream"] is True and body["store"] is False for body in requests)
    assert requests[0]["tools"][0]["type"] == "namespace"
    assert requests[1]["input"][1]["type"] == "reasoning"
    assert any(item.get("type") == "function_call_output" for item in requests[1]["input"])
    report = tracker.report()
    assert report["input_tokens"] == 20 and report["output_tokens"] == 8
    assert report["usage_complete"] and report["billing_mode"] == "chatgpt_plan"
    assert report["cost_usd"] is None and not report["cost_complete"]
    assert not report["cost_applicable"] and budget.calls == 2


def test_quota_failure_stops_campaign_without_retry_or_billing_fallback(tmp_path, monkeypatch):
    calls = []

    def failed(self, payload):
        calls.append(payload)
        return None, ("subscription_sharing_usage_unavailable", "Unavailable")

    monkeypatch.setattr(plan.PlanChatOpenAI, "_stream_once", failed)
    model = plan.plan_model("test-model-not-invoked", credentials(tmp_path), max_retries=0)
    budget = PlanRunBudget(8)
    tracker = UsageTracker(budget)
    with tracing_context(enabled=False), pytest.raises(plan.PlanUsageStopped):
        model.invoke("test", config={"callbacks": [tracker]})
    assert len(calls) == 1 and not budget.can_admit()
    assert tracker.report()["cost_usd"] is None
    assert not tracker.report()["usage_complete"]
    with pytest.raises(BudgetExceeded):
        budget.reserve()
    unknown = UsageTracker(PlanRunBudget(1))
    run_id = uuid4()
    unknown.on_chat_model_start({}, [], run_id=run_id)
    unknown.on_llm_error(RuntimeError("transport"), run_id=run_id)
    assert not unknown.budget.can_admit()


@pytest.mark.parametrize("stage", ["refresh", "stream"])
def test_async_plan_cancellation_closes_io_without_background_inference(tmp_path, monkeypatch, stage):
    saved = credentials(tmp_path)
    if stage == "refresh":
        saved.save(saved.load() | {"expires_at": 0})
    seen, stopped = [], []

    class Stream(httpx.AsyncByteStream):
        async def __aiter__(self):
            seen.append("stream")
            await asyncio.sleep(60)
            yield b"unreachable"

        async def aclose(self):
            stopped.append("stream")

    async def handle(request):
        if str(request.url) == plan.TOKEN_URL:
            seen.append("refresh")
            try:
                await asyncio.sleep(60)
            finally:
                stopped.append("refresh")
        assert stage == "stream", "Cancelled credential refresh must not start inference"
        return httpx.Response(200, headers={"content-type": "text/event-stream"}, stream=Stream())

    class MockClient(httpx.AsyncClient):
        def __init__(self, **kwargs):
            super().__init__(**kwargs, transport=httpx.MockTransport(handle))

    monkeypatch.setattr(plan.httpx, "AsyncClient", MockClient)
    monkeypatch.setattr(plan, "AsyncOpenAI", lambda **kw: AsyncOpenAI(**kw, http_client=MockClient()))
    model = plan.plan_model("test-model-not-invoked", saved, max_retries=0)

    async def run():
        with pytest.raises(TimeoutError):
            async with asyncio.timeout(0.2):
                await model.ainvoke("test")
        assert not [t for t in asyncio.all_tasks() if t is not asyncio.current_task() and not t.done()]

    started = time.monotonic()
    with tracing_context(enabled=False):
        asyncio.run(run())
    assert time.monotonic() - started < 2
    assert seen == [stage] and stopped == [stage]
    assert saved._lock.acquire(blocking=False)
    saved._lock.release()


def test_async_token_refresh_serializes_and_saves_rotated_credentials(tmp_path, monkeypatch):
    saved = credentials(tmp_path)
    saved.save(saved.load() | {"expires_at": 0})
    calls = []

    async def handle(request):
        calls.append(request)
        await asyncio.sleep(0)
        return httpx.Response(
            200,
            json={
                "access_token": "renewed-test-token",
                "refresh_token": "rotated-test-token",
                "expires_in": 3600,
            },
        )

    class MockClient(httpx.AsyncClient):
        def __init__(self, **kwargs):
            super().__init__(**kwargs, transport=httpx.MockTransport(handle))

    monkeypatch.setattr(plan.httpx, "AsyncClient", MockClient)

    async def run():
        return await asyncio.gather(saved.aaccess_token(), saved.aaccess_token())

    assert asyncio.run(run()) == ["renewed-test-token", "renewed-test-token"]
    assert len(calls) == 1 and str(calls[0].url) == plan.TOKEN_URL
    assert saved.load()["refresh_token"] == "rotated-test-token"
