import pytest

from backintel.models import ModelPolicyError, build_model, parse_model_id


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
