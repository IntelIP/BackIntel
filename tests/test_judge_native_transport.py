"""Exercise the native judge's actual SDK payload and parser without model calls."""

import json
from contextlib import nullcontext

import anthropic
import httpx2
import pytest
from langsmith import tracing_context

from backintel.bench import judge
from backintel.bench.usage import NativeRunBudget, UsageTracker
from backintel.contracts import AnalystAnswer
from backintel.models import build_model


@pytest.mark.parametrize("declined", [False, True])
@pytest.mark.parametrize("stop_reason", ["end_turn", "max_tokens"])
def test_native_judge_uses_json_output_without_forcing_tool_or_disabling_thinking(
    monkeypatch, declined, stop_reason
):
    model_id = "anthropic/claude-haiku-5-5"
    model = build_model(
        model_id,
        env={"ANTHROPIC_API_KEY": "offline-test", "BACKINTEL_MAX_COMPLETION_TOKENS": "2048"},
        max_retries=0,
    )
    rubric = judge.DECLINED_RUBRIC if declined else judge.RUBRIC
    assessment = {key: {"reason": "Controlled parser fixture", "rating": 2} for key in rubric}
    if not declined:
        assessment["caveats_material"] = {
            "reason": "Controlled partial scope",
            "verdict": "materially_incomplete",
        }
    requests = []

    def handle(request):
        assert request.url.host == "api.anthropic.com"
        assert request.url.path == "/v1/messages"
        payload = json.loads(request.content)
        requests.append(payload)
        assert payload["model"] == "claude-haiku-5-5"
        assert payload["max_tokens"] == 2048
        assert payload["service_tier"] == "standard_only"
        assert "tools" not in payload and "tool_choice" not in payload
        # Haiku 5.5 defaults to adaptive thinking and medium effort. Keep both.
        assert "thinking" not in payload
        assert "effort" not in payload["output_config"]
        output_format = payload["output_config"]["format"]
        assert output_format["type"] == "json_schema"
        assert set(output_format["schema"]["required"]) == set(rubric)
        return httpx2.Response(
            200,
            json={
                "id": "msg_judge_transport_test",
                "type": "message",
                "role": "assistant",
                "model": "claude-haiku-5-5",
                "stop_reason": stop_reason,
                "stop_sequence": None,
                "content": [
                    {"type": "thinking", "thinking": "", "signature": "test-signature"},
                    {"type": "text", "text": json.dumps(assessment)},
                ],
                "usage": {
                    "input_tokens": 100,
                    "output_tokens": 80,
                    "cache_creation_input_tokens": 0,
                    "cache_read_input_tokens": 0,
                },
            },
        )

    def configured_model(requested_id, max_retries):
        assert requested_id == model_id
        assert max_retries == 0
        return model

    monkeypatch.setattr(judge, "build_model", configured_model)
    tracker = UsageTracker(NativeRunBudget(0.12, 6, 0.02), model_id=model_id)
    with (
        anthropic.Anthropic(
            api_key="offline-test",
            base_url="https://api.anthropic.com",
            http_client=httpx2.Client(transport=httpx2.MockTransport(handle)),
        ) as client,
        tracing_context(enabled=False),
    ):
        monkeypatch.setattr(model, "_client", client)
        expected = (
            pytest.raises(ValueError, match="did not complete")
            if stop_reason == "max_tokens"
            else nullcontext()
        )
        with expected:
            result = judge.judge_answer(
                "Describe the requested population",
                AnalystAnswer(status="cannot_answer" if declined else "answered", method="Test fixture"),
                model_id=model_id,
                max_retries=0,
                callbacks=[tracker],
            )
    assert len(requests) == 1
    if stop_reason == "end_turn":
        assert result["assessments"] == assessment
        assert result["score"] == (1.0 if declined else 0.875)
    assert tracker.report()["estimate_complete"]
    assert tracker.report()["input_tokens"] == 100
    assert tracker.report()["output_tokens"] == 80
    assert tracker.report()["estimated_cost_usd"] == pytest.approx(0.0003)
    assert tracker.report()["cost_usd"] is None


def test_openrouter_judge_keeps_its_existing_transport(monkeypatch):
    class ExistingTransport:
        def with_structured_output(self, schema, **options):
            assert options == {}
            return self

        def invoke(self, prompt, config):
            result = {key: {"reason": "Controlled fixture", "rating": 2} for key in judge.RUBRIC}
            result["caveats_material"] = {"reason": "Controlled fixture", "verdict": "none_established"}
            return result

    monkeypatch.setattr(judge, "build_model", lambda *args, **kwargs: ExistingTransport())
    assert (
        judge.judge_answer(
            "Describe the extract",
            AnalystAnswer(status="answered", method="Test fixture"),
            model_id="openrouter/anthropic/claude-haiku-5.5",
        )["score"]
        == 1.0
    )
