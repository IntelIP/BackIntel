from langchain_core.messages import AIMessage

from backintel.bench.run import Harness
from backintel.sandbox import PythonSandbox
from backintel.settings import Settings


def test_failed_agent_keeps_the_usage_already_reported():
    class FailingAgent:
        def stream(self, *args, **kwargs):
            yield {
                "messages": [
                    AIMessage(
                        content="",
                        usage_metadata={"input_tokens": 20, "output_tokens": 10, "total_tokens": 30},
                        response_metadata={"token_usage": {"cost": 0.001}},
                    )
                ]
            }
            raise RuntimeError("stopped after the first call")

    harness = Harness(Settings.from_env(), None, PythonSandbox(), "test", FailingAgent(), {}, False)
    result = harness.answer("test")
    assert result["error"] == "RuntimeError: stopped after the first call"
    assert result["metrics"]["llm_calls"] == 1
    assert result["metrics"]["input_tokens"] == 20
    assert result["metrics"]["cost_usd"] == 0.001
    assert result["metrics"]["cost_complete"] is False
