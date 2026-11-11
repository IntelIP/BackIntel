"""Ambient replay: monthly as-of snapshots of a dataset with planted, labelled changes.

A standing question is asked once per period against the snapshot of that period. Planted
changes are applied to the canonical frames before the as-of cut, so the oracle and the stores
see the same world. Every planted change is recorded in the answers file, so a scorecard can
always say which detections were planted and which arose naturally in the data.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import polars as pl

PERIODS = ["2018-01", "2018-02", "2018-03", "2018-04", "2018-05", "2018-06", "2018-07", "2018-08"]
REPEAT_PERIODS = ["2017-09", "2017-12", "2018-03"]  # simulated quarterly reviews
CATEGORY_PERIODS = ["2018-06-07", "2018-06-14", "2018-06-21"]  # simulated weekly reviews
SNAPSHOT_PERIODS = sorted(set(PERIODS + REPEAT_PERIODS + CATEGORY_PERIODS))
# One persistent shift: from May 2018 on, orders by customers in SP take seven more days to arrive.
PLANTED = [
    {
        "id": "sp-delivery-plus-7d",
        "kind": "delivery_shift",
        "customer_state": "SP",
        "from": "2018-05-01",
        "days": 7,
        "description": "order_delivered_customer_date += 7 days for SP customers' orders purchased on or "
        "after 2018-05-01 (persistent step change)",
    },
]
MIN_ORDERS = 200  # states compared only when both months have at least this many delivered orders
MATERIAL_CHANGE = 0.25  # relative change in mean delivery days that counts as material


def month_bounds(period: str) -> tuple[datetime, datetime]:
    start = datetime.strptime(period, "%Y-%m")
    end = datetime(start.year + (start.month == 12), start.month % 12 + 1, 1)
    return start, end


def previous_period(period: str) -> str:
    start, _ = month_bounds(period)
    prev = datetime(start.year - (start.month == 1), (start.month - 2) % 12 + 1, 1)
    return prev.strftime("%Y-%m")


def apply_planted(frames: dict[str, pl.DataFrame]) -> dict[str, pl.DataFrame]:
    frames = dict(frames)
    for change in PLANTED:
        if change["kind"] != "delivery_shift":
            raise ValueError(change["kind"])
        state_orders = (
            frames["orders"]
            .join(frames["customers"].select("customer_id", "customer_state"), on="customer_id")
            .filter(
                (pl.col("customer_state") == change["customer_state"])
                & (pl.col("order_purchase_timestamp") >= datetime.fromisoformat(change["from"]))
            )
            .select("order_id")
            .with_columns(pl.lit(True).alias("_shift"))
        )
        frames["orders"] = (
            frames["orders"]
            .join(state_orders, on="order_id", how="left")
            .with_columns(
                pl.when(
                    pl.col("_shift").fill_null(False) & pl.col("order_delivered_customer_date").is_not_null()
                )
                .then(pl.col("order_delivered_customer_date") + timedelta(days=change["days"]))
                .otherwise(pl.col("order_delivered_customer_date"))
                .alias("order_delivered_customer_date")
            )
            .drop("_shift")
        )
    return frames


def as_of(frames: dict[str, pl.DataFrame], period: str) -> dict[str, pl.DataFrame]:
    """Everything known by the end of `period`: orders purchased before the next month, and their rows."""
    end = (
        datetime.strptime(period, "%Y-%m-%d") + timedelta(days=1)
        if len(period) == 10
        else month_bounds(period)[1]
    )
    orders = frames["orders"].filter(pl.col("order_purchase_timestamp") < end)
    # Observations that had not arrived at the cutoff cannot inform that run. The estimated
    # delivery date is a prediction known at purchase and is deliberately retained.
    delivery = "order_delivered_customer_date"
    if delivery in orders.columns:
        orders = orders.with_columns(
            pl.when(pl.col(delivery) >= end)
            .then(pl.lit("shipped"))
            .otherwise(pl.col("order_status"))
            .alias("order_status")
        )
    for column in ("order_approved_at", "order_delivered_carrier_date", delivery):
        if column in orders.columns:
            orders = orders.with_columns(
                pl.when(pl.col(column) >= end).then(None).otherwise(pl.col(column)).alias(column)
            )
    keep = orders.select("order_id")
    out = dict(frames)
    out["orders"] = orders
    for table in ("order_items", "order_payments", "order_reviews"):
        out[table] = frames[table].join(keep, on="order_id", how="inner")
    reviews = out["order_reviews"]
    if "review_creation_date" in reviews.columns:
        reviews = reviews.filter(pl.col("review_creation_date") < end)
    if "review_answer_timestamp" in reviews.columns:
        reviews = reviews.filter(
            pl.col("review_answer_timestamp").is_null() | (pl.col("review_answer_timestamp") < end)
        )
    out["order_reviews"] = reviews
    return out


def replay_frames(frames: dict[str, pl.DataFrame], period: str) -> dict[str, pl.DataFrame]:
    return as_of(apply_planted(frames), period)


def snapshot_name(period: str) -> str:
    return f"olist_asof_{period}"


def delivery_by_state(frames: dict[str, pl.DataFrame], period: str) -> pl.DataFrame:
    """Mean delivery days per customer state for orders purchased in `period` (delivered, dated)."""
    start, end = month_bounds(period)
    days = (
        pl.col("order_delivered_customer_date") - pl.col("order_purchase_timestamp")
    ).dt.total_seconds() / 86400
    return (
        frames["orders"]
        .filter(
            (pl.col("order_status") == "delivered")
            & pl.col("order_delivered_customer_date").is_not_null()
            & (pl.col("order_purchase_timestamp") >= start)
            & (pl.col("order_purchase_timestamp") < end)
        )
        .join(frames["customers"].select("customer_id", "customer_state"), on="customer_id")
        .group_by("customer_state")
        .agg(pl.len().alias("orders"), days.mean().alias("avg_days"))
    )


def material_changes(frames: dict[str, pl.DataFrame], period: str) -> pl.DataFrame:
    """States whose mean delivery time moved by more than MATERIAL_CHANGE between the two months."""
    current = delivery_by_state(frames, period)
    before = delivery_by_state(frames, previous_period(period))
    joined = current.join(before, on="customer_state", suffix="_prev").filter(
        (pl.col("orders") >= MIN_ORDERS) & (pl.col("orders_prev") >= MIN_ORDERS)
    )
    joined = joined.with_columns(
        ((pl.col("avg_days") - pl.col("avg_days_prev")) / pl.col("avg_days_prev")).alias("change")
    )
    return joined.sort("customer_state")


def replay_facts(frames: dict[str, pl.DataFrame], period: str) -> list[dict]:
    world = replay_frames(frames, period)
    table = material_changes(world, period)
    flagged = table.filter(pl.col("change").abs() > MATERIAL_CHANGE)
    facts = [
        {
            "name": "status",
            "value": "CHANGE_DETECTED" if flagged.height else "NO_CHANGE",
            "rel": None,
            "abs": None,
        }
    ]
    for row in table.iter_rows(named=True):
        state = row["customer_state"]
        if abs(row["change"]) > MATERIAL_CHANGE:
            facts.append({"name": f"changed_state_{state}", "value": state, "rel": None, "abs": None})
        for metric, column in (
            (f"avg_days_{state}_current", "avg_days"),
            (f"avg_days_{state}_previous", "avg_days_prev"),
            (f"relative_change_{state}", "change"),
        ):
            facts.append({"name": metric, "value": float(row[column]), "rel": 0.01, "abs": 0.0001})
    return facts


def replay_question(period: str) -> str:
    prev = previous_period(period)
    return (
        f"Standing question for the {period} run: did delivery performance change materially by customer "
        f"state? Compare orders purchased in {period} with orders purchased in {prev}, using orders with "
        "status 'delivered' that have a customer delivery date, and the average delivery time in fractional "
        "days from purchase to customer delivery. Consider only states (two-letter codes) with at least 200 "
        "such orders in both months; a material change is a relative change of more than 25% in the average. "
        "Return a report with metric/value/unit rows: avg_days_STATE_current, avg_days_STATE_previous, "
        "and relative_change_STATE for every considered state, replacing STATE with its code; then a "
        "row with metric 'status' and value CHANGE_DETECTED or NO_CHANGE, and one row with metric "
        "'changed_state_STATE' per state that changed materially (value = the state code). "
        "Note anything else in "
        "the data that affects the reading."
    )
