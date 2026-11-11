"""Online Retail II scenarios. One table, `transactions`, 1,067,371 rows, Dec 2009 to Dec 2011.

Known mess, used deliberately: the two yearly sheets overlap for 1 to 9 Dec 2010 (22,523 rows
appear twice); cancellation invoices start with 'C' and carry negative quantities; 243,007 rows
have no customer id; stock codes without digits are charges, postage or adjustments; some
prices are zero or negative; descriptions vary for one stock code.
"""

from __future__ import annotations

import polars as pl

from backintel.bench.oracle import EXACT, MONEY, RATIO, Frames, Spec, _scalar

Y2011 = (pl.col("invoice_date") >= pl.datetime(2011, 1, 1)) & (
    pl.col("invoice_date") < pl.datetime(2011, 12, 10)
)
NOT_CANCELLED = ~pl.col("invoice").str.starts_with("C")
REVENUE = (pl.col("quantity") * pl.col("price")).alias("revenue")


def t(frames: Frames) -> pl.DataFrame:
    return frames["transactions"]


def sales_2011(frames: Frames) -> pl.DataFrame:
    return t(frames).filter(Y2011 & NOT_CANCELLED)


# ---------------------------------------------------------------- level 1: single table
def total_rows(f):
    return float(t(f).height)


def revenue_march_2011(f):
    frame = t(f).filter(
        NOT_CANCELLED
        & (pl.col("invoice_date") >= pl.datetime(2011, 3, 1))
        & (pl.col("invoice_date") < pl.datetime(2011, 4, 1))
    )
    return _scalar(frame.select(REVENUE.sum()))


def top_country_outside_uk(f):
    frame = (
        sales_2011(f)
        .filter(pl.col("country") != "United Kingdom")
        .group_by("country")
        .agg(REVENUE.sum())
        .sort("revenue", descending=True)
    )
    return frame["country"][0]


def customers_2011(f):
    return float(sales_2011(f).filter(pl.col("customer_id").is_not_null())["customer_id"].n_unique())


def top5_countries_by_invoices(f):
    frame = (
        sales_2011(f)
        .filter(pl.col("country") != "United Kingdom")
        .group_by("country")
        .agg(pl.col("invoice").n_unique().alias("n"))
        .sort(["n", "country"], descending=[True, False])
    )
    return frame["country"].head(5).to_list()


def avg_price_85123a(f):
    frame = sales_2011(f).filter((pl.col("stock_code") == "85123A") & (pl.col("price") > 0))
    return _scalar(frame.select(pl.col("price").mean()))


def qty_85123a_nov_2011(f):
    frame = t(f).filter(
        NOT_CANCELLED
        & (pl.col("stock_code") == "85123A")
        & (pl.col("invoice_date") >= pl.datetime(2011, 11, 1))
        & (pl.col("invoice_date") < pl.datetime(2011, 12, 1))
    )
    return _scalar(frame.select(pl.col("quantity").sum()))


def monthly_invoices_h1_2011(f):
    frame = (
        t(f)
        .filter(
            NOT_CANCELLED
            & (pl.col("invoice_date") >= pl.datetime(2011, 1, 1))
            & (pl.col("invoice_date") < pl.datetime(2011, 7, 1))
        )
        .with_columns(pl.col("invoice_date").dt.strftime("%Y-%m").alias("month"))
        .group_by("month")
        .agg(pl.col("invoice").n_unique().alias("invoices"))
        .sort("month")
    )
    return frame.with_columns(pl.col("invoices").cast(pl.Float64))


# ---------------------------------------------------------------- level 2: multi-step
def repeat_customer_share_2011(f):
    frame = (
        sales_2011(f)
        .filter(pl.col("customer_id").is_not_null())
        .group_by("customer_id")
        .agg(pl.col("invoice").n_unique().alias("n"))
    )
    return float((frame["n"] > 1).sum() / frame.height)


def best_month_2011(f):
    frame = (
        sales_2011(f)
        .with_columns(pl.col("invoice_date").dt.strftime("%Y-%m").alias("month"))
        .group_by("month")
        .agg(REVENUE.sum())
        .sort("revenue", descending=True)
    )
    return frame["month"][0]


def avg_basket_2011(f):
    frame = sales_2011(f)
    return float(frame.select(REVENUE.sum()).item() / frame["invoice"].n_unique())


