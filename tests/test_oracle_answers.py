"""The committed reference answers are the benchmark's truth; keep them well-formed."""

from backintel.bench.oracle import ANSWERS_DIR, load_answers


def test_answers_exist_and_are_consistent():
    for dataset in ("online_retail_ii", "olist", "tpch_sf1"):
        assert (ANSWERS_DIR / f"{dataset}.json").exists()
        scenarios = load_answers(dataset)
        ids = [s.id for s in scenarios]
        assert len(ids) == len(set(ids))
        assert {1, 2, 3} <= {s.level for s in scenarios} or {s.level for s in scenarios} == {7}
        for s in scenarios:
            assert s.question.strip().endswith("?") or s.question.strip().endswith(".")
            if s.answerable:
                assert s.expected is not None, s.id
            else:
                assert s.expected is None and "unanswerable" in s.tags, s.id
            if s.answer_type == "ranked_list":
                assert isinstance(s.expected, list) and all(isinstance(x, str) for x in s.expected)
            if s.answer_type == "table":
                assert isinstance(s.expected, list) and isinstance(s.expected[0], dict)
