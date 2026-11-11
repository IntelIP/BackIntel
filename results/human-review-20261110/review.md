# BackIntel human explanation review

Rate each criterion: **0 = fails/contradicts; 1 = partially supported or uncertain; 2 = clearly satisfies**. Numerical reference matching is checked separately. Read the question, response and cited calculation; model grades are withheld.

Reply in chat using `review-01: 2, 2, 2, 1 — your comment`, with ratings in each table's order. You can mark a case `unsure` and explain why. Alternatively fill human-labels.json and add your name and review timestamp. Blank means unreviewed.

## review-01

Source: recorded_agent_response.

Standing problem: how do delivery performance and customer satisfaction relate? Over orders with status 'delivered' that have a customer delivery date, report one metric per row: (1) the average delivery time in fractional days from purchase to customer delivery; (2) the share of those orders delivered after the estimated delivery date; (3) the average review score of late orders and (4) of on-time orders, averaging over review rows; (5) the customer state (two-letter code) with the longest average delivery time among states with at least 500 such orders. Then say what the numbers mean together, without claiming causes the data cannot show. Use these metric identifiers in rows: avg_delivery_days, late_share, avg_review_score_late, avg_review_score_on_time, slowest_state_500_plus.

**Status:** answered

| metric | value | unit |
| --- | --- | --- |
| avg_delivery_days | 12.558217098051713 | days |
| late_share | 0.08112366538820359 | share of eligible orders |
| avg_review_score_late | 2.5664935064935066 | review-score points per review row |
| avg_review_score_on_time | 4.2937182046856845 | review-score points per review row |
| slowest_state_500_plus | PA | two-letter customer-state code |

**Method:** Eligible orders are those with order_status = 'delivered' and a non-null customer delivery timestamp. Delivery time is the exact timestamp difference between purchase and customer delivery in fractional days. Late means customer delivery timestamp is strictly after the estimated delivery timestamp; equality is on time. Review averages are over joined review rows, so orders with multiple review rows contribute each row and orders without reviews do not contribute to those averages. The slowest-state ranking uses customer state, requires at least 500 eligible orders, and ranks by average delivery time. Together, the results show that 8.11% of eligible orders were late, and review rows for late orders averaged lower scores than those for on-time orders; this is an association and does not establish causation.

**Caveats:**

- The review-score averages are based on available review rows, not one score per order; there are 7,700 late and 88,653 on-time review rows in this population.
- The result describes the orders in this dataset and shows association only, not that delivery timing caused the review-score difference.

<details>
<summary>Evidence 1: python</summary>

```python
import os, sqlite3
from datetime import datetime

path = os.environ['BACKINTEL_SQLITE_PATH']
con = sqlite3.connect(f'file:{path}?mode=ro', uri=True)

orders = con.execute("""
    SELECT o.order_id, o.customer_id, o.order_purchase_timestamp,
           o.order_delivered_customer_date, o.order_estimated_delivery_date,
           c.customer_state
    FROM orders AS o
    JOIN customers AS c ON c.customer_id = o.customer_id
    WHERE o.order_status = 'delivered'
      AND o.order_delivered_customer_date IS NOT NULL
""").fetchall()

def parse(ts):
    return datetime.fromisoformat(ts)

n = 0
late_count = 0
sum_days = 0.0
state_totals = {}
order_timing = {}
for order_id, customer_id, purchased, delivered, estimated, state in orders:
    days = (parse(delivered) - parse(purchased)).total_seconds() / 86400
    late = delivered > estimated
    n += 1
    sum_days += days
    late_count += int(late)
    order_timing[order_id] = late
    total, count = state_totals.get(state, (0.0, 0))
    state_totals[state] = (total + days, count + 1)

review_sums = {True: 0, False: 0}
review_counts = {True: 0, False: 0}
for order_id, score in con.execute('SELECT order_id, review_score FROM order_reviews'):
    if order_id in order_timing:
        late = order_timing[order_id]
        review_sums[late] += score
        review_counts[late] += 1

slow_state, slow_data = max(
    ((state, data) for state, data in state_totals.items() if data[1] >= 500),
    key=lambda item: (item[1][0] / item[1][1], item[0])
)
print({
    'eligible_orders': n,
    'avg_delivery_days': sum_days / n,
    'late_share': late_count / n,
    'avg_review_score_late': review_sums[True] / review_counts[True],
    'late_review_rows': review_counts[True],
    'avg_review_score_on_time': review_sums[False] / review_counts[False],
    'on_time_review_rows': review_counts[False],
    'slowest_state_500_plus': slow_state,
    'slowest_state_orders': slow_data[1],
    'slowest_state_avg_delivery_days': slow_data[0] / slow_data[1]
})
```

