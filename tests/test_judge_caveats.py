"""Prospective caveat scoring contract; these checks do not calibrate the live model."""

import pytest

from backintel.bench import judge
from backintel.contracts import AnalystAnswer


def stub_model(monkeypatch, assessment, *, declined=False):
    class Stub:
        def with_structured_output(self, schema):
            fields = schema["properties"]
            if declined:
                assert "caveats_material" not in fields
            else:
                caveat = fields["caveats_material"]
                assert caveat["required"] == ["reason", "verdict"]
                assert "rating" not in caveat["properties"]
                assert set(caveat["properties"]["verdict"]["enum"]) == set(judge.CAVEAT_SCORES)
            return self

        def invoke(self, prompt, config):
            rubric = judge.DECLINED_RUBRIC if declined else judge.RUBRIC
            result = {key: {"reason": "Controlled numeric assessment", "rating": 1} for key in rubric}
            if not declined:
                result["caveats_material"] = assessment
            return result

    monkeypatch.setattr(judge, "build_model", lambda *args, **kwargs: Stub())


@pytest.mark.parametrize(
    ("verdict", "score"),
    [
        ("none_established", 1.0),
        ("adequately_disclosed", 1.0),
        ("materially_incomplete", 0.5),
        ("omitted_or_denied", 0.0),
    ],
)
def test_caveat_category_has_one_fixed_score_and_retains_original_assessment(monkeypatch, verdict, score):
    assessment = {"reason": "Controlled category, not live semantics", "verdict": verdict}
    stub_model(monkeypatch, assessment)
    result = judge.judge_answer(
        "Describe the extract",
        AnalystAnswer(status="answered", method="Describe the supplied extract"),
        model_id="offline",
    )
    assert result["criteria"]["caveats_material"] == score
    assert result["assessments"]["caveats_material"] == assessment
    assert all(value == 0.5 for key, value in result["criteria"].items() if key != "caveats_material")
    assert result["score"] == round((1.5 + score) / 4, 3)


@pytest.mark.parametrize(
    "assessment", [{"reason": "Missing verdict"}, {"reason": "Unknown", "verdict": "uncertain"}]
)
def test_invalid_caveat_verdict_never_defaults_to_a_favorable_score(monkeypatch, assessment):
    stub_model(monkeypatch, assessment)
    with pytest.raises(KeyError):
        judge.judge_answer(
            "Describe the extract",
            AnalystAnswer(status="answered", method="Describe the supplied extract"),
            model_id="offline",
        )


def test_refusal_rubric_keeps_its_numeric_contract(monkeypatch):
    stub_model(monkeypatch, None, declined=True)
    result = judge.judge_answer(
        "What is profit?",
        AnalystAnswer(status="cannot_answer", method="Inspect source fields", reason="Costs are absent"),
        model_id="offline",
    )
    assert result["score"] == 0.5
    assert set(result["criteria"]) == set(judge.DECLINED_RUBRIC)
