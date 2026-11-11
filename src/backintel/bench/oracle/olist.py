"""Olist scenarios. Nine tables (geolocation excluded from stores), ~100k orders, Sep 2016 to Oct 2018.

Known mess, used deliberately: 8 delivered orders without a delivery date; 3 category names
without an English translation (one is null); 2,961 orders with several payment records;
duplicate review ids; `customer_id` is per order while `customer_unique_id` identifies people.
"""

from __future__ import annotations

from functools import partial

import polars as pl

from backintel.bench.oracle import EXACT, MONEY, RATIO, Frames, Spec, _scalar
from backintel.bench.replay import (
    CATEGORY_PERIODS,
    PERIODS,
    REPEAT_PERIODS,
    replay_facts,
    replay_frames,
    replay_question,
    snapshot_name,
)

DELIVERED = pl.col("order_status") == "delivered"


def delivered_orders(f: Frames) -> pl.DataFrame:
    return f["orders"].filter(DELIVERED)


# ---------------------------------------------------------------- level 1
def delivered_count(f):
    return float(delivered_orders(f).height)


def unique_customers(f):
    return float(f["customers"]["customer_unique_id"].n_unique())


def top_payment_type(f):
    return f["order_payments"].group_by("payment_type").len().sort("len", descending=True)["payment_type"][0]


def avg_review_score(f):
    return _scalar(f["order_reviews"].select(pl.col("review_score").mean()))


def top3_states_by_customers(f):
    frame = (
        f["customers"]
        .group_by("customer_state")
        .len()
        .sort(["len", "customer_state"], descending=[True, False])
    )
    return frame["customer_state"].head(3).to_list()


def total_freight(f):
    return _scalar(f["order_items"].select(pl.col("freight_value").sum()))


def orders_2017(f):
    return float(f["orders"].filter(pl.col("order_purchase_timestamp").dt.year() == 2017).height)


def orders_per_status(f):
    return (
        f["orders"]
        .group_by("order_status")
        .len()
        .rename({"len": "orders"})
        .sort("order_status")
        .with_columns(pl.col("orders").cast(pl.Float64))
    )


# ---------------------------------------------------------------- level 2: joins
def items_delivered(f):
    return f["order_items"].join(delivered_orders(f).select("order_id"), on="order_id", how="inner")


def top_category_english(f):
    frame = (
        items_delivered(f)
        .join(f["products"].select("product_id", "product_category_name"), on="product_id")
        .join(f["product_category_translation"], on="product_category_name", how="inner")
        .group_by("product_category_name_english")
        .agg(pl.col("price").sum().alias("revenue"))
        .sort("revenue", descending=True)
    )
    return frame["product_category_name_english"][0]


def avg_delivery_days(f):
    frame = delivered_orders(f).filter(pl.col("order_delivered_customer_date").is_not_null())
    days = (
        pl.col("order_delivered_customer_date") - pl.col("order_purchase_timestamp")
    ).dt.total_seconds() / 86400
    return _scalar(frame.select(days.mean()))


def top5_seller_states(f):
    frame = (
        items_delivered(f)
        .join(f["sellers"].select("seller_id", "seller_state"), on="seller_id")
        .group_by("seller_state")
        .agg(pl.col("price").sum().alias("revenue"))
        .sort(["revenue", "seller_state"], descending=[True, False])
    )
    return frame["seller_state"].head(5).to_list()


def avg_score_late_orders(f):
    late = delivered_orders(f).filter(
        pl.col("order_delivered_customer_date") > pl.col("order_estimated_delivery_date")
    )
    frame = f["order_reviews"].join(late.select("order_id"), on="order_id", how="inner")
    return _scalar(frame.select(pl.col("review_score").mean()))


def boleto_share_delivered(f):
    delivered = delivered_orders(f).select("order_id")
    boleto = f["order_payments"].filter(pl.col("payment_type") == "boleto").select("order_id").unique()
    return float(delivered.join(boleto, on="order_id", how="inner").height / delivered.height)