Computes all five report values; yields 96,470 eligible orders and PA with 946 eligible orders.

</details>

<details>
<summary>Evidence 2: python</summary>

```python
import os, sqlite3
path=os.environ['BACKINTEL_SQLITE_PATH']
con=sqlite3.connect(f'file:{path}?mode=ro', uri=True)
row=con.execute("""
SELECT COUNT(*) AS eligible_orders,
       SUM(CASE WHEN order_delivered_customer_date > order_estimated_delivery_date THEN 1 ELSE 0 END) AS late_orders,
       SUM(CASE WHEN order_delivered_customer_date <= order_estimated_delivery_date THEN 1 ELSE 0 END) AS on_time_orders
FROM orders
WHERE order_status = 'delivered' AND order_delivered_customer_date IS NOT NULL
""").fetchone()
print({'eligible_orders': row[0], 'late_orders': row[1], 'on_time_orders': row[2], 'late_plus_on_time': row[1] + row[2]})
```

Sanity check confirms late and on-time counts partition all 96,470 eligible orders.

</details>

| Criterion, in rating order | What to assess | Your rating |
| --- | --- | --- |
| conventions_stated | Does `method` state the concrete filters, exclusions and definitions used (which rows count, which period, how duplicates or nulls were handled), rather than a vague summary? | |
| method_matches_question | Does the method (and the cited evidence code) compute what the question asks: the right metric, grain, population and period, following any convention the question states? | |
| no_overreach | Does the answer avoid claims the data cannot support (causal explanations, estimates presented as measurements, invented fields)? If it declined, is the stated reason a real gap in the data rather than an avoidable difficulty? | |
| caveats_material | Are the caveats specific to this data and question (e.g. shares of missing ids, duplicated rows, scope limits) rather than boilerplate or absent when something clearly applies? | |

## review-02

Source: recorded_agent_response.

What was Olist's net profit in 2017?

**Status:** cannot_answer

**Method:** Net profit requires revenue and the associated costs/expenses for 2017. The available Olist tables include order and payment amounts, but no cost, expense, or profit fields, so net profit cannot be calculated from this dataset.

**Reason:** The data does not provide costs or expenses needed to calculate net profit. Revenue or payment totals alone would not establish profit; cost/expense data for the relevant period would be required.

**Caveats:**

- The Olist order/payment data can support measures of payments or item prices, but those are not net profit.

<details>
<summary>Evidence 1: sql</summary>

```sql
SELECT table_name, column_name, data_type FROM information_schema.columns WHERE table_schema = 'main' AND (lower(column_name) LIKE '%cost%' OR lower(column_name) LIKE '%profit%' OR lower(column_name) LIKE '%expense%' OR lower(column_name) LIKE '%fee%') ORDER BY table_name, column_name
```

No cost, profit, expense, or fee columns were found in the inspected tables.

</details>

| Criterion, in rating order | What to assess | Your rating |
| --- | --- | --- |
| gap_is_real | Is the stated reason a genuine absence of required data (a field or table that does not exist), rather than a difficulty the analyst could have worked around with the available tables? | |
| no_fabrication | Does the answer avoid inventing numbers, proxies presented as the asked-for metric, or fields that are not in the data? | |
| names_what_is_needed | Does the answer say concretely what data would be needed to answer the question? | |

## review-03

Source: recorded_agent_response.

Simulated quarterly review as of the end of 2017-09. Standing problem: how healthy is repeat purchasing? Report one metric per row: (1) the share of people (customer_unique_id) with more than one order, across all orders regardless of status; (2) the average number of orders among those repeat customers; (3) the share of item revenue (sum of item price over orders with status 'delivered') that came from repeat customers' orders; (4) the calendar month (YYYY-MM) in which the most people placed their first order. Then say what the numbers mean together. Use these metric identifiers in rows: repeat_customer_share, avg_orders_per_repeat_customer, repeat_revenue_share, month_most_first_orders.

