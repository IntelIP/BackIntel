import json

import pytest

from backintel.bench.calibration import assess_calibration, write_review_packet
from backintel.bench.judge import RUBRIC


def packet(tmp_path):
    record = {
        "question": "q",
        "scenario_id": "case",
        "outputs": {
            "answer": {
                "status": "answered",
                "value": 4,
                "method": "counted rows",
                "evidence": [{"kind": "sql", "code": "select count(*) from events"}],
            }
        },
        "judge_criteria": dict.fromkeys(RUBRIC, 1),
        "scores": {"judge_method": 1},
    }
    target = tmp_path / "review"
    write_review_packet([record], target)
    return target, *(
        json.loads((target / name).read_text())
        for name in ("packet.json", "human-labels.json", "judge-ratings.json")
    )


def test_unreviewed_packet_cannot_appear_calibrated_and_does_not_reveal_model_grades(tmp_path):
    target, data, labels, judges = packet(tmp_path)
    assert assess_calibration(data, labels, judges)["status"] == "awaiting_human_review"
    text = (target / "review.md").read_text()
    assert "<details>" in text and "counted rows" in text
    assert "judge_method" not in text and "judge_criteria" not in text
    assert "review-01:" in text


def test_real_labels_report_disagreements_and_packet_tampering_fails(tmp_path):
    _, data, labels, judges = packet(tmp_path)
    labels.update(reviewer="human-test-fixture", reviewed_at="2026-11-11T00:00:00Z")
    labels["cases"]["review-01"]["ratings"] = dict.fromkeys(RUBRIC, 2)
    labels["cases"]["review-01"]["ratings"]["caveats_material"] = 1
    result = assess_calibration(data, labels, judges)
    assert result["status"] == "reviewed" and result["exact_agreement"] == 0.75
    assert result["disagreements"][0]["criterion"] == "caveats_material"
    labels["reviewer_type"] = "agent"
    with pytest.raises(ValueError, match="Agent labels"):
        assess_calibration(data, labels, judges)
    labels["reviewer_type"] = "human"
    data["cases"][0]["question"] = "changed"
    with pytest.raises(ValueError, match="changed"):
        assess_calibration(data, labels, judges)