def state_delivery_table(f):
    frame = (
        delivered_orders(f)
        .filter(pl.col("order_delivered_customer_date").is_not_null())
        .join(f["customers"].select("customer_id", "customer_state"), on="customer_id")
        .filter(pl.col("customer_state").is_in(["SP", "RJ", "MG"]))
    )
    days = (
        pl.col("order_delivered_customer_date") - pl.col("order_purchase_timestamp")
    ).dt.total_seconds() / 86400
    return (
        frame.group_by("customer_state")
        .agg(pl.len().cast(pl.Float64).alias("orders"), days.mean().alias("avg_delivery_days"))
        .sort("customer_state")
    )


def repeat_customer_share(f):
    frame = (
        f["orders"]
        .join(f["customers"].select("customer_id", "customer_unique_id"), on="customer_id")
        .group_by("customer_unique_id")
        .len()
    )
    return float((frame["len"] > 1).sum() / frame.height)


def top_seller_id(f):
    frame = (
        items_delivered(f)
        .group_by("seller_id")
        .agg(pl.col("price").sum().alias("revenue"))
        .sort("revenue", descending=True)
    )
    return frame["seller_id"][0]


# ---------------------------------------------------------------- level 4: cross-store extras
def avg_item_price_boleto_orders(f):
    boleto = f["order_payments"].filter(pl.col("payment_type") == "boleto").select("order_id").unique()
    items = items_delivered(f).join(boleto, on="order_id", how="inner")
    return _scalar(items.select(pl.col("price").mean()))


def delivered_orders_with_bed_bath_table(f):
    products = f["products"].filter(pl.col("product_category_name") == "cama_mesa_banho").select("product_id")
    orders = items_delivered(f).join(products, on="product_id", how="inner").select("order_id").unique()
    return float(orders.height)


# ---------------------------------------------------------------- level 5: standing problems
def _fact(name, value, *, rel=None, abs=None):
    return {"name": name, "value": value, "rel": rel, "abs": abs}


def orders_with_people(f):
    return f["orders"].join(f["customers"].select("customer_id", "customer_unique_id"), on="customer_id")


def problem_repeat_purchasing(f):
    per_person = (
        orders_with_people(f)
        .group_by("customer_unique_id")
        .agg(pl.len().alias("orders"), pl.col("order_purchase_timestamp").min().alias("first_order"))
    )
    repeat = per_person.filter(pl.col("orders") > 1)
    delivered = orders_with_people(f).filter(DELIVERED).select("order_id", "customer_unique_id")
    revenue = (
        f["order_items"]
        .join(delivered, on="order_id", how="inner")
        .join(
            repeat.select("customer_unique_id").with_columns(pl.lit(True).alias("is_repeat")),
            on="customer_unique_id",
            how="left",
        )
    )
    total = revenue["price"].sum()
    repeat_revenue = revenue.filter(pl.col("is_repeat"))["price"].sum()
    first_month = (
        per_person.with_columns(pl.col("first_order").dt.strftime("%Y-%m").alias("month"))
        .group_by("month")
        .len()
        .sort(["len", "month"], descending=[True, False])
    )
    return [
        _fact("repeat_customer_share", repeat.height / per_person.height, rel=0.005),
        _fact("avg_orders_per_repeat_customer", float(repeat["orders"].mean()), rel=0.005),
        _fact("repeat_revenue_share", repeat_revenue / total, rel=0.01),
        _fact("month_most_first_orders", first_month["month"][0]),
    ]