# ---------------------------------------------------------------- level 3: messy data
CORE = [
    "invoice",
    "stock_code",
    "description",
    "quantity",
    "invoice_date",
    "price",
    "customer_id",
    "country",
]


def exact_duplicate_rows(f):
    frame = t(f).select(CORE)
    return float(frame.height - frame.unique().height)


def revenue_dec_2010_dedup(f):
    frame = (
        t(f)
        .select(CORE)
        .unique()
        .filter(
            NOT_CANCELLED
            & (pl.col("invoice_date") >= pl.datetime(2010, 12, 1))
            & (pl.col("invoice_date") < pl.datetime(2011, 1, 1))
        )
    )
    return _scalar(frame.select(REVENUE.sum()))


def net_revenue_2011(f):
    return _scalar(t(f).filter(Y2011).select(REVENUE.sum()))


def non_product_lines_2011(f):
    return float(t(f).filter(Y2011 & ~pl.col("stock_code").str.contains(r"\d")).height)


def no_customer_share_2011(f):
    frame = t(f).filter(Y2011)
    return float(frame["customer_id"].null_count() / frame.height)


def inconsistent_descriptions_2011(f):
    frame = (
        t(f)
        .filter(Y2011 & pl.col("description").is_not_null())
        .group_by("stock_code")
        .agg(pl.col("description").n_unique().alias("n"))
    )
    return float((frame["n"] > 1).sum())


def clean_product_revenue_2011(f):
    frame = t(f).filter(
        Y2011
        & NOT_CANCELLED
        & (pl.col("price") > 0)
        & (pl.col("quantity") > 0)
        & pl.col("stock_code").str.contains(r"\d")
    )
    return _scalar(frame.select(REVENUE.sum()))