**Status:** answered

| metric | value | unit |
| --- | --- | --- |
| repeat_customer_share | 0.027378328913457588 | share of people |
| avg_orders_per_repeat_customer | 2.1036834924965895 | orders per repeat customer |
| repeat_revenue_share | 0.050677401212069345 | share of delivered item revenue |
| month_most_first_orders | 2017-08 | calendar month (YYYY-MM) |

**Method:** Counted orders by customer_unique_id using all order statuses; repeat customers have more than one observed order. The repeat-order average is total orders from repeat customers divided by repeat customers. Repeat revenue is the sum of order_items.price on delivered orders associated with repeat customers, divided by delivered item-price revenue overall; freight is not included. First-order month is based on each person's earliest observed order_purchase_timestamp, with month ties resolved by earliest month. Together, the measures show that repeat purchasing was limited (about 2.74% of people), although repeat customers averaged just over two orders and contributed a larger 5.07% share of delivered item revenue; the largest first-order cohort was in 2017-08.

**Caveats:**

- The customer population is people represented by at least one row in orders; customers without an observed order are not included.
- The earliest order and repeat status are relative to orders present in this as-of dataset, not necessarily each person's full lifetime history.
- Item revenue uses item price only and excludes freight.

<details>
<summary>Evidence 1: python</summary>

```python
import os, sqlite3, collections
path=os.environ['BACKINTEL_SQLITE_PATH']
con=sqlite3.connect(f'file:{path}?mode=ro', uri=True)
# Fetch each relatively small table independently; map customer_id to persistent customer identity.
customer_map=dict(con.execute('SELECT customer_id, customer_unique_id FROM customers'))
orders=con.execute('SELECT order_id, customer_id, order_status, order_purchase_timestamp FROM orders').fetchall()
by_person=collections.defaultdict(list)
status_by_order={}
for oid,cid,status,ts in orders:
    uid=customer_map[cid]
    by_person[uid].append((oid,ts))
    status_by_order[oid]=status
repeat=[uid for uid,os_ in by_person.items() if len(os_)>1]
repeat_share=len(repeat)/len(by_person)
avg_repeat=sum(len(by_person[u]) for u in repeat)/len(repeat)
first_months=collections.Counter(min(ts for _,ts in os_)[:7] for os_ in by_person.values())
best_month=sorted(first_months, key=lambda m:(-first_months[m],m))[0]
repeat_set=set(repeat)
order_to_uid={oid:customer_map[cid] for oid,cid,status,ts in orders}
repeat_revenue=total_revenue=0.0
for oid,price in con.execute("SELECT i.order_id, i.price FROM order_items i JOIN orders o ON o.order_id=i.order_id WHERE o.order_status='delivered'"):
    total_revenue+=price
    if order_to_uid[oid] in repeat_set: repeat_revenue+=price
print({'repeat_customer_share':repeat_share,'avg_orders_per_repeat_customer':avg_repeat,'repeat_revenue_share':repeat_revenue/total_revenue,'month_most_first_orders':best_month,'customers':len(by_person),'repeat_customers':len(repeat),'month_people':first_months[best_month],'delivered_item_revenue':total_revenue})
```

Computes all four reported metrics from orders, customers, and delivered order-item prices.

</details>

<details>
<summary>Evidence 2: python</summary>

```python
import os, sqlite3, collections
p=os.environ['BACKINTEL_STORE_NOTE']; db=sqlite3.connect(f'file:{p}?mode=ro',uri=True)
uid_by_cid=dict(db.execute('SELECT customer_id, customer_unique_id FROM customers'))
counts=collections.Counter(uid_by_cid[cid] for (cid,) in db.execute('SELECT customer_id FROM orders'))
repeat_ids={u for u,n in counts.items() if n>1}
order_uid={oid:uid_by_cid[cid] for oid,cid in db.execute('SELECT order_id, customer_id FROM orders')}
rev=collections.defaultdict(float)
for oid,price in db.execute("SELECT i.order_id, i.price FROM order_items i JOIN orders o ON o.order_id=i.order_id WHERE o.order_status='delivered'"):
    rev[order_uid[oid]]+=price
repeat_rev=sum(v for u,v in rev.items() if u in repeat_ids)
all_rev=sum(rev.values())
print({'customer_count':len(counts),'repeat_customer_count':len(repeat_ids),'repeat_order_count':sum(counts[u] for u in repeat_ids),'repeat_delivered_item_revenue':repeat_rev,'all_delivered_item_revenue':all_rev,'repeat_share_from_revenue_parts':repeat_rev/all_rev})
```

