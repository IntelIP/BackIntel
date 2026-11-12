from backintel.bench.scoring import replay_status, report_facts_found, score_correct
from backintel.contracts import AnalystAnswer, Evidence, Scenario, Tolerance

FACTS = [
    {"name": "repeat_share", "value": 0.0312, "rel": 0.005, "abs": None},
    {"name": "avg_orders", "value": 2.116, "rel": 0.005, "abs": None},
    {"name": "best_month", "value": "2017-11", "rel": None, "abs": None},
]


def report(rows):
    return AnalystAnswer(
        status="answered",
        answer_type="report",
        rows=rows,
        method="m",
        evidence=[Evidence(kind="sql", code="SELECT 1")],
    )


def test_report_facts_require_the_correct_metric_and_value():
    scenario = Scenario(
        id="p",
        dataset="olist",
        level=5,
        question="q",
        answer_type="report",
        expected=FACTS,
        tolerance=Tolerance(rel=0.005),
    )
    good = report(
        [
            {"metric": "repeat_share", "value": 0.03119, "unit": "share"},
            {"metric": "avg_orders", "value": 2.1161, "unit": "orders"},
            {"metric": "best_month", "value": "2017-11", "unit": None},
        ]
    )
    assert score_correct(scenario, good)["correct"] == 1.0
    partial = report([{"metric": "repeat_share", "value": 0.0312, "unit": "share"}])
    scored = score_correct(scenario, partial)
    assert scored["correct"] == 0.0 and abs(scored["partial"] - 1 / 3) < 1e-9
    found, missing = report_facts_found(FACTS, partial)
    assert [f["name"] for f in found] == ["repeat_share"] and missing == ["avg_orders", "best_month"]


def test_swapping_correct_values_between_metrics_is_wrong():
    rows = [
        {"metric": "repeat_share", "value": 2.116},
        {"metric": "avg_orders", "value": 0.0312},
        {"metric": "best_month", "value": "2017-11"},
    ]
    found, missing = report_facts_found(FACTS, report(rows))
    assert [f["name"] for f in found] == ["best_month"]
    assert missing == ["repeat_share", "avg_orders"]


def test_replay_status_can_be_derived_from_reproduced_changes():
    assert replay_status(report([{"metric": "relative_change_SP", "value": 0.1}])) == "NO_CHANGE"
    assert replay_status(report([{"metric": "relative_change_SP", "value": -0.3}])) == "CHANGE_DETECTED"
    assert replay_status(report([])) is None