def problem_delivery_satisfaction(f):
    delivered = delivered_orders(f).filter(pl.col("order_delivered_customer_date").is_not_null())
    days = (
        pl.col("order_delivered_customer_date") - pl.col("order_purchase_timestamp")
    ).dt.total_seconds() / 86400
    late = pl.col("order_delivered_customer_date") > pl.col("order_estimated_delivery_date")
    delivered = delivered.with_columns(days.alias("days"), late.alias("late"))
    reviews = f["order_reviews"].join(delivered.select("order_id", "late"), on="order_id", how="inner")
    by_state = (
        delivered.join(f["customers"].select("customer_id", "customer_state"), on="customer_id")
        .group_by("customer_state")
        .agg(pl.len().alias("n"), pl.col("days").mean().alias("days"))
        .filter(pl.col("n") >= 500)
        .sort("days", descending=True)
    )
    return [
        _fact("avg_delivery_days", float(delivered["days"].mean()), rel=0.005),
        _fact("late_share", float(delivered["late"].mean()), rel=0.01),
        _fact(
            "avg_review_score_late", float(reviews.filter(pl.col("late"))["review_score"].mean()), rel=0.005
        ),
        _fact(
            "avg_review_score_on_time",
            float(reviews.filter(~pl.col("late"))["review_score"].mean()),
            rel=0.005,
        ),
        _fact("slowest_state_500_plus", by_state["customer_state"][0]),
    ]


def problem_category_seller_performance(f):
    items = items_delivered(f)
    cats = items.join(f["products"].select("product_id", "product_category_name"), on="product_id").join(
        f["product_category_translation"], on="product_category_name", how="inner"
    )
    by_cat = (
        cats.group_by("product_category_name_english")
        .agg(pl.col("price").sum().alias("revenue"))
        .sort("revenue", descending=True)
    )
    by_seller = (
        items.group_by("seller_id")
        .agg(pl.col("price").sum().alias("revenue"), pl.len().alias("n"))
        .sort("revenue", descending=True)
    )
    total = items["price"].sum()
    pairs = cats.select("order_id", "product_category_name_english").unique()
    scored = (
        f["order_reviews"]
        .select("order_id", "review_score")
        .join(pairs, on="order_id", how="inner")
        .group_by("product_category_name_english")
        .agg(pl.len().alias("n"), pl.col("review_score").mean().alias("score"))
        .filter(pl.col("n") >= 500)
        .sort(["score", "product_category_name_english"])
    )
    return [
        _fact("top_category_english", by_cat["product_category_name_english"][0]),
        _fact("top_category_revenue", float(by_cat["revenue"][0]), rel=0.002),
        _fact("top10_seller_revenue_share", float(by_seller.head(10)["revenue"].sum() / total), rel=0.01),
        _fact("sellers_with_100_plus_delivered_items", float((by_seller["n"] >= 100).sum()), abs=0),
        _fact("lowest_score_category_500_plus", scored["product_category_name_english"][0]),
    ]


# ---------------------------------------------------------------- level 3: messy
def delivered_without_date(f):
    return float(delivered_orders(f).filter(pl.col("order_delivered_customer_date").is_null()).height)


def categories_without_translation(f):
    cats = f["products"].select("product_category_name").drop_nulls().unique()
    return float(cats.join(f["product_category_translation"], on="product_category_name", how="anti").height)


def multi_payment_orders(f):
    return float((f["order_payments"].group_by("order_id").len()["len"] > 1).sum())


def duplicate_review_ids(f):
    reviews = f["order_reviews"]
    return float(reviews.height - reviews["review_id"].n_unique())


def payment_mismatch_share(f):
    delivered = delivered_orders(f).select("order_id")
    items = (
        f["order_items"]
        .group_by("order_id")
        .agg((pl.col("price").sum() + pl.col("freight_value").sum()).alias("goods"))
    )
    pays = f["order_payments"].group_by("order_id").agg(pl.col("payment_value").sum().alias("paid"))
    frame = delivered.join(items, on="order_id", how="inner").join(pays, on="order_id", how="inner")
    return float(((frame["paid"] - frame["goods"]).abs() > 1.0).sum() / frame.height)


def products_without_category(f):
    return float(f["products"]["product_category_name"].null_count())