SCENARIOS: list[Spec] = [
    Spec(
        "orii-l1-01",
        1,
        "How many rows (invoice lines) does the transactions table contain in total?",
        "number",
        total_rows,
        EXACT,
        "rows",
        ["count"],
        "Calibration item: a single COUNT(*).",
    ),
    Spec(
        "orii-l1-02",
        1,
        "What was total revenue in March 2011? Revenue is quantity times price summed "
        "over lines, excluding cancellation invoices (invoice numbers starting with 'C'). Answer in GBP.",
        "number",
        revenue_march_2011,
        MONEY,
        "GBP",
        ["sum", "date-filter", "stated-convention"],
    ),
    Spec(
        "orii-l1-03",
        1,
        "Which country outside the United Kingdom had the highest revenue (quantity times "
        "price, excluding invoices starting with 'C') between 1 January and 9 December 2011?",
        "text",
        top_country_outside_uk,
        EXACT,
        None,
        ["ranking", "text-answer"],
    ),
    Spec(
        "orii-l1-04",
        1,
        "How many distinct customers (rows with a customer id) made a non-cancelled "
        "purchase between 1 January and 9 December 2011? Exclude invoices starting with 'C'.",
        "number",
        customers_2011,
        EXACT,
        "customers",
        ["count-distinct", "nulls"],
    ),
    Spec(
        "orii-l1-05",
        1,
        "List the top 5 countries outside the United Kingdom by number of distinct "
        "non-cancelled invoices between 1 January and 9 December 2011, highest first. Exclude invoices "
        "starting with 'C'. Break ties alphabetically.",
        "ranked_list",
        top5_countries_by_invoices,
        EXACT,
        None,
        ["ranking", "count-distinct"],
    ),
    Spec(
        "orii-l1-06",
        1,
        "What is the simple average of the unit price column for stock code 85123A over "
        "non-cancelled lines with a positive price between 1 January and 9 December 2011? Answer in GBP.",
        "number",
        avg_price_85123a,
        RATIO,
        "GBP",
        ["mean", "filter"],
    ),
    Spec(
        "orii-l1-07",
        1,
        "How many units of stock code 85123A were sold in November 2011? Sum the quantity "
        "column over lines in November 2011, excluding invoices starting with 'C'.",
        "number",
        qty_85123a_nov_2011,
        EXACT,
        "units",
        ["sum", "date-filter"],
    ),
    Spec(
        "orii-l1-08",
        1,
        "For each month from January to June 2011, how many distinct non-cancelled "
        "invoices were issued? Exclude invoices starting with 'C'. Return a table with columns "
        "`month` (format YYYY-MM) and `invoices`.",
        "table",
        monthly_invoices_h1_2011,
        EXACT,
        "invoices",
        ["table", "group-by-month"],
    ),
    Spec(
        "orii-l2-01",
        2,
        "Among customers with a customer id who made at least one non-cancelled purchase "
        "between 1 January and 9 December 2011, what share had more than one distinct invoice in that "
        "period? Exclude invoices starting with 'C'. Answer as a fraction between 0 and 1.",
        "number",
        repeat_customer_share_2011,
        RATIO,
        "share",
        ["two-step", "ratio"],
    ),
    Spec(
        "orii-l2-02",
        2,
        "Which calendar month of 2011 had the highest revenue (quantity times price, "
        "excluding invoices starting with 'C')? Answer in the format YYYY-MM.",
        "text",
        best_month_2011,
        EXACT,
        None,
        ["ranking", "group-by-month"],
    ),
    Spec(
        "orii-l2-03",
        2,
        "What was the average basket value in 2011 (1 January to 9 December): total revenue "
        "(quantity times price) divided by the number of distinct invoices, both excluding invoices "
        "starting with 'C'? Answer in GBP.",
        "number",
        avg_basket_2011,
        RATIO,
        "GBP",
        ["ratio", "two-step"],
    ),
    Spec(
        "orii-l3-01",
        3,
        "How many rows in the transactions table are exact duplicates of another row, "
        "counting every copy beyond the first? Two rows are duplicates when all columns are equal.",
        "number",
        exact_duplicate_rows,
        EXACT,
        "rows",
        ["duplicates", "discovery"],
        "The two yearly sheets of the source overlap for 1-9 Dec 2010, plus genuine repeated lines.",
    ),
    Spec(
        "orii-l3-02",
        3,
        "What was total revenue in December 2010 (1 to 31 December), excluding invoices "
        "starting with 'C'? The export is known to contain some rows twice; count each distinct row "
        "once. Answer in GBP and note what you found about the duplication.",
        "number",
        revenue_dec_2010_dedup,
        MONEY,
        "GBP",
        ["duplicates", "sum"],
        "Requires de-duplicating the doubled 1-9 Dec 2010 rows before summing.",
    ),
    Spec(
        "orii-l3-03",
        3,
        "What was net revenue for 1 January to 9 December 2011, treating cancellation "
        "invoices (negative quantities) as reductions? Sum quantity times price over all rows in the "
        "period, with no other exclusions. Answer in GBP.",
        "number",
        net_revenue_2011,
        MONEY,
        "GBP",
        ["signs", "sum"],
    ),
    Spec(
        "orii-l3-04",
        3,
        "How many lines between 1 January and 9 December 2011 have a stock code that "
        "contains no digit at all (these are postage, manual entries, fees and adjustments rather "
        "than products)?",
        "number",
        non_product_lines_2011,
        EXACT,
        "rows",
        ["codes", "discovery"],
    ),
    Spec(
        "orii-l3-05",
        3,
        "What share of lines between 1 January and 9 December 2011 have no customer id? "
        "Answer as a fraction between 0 and 1.",
        "number",
        no_customer_share_2011,
        RATIO,
        "share",
        ["nulls", "ratio"],
    ),
    Spec(
        "orii-l3-06",
        3,
        "How many distinct stock codes have more than one distinct non-null description "
        "between 1 January and 9 December 2011?",
        "number",
        inconsistent_descriptions_2011,
        EXACT,
        "stock codes",
        ["text-quality", "count-distinct"],
    ),
    Spec(
        "orii-l3-07",
        3,
        "What was revenue from product sales between 1 January and 9 December 2011 after "
        "cleaning: exclude invoices starting with 'C', lines with a non-positive price or quantity, and "
        "stock codes containing no digit? Revenue is quantity times price. Answer in GBP.",
        "number",
        clean_product_revenue_2011,
        MONEY,
        "GBP",
        ["cleaning", "sum"],
    ),
    Spec(
        "orii-l3-08",
        3,
        "What was the gross profit margin on sales in 2011?",
        "number",
        None,
        RATIO,
        "share",
        ["unanswerable", "missing-cost"],
        "No cost data exists; the right answer is cannot_answer.",
    ),
    Spec(
        "orii-l3-09",
        3,
        "How many customers in 2011 were first-time buyers acquired through paid marketing?",
        "number",
        None,
        EXACT,
        "customers",
        ["unanswerable", "missing-channel"],
        "No acquisition-channel data exists; the right answer is cannot_answer.",
    ),
]