Independent check of customer/repeat counts and delivered revenue share.

</details>

| Criterion, in rating order | What to assess | Your rating |
| --- | --- | --- |
| conventions_stated | Does `method` state the concrete filters, exclusions and definitions used (which rows count, which period, how duplicates or nulls were handled), rather than a vague summary? | |
| method_matches_question | Does the method (and the cited evidence code) compute what the question asks: the right metric, grain, population and period, following any convention the question states? | |
| no_overreach | Does the answer avoid claims the data cannot support (causal explanations, estimates presented as measurements, invented fields)? If it declined, is the stated reason a real gap in the data rather than an avoidable difficulty? | |
| caveats_material | Are the caveats specific to this data and question (e.g. shares of missing ids, duplicated rows, scope limits) rather than boilerplate or absent when something clearly applies? | |

## review-04

Source: recorded_agent_response.

Standing question for the 2018-03 run: did delivery performance change materially by customer state? Compare orders purchased in 2018-03 with orders purchased in 2018-02, using orders with status 'delivered' that have a customer delivery date, and the average delivery time in fractional days from purchase to customer delivery. Consider only states (two-letter codes) with at least 200 such orders in both months; a material change is a relative change of more than 25% in the average. Return a report with metric/value/unit rows: avg_days_STATE_current, avg_days_STATE_previous, and relative_change_STATE for every considered state, replacing STATE with its code; then a row with metric 'status' and value CHANGE_DETECTED or NO_CHANGE, and one row with metric 'changed_state_STATE' per state that changed materially (value = the state code). Note anything else in the data that affects the reading.

**Status:** answered

| metric | value | unit |
| --- | --- | --- |
| avg_days_MG_current | 12.241424543050107 | fractional days |
| avg_days_MG_previous | 15.007036209243903 | fractional days |
| relative_change_MG | -0.18428766530797464 | relative change (fraction) |
| avg_days_RJ_current | 12.6328319201511 | fractional days |
| avg_days_RJ_previous | 18.436029736231887 | fractional days |
| relative_change_RJ | -0.31477481318420214 | fractional days |
| relative_change_RJ | -0.31477481318420214 | relative change (fraction) |
| avg_days_SP_current | 8.069247442978844 | fractional days |
| avg_days_SP_previous | 10.956142073309513 | fractional days |
| relative_change_SP | -0.26349554533100605 | relative change (fraction) |
| status | CHANGE_DETECTED | status |
| changed_state_RJ | RJ | state code |
| changed_state_SP | SP | state code |

**Method:** Included orders purchased in February or March 2018 with status 'delivered' and a non-null customer delivery date, joined to customer state. Per state/month, average delivery time is the mean of julianday(customer delivery date) minus julianday(purchase timestamp), in fractional days. Relative change is (March average − February average) / February average; a change is material when its absolute value exceeds 0.25. MG, RJ, and SP alone meet the 200-order threshold in both months; RJ and SP show material decreases, while MG does not.

**Caveats:**

- The averages cover only deliveries already recorded by the dataset snapshot; March orders without a customer delivery date are excluded, so the March cohort may be incomplete or biased toward faster deliveries.
- Qualifying order counts (March / February) were MG 385 / 769, RJ 267 / 747, and SP 2007 / 2598.

<details>
<summary>Evidence 1: python</summary>