SCENARIOS: list[Spec] = [
    Spec(
        "olist-l1-01",
        1,
        "How many orders have the status 'delivered'?",
        "number",
        delivered_count,
        EXACT,
        "orders",
        ["count", "filter"],
    ),
    Spec(
        "olist-l1-02",
        1,
        "How many distinct people are in the customers table? Use customer_unique_id, "
        "which identifies a person across orders.",
        "number",
        unique_customers,
        EXACT,
        "customers",
        ["count-distinct"],
    ),
    Spec(
        "olist-l1-03",
        1,
        "Which payment type appears most often in the order payments table?",
        "text",
        top_payment_type,
        EXACT,
        None,
        ["ranking", "text-answer"],
    ),
    Spec(
        "olist-l1-04",
        1,
        "What is the average review score across all rows of the order reviews table?",
        "number",
        avg_review_score,
        RATIO,
        "score",
        ["mean"],
    ),
    Spec(
        "olist-l1-05",
        1,
        "List the top 3 customer states by number of rows in the customers table, highest "
        "first (two-letter state codes). Break ties alphabetically.",
        "ranked_list",
        top3_states_by_customers,
        EXACT,
        None,
        ["ranking"],
    ),
    Spec(
        "olist-l1-06",
        1,
        "What is the total freight value summed over all order items? Answer in BRL.",
        "number",
        total_freight,
        MONEY,
        "BRL",
        ["sum"],
    ),
    Spec(
        "olist-l1-07",
        1,
        "How many orders were purchased in calendar year 2017, by order purchase timestamp?",
        "number",
        orders_2017,
        EXACT,
        "orders",
        ["count", "date-filter"],
    ),
    Spec(
        "olist-l1-08",
        1,
        "How many orders are there per order status? Return a table with columns "
        "`order_status` and `orders`, one row per status.",
        "table",
        orders_per_status,
        EXACT,
        "orders",
        ["table", "group-by"],
    ),
    Spec(
        "olist-l2-01",
        2,
        "Which product category, by its English name, had the highest total item revenue "
        "(sum of item price, excluding freight) across orders with status 'delivered'? Ignore categories "
        "without an English translation.",
        "text",
        top_category_english,
        EXACT,
        None,
        ["join-3", "ranking"],
    ),
    Spec(
        "olist-l2-02",
        2,
        "What was the average delivery time in days for orders with status 'delivered' that "
        "have a customer delivery date: the time from order purchase timestamp to delivered customer date, "
        "averaged as a fractional number of days?",
        "number",
        avg_delivery_days,
        RATIO,
        "days",
        ["dates", "mean", "nulls"],
    ),
    Spec(
        "olist-l2-03",
        2,
        "List the top 5 seller states by total item revenue (sum of item price) across "
        "orders with status 'delivered', highest first (two-letter codes). Break ties alphabetically.",
        "ranked_list",
        top5_seller_states,
        EXACT,
        None,
        ["join", "ranking"],
    ),
    Spec(
        "olist-l2-04",
        2,
        "What was the average review score of orders with status 'delivered' whose customer "
        "delivery date is later than the estimated delivery date? Average over review rows.",
        "number",
        avg_score_late_orders,
        RATIO,
        "score",
        ["join", "dates", "mean"],
    ),
    Spec(
        "olist-l2-05",
        2,
        "What share of orders with status 'delivered' have at least one payment record of "
        "type 'boleto'? Answer as a fraction between 0 and 1.",
        "number",
        boleto_share_delivered,
        RATIO,
        "share",
        ["join", "ratio", "exists"],
    ),
    Spec(
        "olist-l2-06",
        2,
        "For customer states SP, RJ and MG, how many orders with status 'delivered' and a "
        "customer delivery date are there, and what is their average delivery time in fractional days from "
        "purchase to customer delivery? Return a table with columns `customer_state`, `orders`, "
        "`avg_delivery_days`.",
        "table",
        state_delivery_table,
        RATIO,
        None,
        ["table", "join", "dates"],
    ),
    Spec(
        "olist-l2-07",
        2,
        "What share of people (customer_unique_id) placed more than one order, across all "
        "orders regardless of status? Answer as a fraction between 0 and 1.",
        "number",
        repeat_customer_share,
        RATIO,
        "share",
        ["join", "ratio", "identity"],
    ),
    Spec(
        "olist-l2-08",
        2,
        "Which seller_id had the highest total item revenue (sum of item price) across "
        "orders with status 'delivered'? Answer with the seller_id.",
        "text",
        top_seller_id,
        EXACT,
        None,
        ["join", "ranking", "text-answer"],
    ),
    Spec(
        "olist-l3-01",
        3,
        "How many orders have the status 'delivered' but no customer delivery date?",
        "number",
        delivered_without_date,
        EXACT,
        "orders",
        ["nulls", "discovery"],
    ),
    Spec(
        "olist-l3-02",
        3,
        "How many distinct non-null product category names in the products table have no "
        "English translation in the translation table?",
        "number",
        categories_without_translation,
        EXACT,
        "categories",
        ["anti-join", "discovery"],
    ),
    Spec(
        "olist-l3-03",
        3,
        "How many orders have more than one row in the order payments table?",
        "number",
        multi_payment_orders,
        EXACT,
        "orders",
        ["duplicates", "grain"],
    ),
    Spec(
        "olist-l3-04",
        3,
        "How many rows in the order reviews table share a review_id with another row, "
        "counting every copy beyond the first?",
        "number",
        duplicate_review_ids,
        EXACT,
        "rows",
        ["duplicates", "discovery"],
    ),
    Spec(
        "olist-l3-05",
        3,
        "Among orders with status 'delivered' that have both items and payments, what share "
        "have a total payment value that differs from the sum of item prices plus freight by more than "
        "1 BRL in absolute terms? Answer as a fraction between 0 and 1.",
        "number",
        payment_mismatch_share,
        RATIO,
        "share",
        ["reconciliation", "grain", "ratio"],
    ),
    Spec(
        "olist-l3-06",
        3,
        "How many products have no category name?",
        "number",
        products_without_category,
        EXACT,
        "products",
        ["nulls"],
    ),
    Spec(
        "olist-l3-07",
        3,
        "What was Olist's net profit in 2017?",
        "number",
        None,
        MONEY,
        "BRL",
        ["unanswerable", "missing-cost"],
        "No cost or margin data exists; the right answer is cannot_answer.",
    ),
    Spec(
        "olist-l3-08",
        3,
        "What was the average age of customers who received a delivered order?",
        "number",
        None,
        RATIO,
        "years",
        ["unanswerable", "missing-field"],
        "No customer age exists; the right answer is cannot_answer.",
    ),
]


