from datetime import datetime

import polars as pl

from backintel.bench.replay import apply_planted, as_of, month_bounds, previous_period
from backintel.stores.multi import DIRECTIVE


def test_month_arithmetic():
    assert month_bounds("2018-12") == (datetime(2018, 12, 1), datetime(2019, 1, 1))
    assert previous_period("2018-01") == "2017-12"
    assert previous_period("2018-05") == "2018-04"


def test_planted_shift_applies_only_to_target_state_after_start():
    orders = pl.DataFrame(
        {
            "order_id": ["a", "b", "c"],
            "customer_id": ["c1", "c2", "c3"],
            "order_status": ["delivered"] * 3,
            "order_purchase_timestamp": [datetime(2018, 5, 2), datetime(2018, 4, 2), datetime(2018, 5, 3)],
            "order_delivered_customer_date": [
                datetime(2018, 5, 10),
                datetime(2018, 4, 10),
                datetime(2018, 5, 11),
            ],
        }
    )
    customers = pl.DataFrame({"customer_id": ["c1", "c2", "c3"], "customer_state": ["SP", "SP", "RJ"]})
    empty = pl.DataFrame({"order_id": pl.Series([], dtype=pl.Utf8)})
    frames = {
        "orders": orders,
        "customers": customers,
        "order_items": empty,
        "order_payments": empty,
        "order_reviews": empty,
    }
    shifted = apply_planted(frames)["orders"].sort("order_id")["order_delivered_customer_date"].to_list()
    assert shifted == [datetime(2018, 5, 17), datetime(2018, 4, 10), datetime(2018, 5, 11)]
    cut = as_of(frames, "2018-04")
    assert cut["orders"]["order_id"].to_list() == ["b"]

    future = dict(frames)
    future["orders"] = orders.with_columns(
        pl.lit(datetime(2018, 6, 2)).alias("order_delivered_customer_date")
    )
    cutoff = as_of(future, "2018-05")
    assert cutoff["orders"]["order_delivered_customer_date"].null_count() == 3
    assert cutoff["orders"]["order_status"].to_list() == ["shipped"] * 3


def test_multi_store_directive_parsing():
    match = DIRECTIVE.match("-- store: postgres:olist_orders\nSELECT 1")
    assert match and match.group(1) == "postgres:olist_orders"
    assert DIRECTIVE.match("SELECT 1") is None