```python
import os, sqlite3
p=os.environ['BACKINTEL_SQLITE_PATH']
con=sqlite3.connect(f'file:{p}?mode=ro', uri=True)
q = """
SELECT c.customer_state,
       substr(o.order_purchase_timestamp,1,7) AS purchase_month,
       COUNT(*) AS n,
       AVG(julianday(o.order_delivered_customer_date)-julianday(o.order_purchase_timestamp)) AS avg_days
FROM orders o INDEXED BY ix_orders_customer_id
JOIN customers c INDEXED BY ix_customers_customer_id ON c.customer_id=o.customer_id
WHERE o.order_status='delivered'
  AND o.order_delivered_customer_date IS NOT NULL
  AND o.order_purchase_timestamp >= '2018-02-01' AND o.order_purchase_timestamp < '2018-04-01'
  AND length(trim(c.customer_state))=2
GROUP BY c.customer_state, substr(o.order_purchase_timestamp,1,7)
"""
agg = {(state, month): (n, avg) for state, month, n, avg in con.execute(q)}
considered = sorted(state for state, month in agg if month == '2018-03' and (state, '2018-02') in agg and agg[(state,'2018-03')][0] >= 200 and agg[(state,'2018-02')][0] >= 200)
rows=[]
changed=[]
for state in considered:
    ncur, cur = agg[(state,'2018-03')]
    nprev, prev = agg[(state,'2018-02')]
    rel=(cur-prev)/prev
    rows.extend([
        {'metric':f'avg_days_{state}_current','value':cur,'unit':'fractional days'},
        {'metric':f'avg_days_{state}_previous','value':prev,'unit':'fractional days'},
        {'metric':f'relative_change_{state}','value':rel,'unit':'relative change (fraction)'},
    ])
    if abs(rel) > 0.25:
        changed.append(state)
rows.append({'metric':'status','value':'CHANGE_DETECTED' if changed else 'NO_CHANGE','unit':'status'})
for state in changed:
    rows.append({'metric':f'changed_state_{state}','value':state,'unit':'state code'})
print(rows)
print('supporting_counts', {state:{'2018-03':agg[(state,'2018-03')][0], '2018-02':agg[(state,'2018-02')][0]} for state in considered})

```

Produces per-state monthly averages and relative changes, determines qualifying and materially changed states, and prints qualifying sample counts.

</details>

| Criterion, in rating order | What to assess | Your rating |
| --- | --- | --- |
| conventions_stated | Does `method` state the concrete filters, exclusions and definitions used (which rows count, which period, how duplicates or nulls were handled), rather than a vague summary? | |
| method_matches_question | Does the method (and the cited evidence code) compute what the question asks: the right metric, grain, population and period, following any convention the question states? | |
| no_overreach | Does the answer avoid claims the data cannot support (causal explanations, estimates presented as measurements, invented fields)? If it declined, is the stated reason a real gap in the data rather than an avoidable difficulty? | |
| caveats_material | Are the caveats specific to this data and question (e.g. shares of missing ids, duplicated rows, scope limits) rather than boilerplate or absent when something clearly applies? | |

## review-05

Source: recorded_agent_response.

What was Olist's net profit in 2017?

**Status:** cannot_answer

**Method:** I checked the available schema for fields whose names indicate costs, expenses, profit, revenue, or commissions. None are present, so net profit for 2017 cannot be computed from this store without additional financial data.

**Reason:** The connected Olist data has order-item prices and freight values, plus payment amounts, but no cost, operating-expense, commission, or profit fields. Revenue or payment totals alone cannot establish net profit; a cost/expense dataset or an explicit profit definition with its required inputs would be needed.

**Caveats:**

- The available order-item and payment measures are not a substitute for net profit, which requires the relevant cost and expense inputs.

<details>
<summary>Evidence 1: sql</summary>

```sql
SELECT table, name FROM system.columns WHERE database = currentDatabase() AND (lower(name) LIKE '%cost%' OR lower(name) LIKE '%expense%' OR lower(name) LIKE '%profit%' OR lower(name) LIKE '%revenue%' OR lower(name) LIKE '%commission%') ORDER BY table, name
```

No matching financial cost, expense, profit, revenue, or commission fields were found.

</details>

| Criterion, in rating order | What to assess | Your rating |
| --- | --- | --- |
| gap_is_real | Is the stated reason a genuine absence of required data (a field or table that does not exist), rather than a difficulty the analyst could have worked around with the available tables? | |
| no_fabrication | Does the answer avoid inventing numbers, proxies presented as the asked-for metric, or fields that are not in the data? | |
| names_what_is_needed | Does the answer say concretely what data would be needed to answer the question? | |

## review-06

Source: recorded_agent_response.