# Level 4 reuses cross-cutting questions; the harness connects the dataset as two stores
# (orders/customers/payments/reviews in PostgreSQL, items/products/sellers/translation in SQLite),
# so each answer needs data from both. Reference values are the same as the single-store ones.
# Level 5 standing problems list their facets so the facts can be scored; the story is judged.
SCENARIOS += [
    Spec(
        "olist-l4-01",
        4,
        "Which product category, by its English name, had the highest total item revenue "
        "(sum of item price, excluding freight) across orders with status 'delivered'? Ignore categories "
        "without an English translation.",
        "text",
        top_category_english,
        EXACT,
        None,
        ["cross-store", "join", "ranking"],
    ),
    Spec(
        "olist-l4-02",
        4,
        "List the top 5 seller states by total item revenue (sum of item price) across "
        "orders with status 'delivered', highest first (two-letter codes). Break ties alphabetically.",
        "ranked_list",
        top5_seller_states,
        EXACT,
        None,
        ["cross-store", "join", "ranking"],
    ),
    Spec(
        "olist-l4-03",
        4,
        "Which seller_id had the highest total item revenue (sum of item price) across "
        "orders with status 'delivered'? Answer with the seller_id.",
        "text",
        top_seller_id,
        EXACT,
        None,
        ["cross-store", "join", "ranking"],
    ),
    Spec(
        "olist-l4-04",
        4,
        "Among orders with status 'delivered' that have both items and payments, what share "
        "have a total payment value that differs from the sum of item prices plus freight by more than "
        "1 BRL in absolute terms? Answer as a fraction between 0 and 1.",
        "number",
        payment_mismatch_share,
        RATIO,
        "share",
        ["cross-store", "reconciliation", "ratio"],
    ),
    Spec(
        "olist-l4-05",
        4,
        "What is the average item price (simple mean over order item rows) for orders with "
        "status 'delivered' that have at least one payment of type 'boleto'? Answer in BRL.",
        "number",
        avg_item_price_boleto_orders,
        RATIO,
        "BRL",
        ["cross-store", "join", "mean"],
    ),
    Spec(
        "olist-l4-06",
        4,
        "How many distinct orders with status 'delivered' contain at least one item whose "
        "product category name is 'cama_mesa_banho'?",
        "number",
        delivered_orders_with_bed_bath_table,
        EXACT,
        "orders",
        ["cross-store", "join", "count-distinct"],
    ),
    Spec(
        "olist-l5-01",
        5,
        "Standing problem: how healthy is repeat purchasing? Report one metric per row: "
        "(1) the share of people (customer_unique_id) with more than one order, across all orders regardless "
        "of status; (2) the average number of orders among those repeat customers; (3) the share of item "
        "revenue (sum of item price over orders with status 'delivered') that came from repeat customers' "
        "orders; (4) the calendar month (YYYY-MM) in which the most people placed their first order. Then "
        "say what the numbers mean together.",
        "report",
        problem_repeat_purchasing,
        RATIO,
        None,
        ["standing-problem", "identity", "cohort"],
    ),
    Spec(
        "olist-l5-02",
        5,
        "Standing problem: how do delivery performance and customer satisfaction relate? "
        "Over orders with status 'delivered' that have a customer delivery date, report one metric per row: "
        "(1) the average delivery time in fractional days from purchase to customer delivery; (2) the share "
        "of those orders delivered after the estimated delivery date; (3) the average review score of late "
        "orders and (4) of on-time orders, averaging over review rows; (5) the customer state (two-letter "
        "code) with the longest average delivery time among states with at least 500 such orders. Then say "
        "what the numbers mean together, without claiming causes the data cannot show.",
        "report",
        problem_delivery_satisfaction,
        RATIO,
        None,
        ["standing-problem", "dates", "join"],
    ),
    Spec(
        "olist-l5-03",
        5,
        "Standing problem: which categories and sellers drive performance? Over orders "
        "with status 'delivered', report one metric per row: (1) the product category (English name) with "
        "the highest item revenue (sum of item price) and (2) that revenue in BRL; (3) the share of item "
        "revenue earned by the top 10 sellers; (4) the number of sellers with at least 100 delivered items; "
        "(5) the category (English name) with the lowest average review score among categories with at "
        "least 500 reviewed delivered orders, counting each order once per category. Then say what the "
        "numbers mean together.",
        "report",
        problem_category_seller_performance,
        RATIO,
        None,
        ["standing-problem", "join", "ranking"],
    ),
]


