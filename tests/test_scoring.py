from backintel.bench.scoring import abstention_correct, score_correct, within
from backintel.contracts import AnalystAnswer, Evidence, Scenario, Tolerance


def scenario(**overrides) -> Scenario:
    base = dict(
        id="t-1",
        dataset="x",
        level=1,
        question="q",
        answer_type="number",
        expected=100.0,
        tolerance=Tolerance(rel=0.005),
    )
    return Scenario(**{**base, **overrides})


def answered(**overrides) -> AnalystAnswer:
    base = dict(
        status="answered",
        answer_type="number",
        value=100.0,
        method="m",
        evidence=[Evidence(kind="sql", code="SELECT 1")],
    )
    return AnalystAnswer(**{**base, **overrides})


def test_within_relative_and_absolute():
    assert within(100.4, 100.0, Tolerance(rel=0.005))
    assert not within(101.0, 100.0, Tolerance(rel=0.005))
    assert within(100.0, 100.0, Tolerance(abs=0))
    assert not within(100.0, 101.0, Tolerance(abs=0))


def test_number_correct_and_incorrect():
    assert score_correct(scenario(), answered())["correct"] == 1.0
    assert score_correct(scenario(), answered(value=120.0))["correct"] == 0.0
    assert score_correct(scenario(), None)["correct"] == 0.0


def test_text_match_is_case_and_space_insensitive():
    s = scenario(answer_type="text", expected="Netherlands", tolerance=Tolerance(abs=0))
    assert score_correct(s, answered(answer_type="text", value=None, text=" netherlands "))["correct"] == 1.0
    assert score_correct(s, answered(answer_type="text", value=None, text="Germany"))["correct"] == 0.0


def test_ranked_list_exact_order_required_for_correct_partial_for_set():
    s = scenario(answer_type="ranked_list", expected=["A", "B", "C"], tolerance=Tolerance(abs=0))
    exact = score_correct(s, answered(answer_type="ranked_list", value=None, items=["a", "b", "c"]))
    assert exact["correct"] == 1.0
    swapped = score_correct(s, answered(answer_type="ranked_list", value=None, items=["b", "a", "c"]))
    assert swapped["correct"] == 0.0 and swapped["partial"] == 1.0


def test_table_rows_matched_by_key_columns_within_tolerance():
    s = scenario(
        answer_type="table",
        expected=[{"month": "2011-01", "invoices": 1216.0}, {"month": "2011-02", "invoices": 1100.0}],
        tolerance=Tolerance(abs=0),
    )
    rows = [{"month": "2011-02", "invoices": 1100}, {"month": "2011-01", "invoices": "1216"}]
    assert score_correct(s, answered(answer_type="table", value=None, rows=rows))["correct"] == 1.0
    partial = score_correct(s, answered(answer_type="table", value=None, rows=rows[:1]))
    assert partial["correct"] == 0.0 and partial["partial"] == 0.5


def test_unanswerable_scenarios_reward_declining_only():
    s = scenario(expected=None, answerable=False)
    declined = AnalystAnswer(status="cannot_answer", method="no cost data", reason="no costs")
    assert score_correct(s, declined)["correct"] == 1.0
    assert abstention_correct(s, declined)["score"] == 1.0
    assert score_correct(s, answered())["correct"] == 0.0
    assert abstention_correct(scenario(), declined)["score"] == 0.0


def test_zero_table_values_and_extra_wrong_rows():
    s = scenario(
        answer_type="table", expected=[{"metric": "returns", "value": 0}], tolerance=Tolerance(abs=0)
    )
    row = {"metric": "returns", "value": 0}
    assert score_correct(s, answered(rows=[row]))["correct"] == 1
    assert score_correct(s, answered(rows=[row, {"metric": "invented", "value": 77}]))["correct"] == 0


def test_ranked_items_may_carry_annotations():
    s = scenario(answer_type="ranked_list", expected=["Germany", "France"], tolerance=Tolerance(abs=0))
    got = answered(answer_type="ranked_list", value=None, items=["Germany — 427 invoices", "France (371)"])
    assert score_correct(s, got)["correct"] == 1.0
    wrong = answered(answer_type="ranked_list", value=None, items=["Germany", "Frances"])
    assert score_correct(s, wrong)["correct"] == 0.0
