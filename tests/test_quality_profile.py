import polars as pl

from backintel.bench.quality import frame_profile, unmatched_rows


def test_provenance_does_not_hide_business_duplicates_and_null_is_not_zero():
    frame = pl.DataFrame(
        {"id": [1, 1, 2], "amount": [0, 0, None], "source_sheet": ["first", "second", "second"]}
    )
    profile = frame_profile(frame, keys=["id"])
    assert profile["exact_duplicate_surplus"] == 1
    assert profile["duplicate_key_surplus"] == 1
    assert profile["nulls"]["amount"] == 1
    assert "source_sheet" not in profile["columns"]


def test_unmatched_count_keeps_child_grain_and_deduplicates_parent_keys():
    parent = pl.DataFrame({"order_id": [1, 1, 2]})
    child = pl.DataFrame({"order_id": [1, 2, 3, 3, None], "amount": [1, 2, 3, 4, 5]})
    assert unmatched_rows(child, parent, "order_id") == 3