# Level 6: the same standing question asked once per monthly snapshot; one planted step change
# (see bench/replay.py) plus whatever the data does naturally. Each scenario binds its snapshot store.
SCENARIOS += [
    Spec(
        f"olist-l6-{period}",
        6,
        replay_question(period),
        "report",
        partial(replay_facts, period=period),
        RATIO,
        None,
        ["ambient-replay", "planted-change", "dates"],
        store=f"sqlite:{snapshot_name(period)}",
    )
    for period in PERIODS
]


# Each standing problem has its own replayed cadence; these are simulated invocations.

for theme, periods, compute, source_id, cadence in (
    ("repeat", REPEAT_PERIODS, problem_repeat_purchasing, "olist-l5-01", "quarterly"),
    ("category", CATEGORY_PERIODS, problem_category_seller_performance, "olist-l5-03", "weekly"),
):
    question = next(s.question for s in SCENARIOS if s.id == source_id)
    for period in periods:
        SCENARIOS.append(
            Spec(
                f"olist-l6-{theme}-{period}",
                6,
                f"Simulated {cadence} review as of the end of {period}. " + question,
                "report",
                (lambda date, fn: lambda f: fn(replay_frames(f, date)))(period, compute),
                RATIO,
                None,
                ["ambient-replay", cadence, theme],
                store=f"sqlite:{snapshot_name(period)}",
            )
        )