Standing problem: how healthy is repeat purchasing? Report one metric per row: (1) the share of people (customer_unique_id) with more than one order, across all orders regardless of status; (2) the average number of orders among those repeat customers; (3) the share of item revenue (sum of item price over orders with status 'delivered') that came from repeat customers' orders; (4) the calendar month (YYYY-MM) in which the most people placed their first order. Then say what the numbers mean together. Use these metric identifiers in rows: repeat_customer_share, avg_orders_per_repeat_customer, repeat_revenue_share, month_most_first_orders.

**Status:** answered

| metric | value | unit |
| --- | --- | --- |
| repeat_customer_share | 0.031187562437562436 | share of customer_unique_id values |
| avg_orders_per_repeat_customer | 2.116116116116116 | orders per repeat customer |
| repeat_revenue_share | 0.057510718806130824 | share of delivered item price revenue |
| month_most_first_orders | 2017-11 | calendar month (YYYY-MM) |

**Method:** Counted one order per row in orders, joining through customer_id and grouping by customer_unique_id; repeat customers have more than one order, with no order-status filter for the first two metrics or first-order timing. Average orders is the mean order count among repeat customers. Delivered item revenue is the sum of order_items.price for items on orders whose status is exactly 'delivered'; the revenue share compares items belonging to repeat customers with all such delivered item revenue. The results indicate that repeat purchasing is limited by customer count (about 3.12%), but those repeat customers average just over two orders and account for about 5.75% of delivered item revenue; November 2017 had the most people placing their first order.

**Caveats:**

- These metrics describe the orders and item rows present in this dataset; item revenue sums product price only, excluding freight_value and payments.

<details>
<summary>Evidence 1: python</summary>

```python
import os, sqlite3, pandas as pd
path = os.environ['BACKINTEL_SQLITE_PATH']
con = sqlite3.connect(f'file:{path}?mode=ro', uri=True)
orders = pd.read_sql_query("SELECT order_id, customer_id, order_status, order_purchase_timestamp FROM orders", con)
customers = pd.read_sql_query("SELECT customer_id, customer_unique_id FROM customers", con)
items = pd.read_sql_query("SELECT order_id, price FROM order_items", con)
orders = orders.merge(customers, on='customer_id', how='inner')
counts = orders.groupby('customer_unique_id').size()
repeat_ids = counts[counts > 1].index
repeat_customer_share = len(repeat_ids) / len(counts)
avg_orders_per_repeat_customer = counts[counts > 1].mean()
first = orders.groupby('customer_unique_id')['order_purchase_timestamp'].min()
month_counts = first.str.slice(0, 7).value_counts()
month_most_first_orders = sorted(month_counts[month_counts == month_counts.max()].index)[0]
delivered_orders = orders.loc[orders['order_status'] == 'delivered', ['order_id', 'customer_unique_id']]
delivered_items = items.merge(delivered_orders, on='order_id', how='inner')
repeat_revenue = delivered_items.loc[delivered_items['customer_unique_id'].isin(repeat_ids), 'price'].sum()
delivered_revenue = delivered_items['price'].sum()
repeat_revenue_share = repeat_revenue / delivered_revenue
print({'repeat_customer_share': repeat_customer_share, 'avg_orders_per_repeat_customer': avg_orders_per_repeat_customer, 'repeat_revenue_share': repeat_revenue_share, 'month_most_first_orders': month_most_first_orders, 'people_first_order_month': int(month_counts.max()), 'repeat_customer_count': len(repeat_ids), 'customer_count': len(counts), 'repeat_item_revenue': repeat_revenue, 'delivered_item_revenue': delivered_revenue})
```

Computes all four report metrics from customers, orders, and order_items.

</details>

| Criterion, in rating order | What to assess | Your rating |
| --- | --- | --- |
| conventions_stated | Does `method` state the concrete filters, exclusions and definitions used (which rows count, which period, how duplicates or nulls were handled), rather than a vague summary? | |
| method_matches_question | Does the method (and the cited evidence code) compute what the question asks: the right metric, grain, population and period, following any convention the question states? | |
| no_overreach | Does the answer avoid claims the data cannot support (causal explanations, estimates presented as measurements, invented fields)? If it declined, is the stated reason a real gap in the data rather than an avoidable difficulty? | |
| caveats_material | Are the caveats specific to this data and question (e.g. shares of missing ids, duplicated rows, scope limits) rather than boilerplate or absent when something clearly applies? | |
