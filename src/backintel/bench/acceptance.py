"""Deterministic contrast cases for data sufficiency, evidence and temporal reporting.

Only the generated SQLite databases are exposed to the analyst. Scenario references,
independent check queries and planting declarations remain in the evaluation process.
The development and acceptance splits are different fixture worlds, not random row splits.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Literal

from backintel.contracts import Scenario, Tolerance
from backintel.settings import Settings, repo_root

VERSION = "acceptance-v1"
Split = Literal["development", "acceptance"]


@dataclass
class AcceptanceSuite:
    dataset: str
    split: str
    scenarios: list[Scenario]
    reference_hash: str
    data_hash: str
    manifest_path: Path


def _digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def _money(cents: int) -> float:
    return float(Decimal(cents) / Decimal(100))


def _fact(name: str, value) -> dict:
    return {"name": name, "value": value, "abs": 0 if isinstance(value, int) else 1e-6, "rel": None}


class _Builder:
    def __init__(self, settings: Settings, split: Split, output: Path, *, generation: int = 1):
        self.settings, self.split, self.output = settings, split, output
        self.version = VERSION if generation == 1 else f"{VERSION}-reserved-{generation}"
        self.dataset = f"backintel_{self.version.replace('-', '_')}_{split}"
        self.scenarios: list[Scenario] = []
        self.worlds: dict[str, dict] = {}
        self.checks: list[dict] = []
        self.truth: dict[str, dict] = {}

    def add(
        self,
        name: str,
        question: str,
        tables: dict[str, tuple[str, list[tuple]]],
        expected,
        *,
        answer_type: str = "number",
        unit: str | None = None,
        tags: tuple[str, ...] = (),
        sql: str | None = None,
        declaration: dict | None = None,
        level: int = 3,
    ) -> None:
        world_name = "bi_" + _digest([self.version, self.split, name])[:16]
        path = self.settings.stores_dir / "sqlite" / f"{world_name}.sqlite"
        path.parent.mkdir(parents=True, exist_ok=True)
        # Rebuild only owned, deterministic fixture paths. No existing benchmark store is changed.
        if path.exists():
            path.unlink()
        with sqlite3.connect(path) as con:
            for table, (schema, rows) in tables.items():
                con.execute(f'CREATE TABLE "{table}" ({schema})')
                if rows:
                    placeholders = ",".join("?" for _ in rows[0])
                    con.executemany(f'INSERT INTO "{table}" VALUES ({placeholders})', rows)
            if sql is not None:
                got = con.execute(sql).fetchall()
                value = got[0][0] if answer_type == "number" else {row[0]: row[1] for row in got}
                want = expected if answer_type == "number" else {f["name"]: f["value"] for f in expected}
                if answer_type == "number":
                    matches = abs(float(value) - float(want)) <= 1e-7
                else:
                    matches = value.keys() == want.keys() and all(
                        value[k] == v if isinstance(v, str) else abs(float(value[k]) - float(v)) <= 1e-7
                        for k, v in want.items()
                    )
                if not matches:
                    raise AssertionError(f"Independent SQL reference mismatch: {name}: {value!r} != {want!r}")
                self.checks.append({"case": name, "sql": sql, "matches": True, "observed": value})
        identifier = f"{self.version}-{self.split}-{name}"
        self.scenarios.append(
            Scenario(
                id=identifier,
                dataset=self.dataset,
                level=level,
                question=question,
                answer_type=answer_type,
                expected=expected,
                answerable=expected is not None,
                tolerance=Tolerance(abs=0.005 if unit == "GBP" else 1e-6),
                unit=unit,
                tags=["acceptance", self.split, *tags],
                store=f"sqlite:{world_name}",
                notes="Synthetic capability case; agent-authored reference, pending owner review.",
            )
        )
        self.worlds[identifier] = {
            "store": f"sqlite:{world_name}",
            "content_hash": _digest(tables),
            "file_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
        if declaration:
            self.truth[identifier] = declaration

    def finish(self) -> AcceptanceSuite:
        reference_hash = _digest([s.model_dump() for s in self.scenarios])
        data_hash = _digest(self.worlds)
        manifest_path = self.output / f"{self.split}.json"
        payload = {
            "version": self.version,
            "dataset": self.dataset,
            "split": self.split,
            "reference_hash": reference_hash,
            "data_hash": data_hash,
            "review_status": "agent-reviewed; human acceptance and calibration pending",
            "oracle": "Python integer/Decimal/date calculations, cross-checked by independent SQLite SQL",
            "isolation": (
                "Only each case's SQLite file is mounted; this manifest and its check SQL "
                "are not agent-visible."
            ),
            "worlds": self.worlds,
            "scenarios": [s.model_dump() for s in self.scenarios],
            "reference_checks": self.checks,
            "planted_changes": self.truth,
        }
        self.output.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(payload, indent=2, default=str) + "\n")
        return AcceptanceSuite(
            self.dataset, self.split, self.scenarios, reference_hash, data_hash, manifest_path
        )


def _financial_cases(b: _Builder, variant: int) -> None:
    sales = "sales_lines" if not variant else "revenue_entries"
    expenses = "expense_lines" if not variant else "cost_entries"
    year, month = (2024, 3) if not variant else (2025, 7)
    if variant == 2:
        sales, expenses, year, month = "receipts", "expenditures", 2026, 2
    period = f"{year}-{month:02d}"
    start, end = f"{period}-01", f"{year}-{month + 1:02d}-01"
    numbers = [12000, 8000, -1500, 5000] if not variant else [17003, 9401, -1107, 6309]
    if variant == 2:
        numbers = [14127, 8263, -2609, 10033]
    rows = [
        (f"E{i + 71}", f"{period}-{day:02d}", amount, "GBP")
        for i, (day, amount) in enumerate(zip((2, 8, 15, 23), numbers, strict=True))
    ]
    rows.append(("P52", f"{year}-{month - 1:02d}-20", 99999, "GBP"))
    sale_schema = "entry_id TEXT, booked_date TEXT, amount_minor INTEGER, currency TEXT"
    cost_schema = "entry_id TEXT, booked_date TEXT, amount_minor INTEGER, currency TEXT"
    coverage_schema = "ledger TEXT, period_start TEXT, period_end_exclusive TEXT, complete INTEGER"
    revenue = sum(numbers)
    costs = [10100, 3300, 700] if not variant else [11011, 5401, 1207]
    if variant == 2:
        costs = [8451, 2067, 999]
    cost_rows = [
        (f"C{i + 31}", f"{period}-{day:02d}", amount, "GBP")
        for i, (day, amount) in enumerate(zip((3, 10, 21), costs, strict=True))
    ]
    cost_rows.append(("C90", f"{year}-{month - 1:02d}-02", 88888, "GBP"))
    basic = {sales: (sale_schema, rows)}
    revenue_sql = (
        f"SELECT SUM(amount_minor)/100.0 FROM {sales} WHERE booked_date >= '{start}' AND "
        f"booked_date < '{end}' AND currency='GBP'"
    )
    b.add(
        "revenue",
        (
            f"What was net sales revenue in {period}, in GBP? Sum signed posted sales amounts, "
            f"including refunds as reductions. Amounts are stored in minor currency units (100 per "
            f"GBP)."
        ),
        basic,
        _money(revenue),
        unit="GBP",
        tags=("answerable-control", "refunds"),
        sql=revenue_sql,
    )
    full = {
        **basic,
        expenses: (cost_schema, cost_rows),
        "ledger_coverage": (coverage_schema, [(sales, start, end, 1), (expenses, start, end, 1)]),
    }
    profit_question = (
        f"What was net profit in {period}, in GBP? For this accounting extract, net profit is "
        f"signed posted sales revenue minus all posted expenses; the coverage table specifies "
        f"whether each ledger covers the full period. Use minor units consistently."
    )
    # A scalar subquery keeps the two ledger grains independent.
    profit_sql = (
        f"SELECT ({revenue_sql}) - (SELECT SUM(amount_minor)/100.0 FROM {expenses} WHERE "
        f"booked_date >= '{start}' AND booked_date < '{end}' AND currency='GBP')"
    )
    b.add(
        "profit-complete",
        profit_question,
        full,
        _money(revenue - sum(costs)),
        unit="GBP",
        tags=("answerable-control", "profit"),
        sql=profit_sql,
    )
    absent = {**basic, "ledger_coverage": (coverage_schema, [(sales, start, end, 1)])}
    b.add(
        "profit-missing",
        profit_question,
        absent,
        None,
        unit="GBP",
        tags=("missing-data", "profit"),
        declaration={"required_data": "full-period expenses", "absence": "no expense ledger"},
    )
    partial = {
        **basic,
        expenses: (cost_schema, cost_rows[:2]),
        "ledger_coverage": (coverage_schema, [(sales, start, end, 1), (expenses, start, f"{period}-15", 0)]),
    }
    b.add(
        "profit-partial",
        profit_question,
        partial,
        None,
        unit="GBP",
        tags=("missing-data", "coverage"),
        declaration={"required_data": "full-period expenses", "absence": "expense coverage ends mid-period"},
    )
    zero = {
        **basic,
        expenses: (cost_schema, [("C44", f"{period}-28", revenue, "GBP")]),
        "ledger_coverage": (coverage_schema, [(sales, start, end, 1), (expenses, start, end, 1)]),
    }
    b.add(
        "profit-zero",
        profit_question,
        zero,
        0.0,
        unit="GBP",
        tags=("answerable-control", "zero"),
        sql=profit_sql,
    )
    duplicate = {sales: (sale_schema, rows + [rows[0], rows[2]])}
    b.add(
        "revenue-duplicates",
        (
            f"What was net sales revenue in {period}, in GBP? This export can repeat identical "
            f"rows. Count each entry_id once, include signed refunds, and convert minor currency "
            f"units to GBP (100 per GBP)."
        ),
        duplicate,
        _money(revenue),
        unit="GBP",
        tags=("data-quality", "duplicates"),
        sql=(
            f"SELECT SUM(amount_minor)/100.0 FROM (SELECT DISTINCT * FROM {sales}) WHERE "
            f"booked_date >= '{start}' AND booked_date < '{end}' AND currency='GBP'"
        ),
    )


def _report_cases(b: _Builder, variant: int) -> None:
    order_table = "orders" if not variant else "fulfilments"
    review_table = "reviews" if not variant else "feedback"
    base = datetime(2024 + variant, 2 + variant, 1, 8)
    durations = [3, 6, 4, 10, 5] if not variant else [2, 7, 6, 12, 4]
    people = (1, 1, 2, 3, 3)
    if variant == 2:
        order_table, review_table = "dispatches", "ratings"
        durations, people = [7, 3, 9, 4, 6], (1, 2, 2, 2, 3)
    estimates = [4, 5, 5, 8, 5]
    rows = [
        (
            f"O{i + 21}",
            f"U{person}",
            "delivered",
            (base + timedelta(days=i)).isoformat(),
            (base + timedelta(days=i + d)).isoformat(),
            (base + timedelta(days=i + estimates[i])).isoformat(),
        )
        for i, (d, person) in enumerate(zip(durations, people, strict=True))
    ]
    rows.append(("O90", "U4", "delivered", base.isoformat(), None, (base + timedelta(days=9)).isoformat()))
    rows.append(("O91", "U5", "canceled", base.isoformat(), None, (base + timedelta(days=9)).isoformat()))
    reviews = [
        ("R1", "O21", 5),
        ("R2", "O22", 2),
        ("R3", "O22", 3),
        ("R4", "O23", 4),
        ("R5", "O24", 1),
        ("R6", "O25", 5),
        ("R7", "O90", 2),
    ]
    if variant == 2:
        reviews = [(r[0], r[1], score) for r, score in zip(reviews, (4, 1, 5, 3, 2, 4, 1), strict=True)]
    schema = (
        "order_id TEXT, customer_person_id TEXT, status TEXT, purchased_at TEXT, delivered_at "
        "TEXT, estimated_at TEXT"
    )
    tables = {
        order_table: (schema, rows),
        review_table: ("review_id TEXT, order_id TEXT, score INTEGER", reviews),
    }
    late = {r[0] for r in rows if r[4] is not None and r[4] > r[5]}
    selected = {r[0] for r in rows if r[2] == "delivered" and r[4] is not None}
    late_scores = [r[2] for r in reviews if r[1] in late]
    ontime_scores = [r[2] for r in reviews if r[1] in selected - late]
    expected = [
        _fact("eligible_orders", len(selected)),
        _fact("avg_delivery_days", sum(durations) / len(durations)),
        _fact("late_share", len(late) / len(selected)),
        _fact("avg_review_late", sum(late_scores) / len(late_scores)),
        _fact("avg_review_on_time", sum(ontime_scores) / len(ontime_scores)),
    ]
    question = (
        "Report delivery performance and satisfaction. Include only status delivered with a "
        "non-null delivered_at. Delivery duration is fractional days from purchased_at to "
        "delivered_at; late is strictly after estimated_at. Average review scores over joined "
        "review rows, not one review per order. Return exactly one metric/value/unit row for "
        "each: eligible_orders, avg_delivery_days, late_share, avg_review_late, "
        "avg_review_on_time. Explain the association without claiming causality."
    )
    selected_sql = f"SELECT * FROM {order_table} WHERE status='delivered' AND delivered_at IS NOT NULL"
    sql = (
        f"WITH eligible AS ({selected_sql}) SELECT 'eligible_orders',COUNT(*) FROM eligible "
        f"UNION ALL SELECT "
        f"'avg_delivery_days',AVG(julianday(delivered_at)-julianday(purchased_at)) FROM "
        f"eligible UNION ALL SELECT 'late_share',AVG(CASE WHEN delivered_at>estimated_at THEN "
        f"1.0 ELSE 0 END) FROM eligible UNION ALL SELECT 'avg_review_late',AVG(r.score) FROM "
        f"eligible o JOIN {review_table} r USING(order_id) WHERE o.delivered_at>o.estimated_at "
        f"UNION ALL SELECT 'avg_review_on_time',AVG(r.score) FROM eligible o JOIN "
        f"{review_table} r USING(order_id) WHERE o.delivered_at<=o.estimated_at"
    )
    b.add(
        "delivery-report",
        question,
        tables,
        expected,
        answer_type="report",
        tags=("evidence", "report", "review-grain"),
        sql=sql,
        level=5,
    )
    person_counts: dict[str, int] = {}
    for row in rows:
        person_counts[row[1]] = person_counts.get(row[1], 0) + 1
    repeat = [
        _fact("people", len(person_counts)),
        _fact("repeat_share", sum(n > 1 for n in person_counts.values()) / len(person_counts)),
        _fact("orders_per_person", len(rows) / len(person_counts)),
    ]
    repeat_sql = (
        f"WITH counts AS (SELECT customer_person_id,COUNT(DISTINCT order_id) n FROM "
        f"{order_table} GROUP BY customer_person_id) SELECT 'people',COUNT(*) FROM counts UNION "
        f"ALL SELECT 'repeat_share',AVG(CASE WHEN n>1 THEN 1.0 ELSE 0 END) FROM counts UNION "
        f"ALL SELECT 'orders_per_person',AVG(n) FROM counts"
    )
    b.add(
        "repeat-report",
        (
            "Report repeat purchasing across all orders regardless of status. A person is "
            "customer_person_id; count each order_id once. Return one row per metric: people "
            "(distinct people), repeat_share (fraction of people with more than one order), "
            "orders_per_person (mean orders per person). State the identity and population used."
        ),
        tables,
        repeat,
        answer_type="report",
        tags=("report", "identity-grain"),
        sql=repeat_sql,
        level=5,
    )
    b.add(
        "delivery-causality",
        (
            "How many review-score points would making every late delivery on time causally "
            "improve in this dataset? Give the causal effect, not the observed difference between "
            "groups."
        ),
        tables,
        None,
        tags=("missing-data", "causality"),
        declaration={"absence": "No randomized assignment or defensible causal identification is supplied."},
    )


def _replay_cases(b: _Builder, variant: int) -> None:
    # Different periods and baseline distributions keep the reserved split distinct.
    year, previous_month = (2024, 5) if not variant else (2025, 8)
    if variant == 2:
        year, previous_month = 2026, 8
    current_month = previous_month + 1
    previous, current = f"{year}-{previous_month:02d}", f"{year}-{current_month:02d}"
    cutoff = datetime(year, current_month + 1, 1)
    durations = [3, 4, 5, 4] if not variant else [5, 6, 7, 6]
    if variant == 2:
        durations = [7, 8, 9, 8]
    schema = "order_id TEXT, purchased_at TEXT, delivered_at TEXT, estimated_at TEXT"
    for name, shift, duplicate, delay in (
        ("stable", 0, False, "none"),
        ("shift", 3, False, "none"),
        ("late-observations", 0, False, "some"),
        ("late-observations-followup", 0, False, "some"),
        ("duplicate-export", 0, True, "none"),
        ("unobserved-period", 0, False, "all"),
    ):
        snapshot_cutoff = cutoff + timedelta(days=7) if name.endswith("followup") else cutoff
        raw = []
        for month in (previous_month, current_month):
            for i, duration in enumerate(durations):
                purchased = datetime(year, month, 2 + i)
                delivered = purchased + timedelta(days=duration + (shift if month == current_month else 0))
                if month == current_month and (delay == "all" or (delay == "some" and i >= 2)):
                    delivered = cutoff + timedelta(days=i + 2)
                raw.append(
                    (
                        f"A{month}{i + 41}",
                        purchased.isoformat(),
                        delivered.isoformat(),
                        (purchased + timedelta(days=8)).isoformat(),
                    )
                )
        visible = [
            (
                identity,
                purchase,
                None if datetime.fromisoformat(delivered) >= snapshot_cutoff else delivered,
                estimated,
            )
            for identity, purchase, delivered, estimated in raw
        ]
        if duplicate:
            visible.extend([visible[4], visible[5]])
        unique = {row[0]: row for row in visible}.values()

        def observed(period, unique=unique):
            return [
                (datetime.fromisoformat(r[2]) - datetime.fromisoformat(r[1])).total_seconds() / 86400
                for r in unique
                if r[1].startswith(period) and r[2] is not None
            ]

        before, now = observed(previous), observed(current)
        expected = None
        if now:
            a, c = sum(before) / len(before), sum(now) / len(now)
            change = (c - a) / a
            expected = [
                _fact("avg_days_previous", a),
                _fact("avg_days_current", c),
                _fact("relative_change", change),
                _fact("eligible_previous", len(before)),
                _fact("eligible_current", len(now)),
                _fact("pending_current", sum(r[1].startswith(current) and r[2] is None for r in unique)),
                _fact("status", "CHANGE_DETECTED" if abs(change) > 0.25 else "NO_CHANGE"),
            ]
        question = (
            f"This extract is a snapshot as of {snapshot_cutoff.date()} exclusive. Compare orders purchased "
            f"in {current} with {previous}. Count each order_id once; an order without an observed "
            f"delivered_at is pending and contributes no delivery duration. Compare mean fractional "
            f"days from purchase to delivery among observed orders. A material change is "
            f"abs(relative_change)>0.25; equality is no change. Return one row each for "
            f"avg_days_previous, avg_days_current, relative_change, eligible_previous, "
            f"eligible_current, pending_current, and status (CHANGE_DETECTED or NO_CHANGE). Explain "
            f"observation coverage. If a period has no observed deliveries, explain why the "
            f"comparison cannot be calculated."
        )
        sql = None
        if expected:
            sql = (
                f"WITH unique_orders AS (SELECT DISTINCT * FROM shipments), stats AS (SELECT AVG(CASE "
                f"WHEN purchased_at LIKE '{previous}%' THEN "
                f"julianday(delivered_at)-julianday(purchased_at) END) a, AVG(CASE WHEN purchased_at "
                f"LIKE '{current}%' THEN julianday(delivered_at)-julianday(purchased_at) END) c, "
                f"SUM(purchased_at LIKE '{previous}%' AND delivered_at IS NOT NULL) n0, "
                f"SUM(purchased_at LIKE '{current}%' AND delivered_at IS NOT NULL) n1, SUM(purchased_at "
                f"LIKE '{current}%' AND delivered_at IS NULL) pending FROM unique_orders) SELECT "
                f"'avg_days_previous',a FROM stats UNION ALL SELECT 'avg_days_current',c FROM stats "
                f"UNION ALL SELECT 'relative_change',(c-a)/a FROM stats UNION ALL SELECT "
                f"'eligible_previous',n0 FROM stats UNION ALL SELECT 'eligible_current',n1 FROM stats "
                f"UNION ALL SELECT 'pending_current',pending FROM stats UNION ALL SELECT 'status',CASE "
                f"WHEN ABS((c-a)/a)>0.25 THEN 'CHANGE_DETECTED' ELSE 'NO_CHANGE' END FROM stats"
            )
        b.add(
            f"replay-{name}",
            question,
            {"shipments": (schema, visible)},
            expected,
            answer_type="report",
            tags=("temporal", "data-quality" if duplicate or delay != "none" else "change-detection"),
            sql=sql,
            level=6,
            declaration={
                "cutoff_exclusive": snapshot_cutoff.isoformat(),
                "sequence": "delayed-arrivals" if delay == "some" else name,
                "current_period_added_days": shift,
                "duplicate_rows_added": 2 if duplicate else 0,
                "delayed_delivery_observations": delay,
                "raw_future_observations": raw,
            },
        )


def _price_replay_cases(b: _Builder, variant: int) -> None:
    previous, current = ("2024-05", "2024-06") if not variant else ("2025-08", "2025-09")
    prices = (1000, 2000) if not variant else (1750, 3500)
    if variant == 2:
        previous, current, prices = "2026-08", "2026-09", (1375, 3125)
    for name, changed in (("mix-only", False), ("shift", True)):
        multiplier = 17 if variant == 2 else 16
        current_prices = (prices[0] * multiplier // 10 if changed else prices[0], prices[1])
        rows = [
            ("L41", previous + "-10", "P11", 100, prices[0]),
            ("L42", previous + "-11", "P92", 10, prices[1]),
            ("L43", current + "-10", "P11", 10, current_prices[0]),
            ("L44", current + "-11", "P92", 100, current_prices[1]),
        ]
        changes = [float(Decimal(c) / Decimal(p) - 1) for p, c in zip(prices, current_prices, strict=True)]
        mean_change = sum(changes) / len(changes)
        expected = [
            _fact("relative_price_change_P11", changes[0]),
            _fact("relative_price_change_P92", changes[1]),
            _fact("mean_relative_price_change", mean_change),
            _fact("status", "CHANGE_DETECTED" if abs(mean_change) > 0.25 else "NO_CHANGE"),
        ]
        question = (
            f"Compare unit prices in {current} against {previous} for SKUs P11 and P92. "
            "Each SKU has one posted unit price in each month. Compute each SKU's relative price "
            "change (current/previous - 1) and their equal-weight mean; do not weight by units sold. "
            "Flag a material change only when the absolute mean exceeds 0.25. Return exactly one "
            "metric/value/unit row each for relative_price_change_P11, relative_price_change_P92, "
            "mean_relative_price_change, and status (CHANGE_DETECTED or NO_CHANGE). Explain whether "
            "a changed sales mix alone would justify a price-change alert."
        )
        sql = (
            "WITH comparisons AS (SELECT sku, "
            f"MAX(CASE WHEN booked_date LIKE '{current}%' THEN unit_price_minor END)*1.0/"
            f"MAX(CASE WHEN booked_date LIKE '{previous}%' THEN unit_price_minor END)-1 change "
            "FROM line_items GROUP BY sku) "
            "SELECT 'relative_price_change_'||sku,change FROM comparisons UNION ALL "
            "SELECT 'mean_relative_price_change',AVG(change) FROM comparisons UNION ALL "
            "SELECT 'status',CASE WHEN ABS(AVG(change))>0.25 THEN 'CHANGE_DETECTED' "
            "ELSE 'NO_CHANGE' END FROM comparisons"
        )
        b.add(
            f"replay-price-{name}",
            question,
            {
                "line_items": (
                    "line_id TEXT, booked_date TEXT, sku TEXT, quantity INTEGER, unit_price_minor INTEGER",
                    rows,
                )
            },
            expected,
            answer_type="report",
            tags=("temporal", "price-change", "mix-confounding"),
            sql=sql,
            level=6,
            declaration={"sku_P11_relative_price_change": changes[0], "quantity_mix_reversed": True},
        )


def build_acceptance(
    settings: Settings,
    split: Split = "development",
    *,
    output: Path | None = None,
    reserved_generation: int = 1,
) -> AcceptanceSuite:
    """Build owned immutable SQLite fixtures and hidden reference manifest without any model calls."""
    if split not in ("development", "acceptance"):
        raise ValueError("split must be development or acceptance")
    if reserved_generation not in (1, 2) or (split != "acceptance" and reserved_generation != 1):
        raise ValueError("Reserved generation must be 1 or 2 and applies only to acceptance")
    version = VERSION if reserved_generation == 1 else f"{VERSION}-reserved-{reserved_generation}"
    builder = _Builder(
        settings,
        split,
        output or repo_root() / "benchmarks" / "acceptance" / version,
        generation=reserved_generation,
    )
    variant = reserved_generation if split == "acceptance" else 0
    _financial_cases(builder, variant)
    _report_cases(builder, variant)
    _replay_cases(builder, variant)
    _price_replay_cases(builder, variant)
    return builder.finish()


def verify_acceptance_data(suite: AcceptanceSuite, settings: Settings) -> bool:
    """Check fixture files against the evaluator-owned manifest before/after a trial."""
    manifest = json.loads(suite.manifest_path.read_text())
    if _digest(manifest["worlds"]) != suite.data_hash:
        return False
    for world in manifest["worlds"].values():
        _, dataset = world["store"].split(":", 1)
        path = settings.stores_dir / "sqlite" / f"{dataset}.sqlite"
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != world["file_sha256"]:
            return False
    return True
