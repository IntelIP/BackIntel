"""Evaluator-only development references computed directly from raw sources with SQL.

This path does not import the Python reference implementation, derived tables or model
outputs. The returned values belong to the evaluator and must not enter analyst mounts.
"""

from __future__ import annotations

from pathlib import Path

import duckdb


def _one(con, sql: str) -> dict:
    result = con.execute(sql)
    return dict(zip((column[0] for column in result.description), result.fetchone(), strict=True))


def _many(con, sql: str) -> list[dict]:
    result = con.execute(sql)
    names = [column[0] for column in result.description]
    return [dict(zip(names, row, strict=True)) for row in result.fetchall()]


def calculate(raw: Path) -> dict:
    """Return the twelve fixed development-case references; never print answer values."""
    raw = Path(raw)
    answers = {}
    with duckdb.connect(config={"threads": 1, "memory_limit": "1GB"}) as con:
        con.execute(
            "CREATE TABLE trips AS SELECT * FROM read_parquet(?)",
            [str(raw / "green_tripdata_2023-01.parquet")],
        )
        con.execute(
            "CREATE TABLE zones_raw AS SELECT * FROM read_csv(?, header=true, all_varchar=true)",
            [str(raw / "taxi_zone_lookup.csv")],
        )
        trip_columns = {row[0].lower() for row in con.execute("DESCRIBE trips").fetchall()}
        missing_profit = ["complete_tips", "fuel_costs", "platform_or_lease_costs", "vehicle_costs"]
        assert set(missing_profit).isdisjoint(trip_columns)
        assert not any(
            word in name
            for name in trip_columns
            for word in ("fuel", "lease", "vehicle_expense", "platform_cost")
        ), "New expense columns require requalification of the refusal reference"
        con.execute(
            """CREATE TABLE january_trips AS
            SELECT * FROM trips WHERE lpep_pickup_datetime >= TIMESTAMP '2023-01-01'
            AND lpep_pickup_datetime < TIMESTAMP '2023-02-01'"""
        )
        answers["transport-01"] = _one(
            con,
            """WITH counts AS (SELECT (SELECT count(*) FROM january_trips) AS eligible_rows,
            (SELECT count(*) FROM trips) AS all_rows)
            SELECT eligible_rows, all_rows - eligible_rows AS excluded_rows FROM counts""",
        )
        assert (
            con.execute(
                """SELECT count(*) FROM january_trips WHERE payment_type IS NOT NULL
            AND (NOT isfinite(payment_type) OR payment_type != floor(payment_type))"""
            ).fetchone()[0]
            == 0
        ), "Payment codes must be integral or missing"
        con.execute(
            """CREATE TABLE payments AS
            SELECT coalesce(CAST(CAST(payment_type AS BIGINT) AS VARCHAR), 'unknown') AS payment_type,
            coalesce(fsum(total_amount), 0.0) AS total_usd
            FROM january_trips GROUP BY 1"""
        )
        answers["transport-02"] = {
            "by_payment": _many(
                con,
                """SELECT * FROM payments UNION ALL
                SELECT 'unknown', 0.0 WHERE NOT EXISTS
                (SELECT 1 FROM payments WHERE payment_type = 'unknown') ORDER BY payment_type""",
            ),
            **_one(con, "SELECT coalesce(fsum(total_amount), 0.0) AS total_usd FROM january_trips"),
        }
        assert con.execute(
            """SELECT count(*) = count(DISTINCT CAST(LocationID AS BIGINT))
            FROM zones_raw"""
        ).fetchone()[0], "Zone keys must be present and unique before the join"
        con.execute(
            """CREATE TABLE joined AS SELECT
            CASE WHEN z.LocationID IS NULL THEN 'unmatched'
                 WHEN z.Borough IS NULL OR lower(trim(z.Borough)) IN ('', 'unknown', 'n/a')
                 THEN 'unknown' ELSE trim(z.Borough) END AS borough
            FROM january_trips t LEFT JOIN zones_raw z
            ON t.PULocationID = CAST(z.LocationID AS BIGINT)"""
        )
        answers["transport-03"] = {
            "by_borough": _many(
                con, "SELECT borough, count(*) AS trip_count FROM joined GROUP BY 1 ORDER BY 1"
            ),
            **_one(
                con,
                """SELECT (SELECT count(*) FROM january_trips) AS input_rows,
                count(*) AS joined_rows, count(*) FILTER (WHERE borough = 'unmatched') AS unmatched_rows,
                count(*) FILTER (WHERE borough = 'unknown') AS unknown_borough_rows FROM joined""",
            ),
        }
        assert answers["transport-03"]["input_rows"] == answers["transport-03"]["joined_rows"]
        con.execute(
            """CREATE TABLE durations AS
            SELECT epoch(lpep_dropoff_datetime - lpep_pickup_datetime) / 60.0 AS minutes
            FROM january_trips"""
        )
        answers["transport-04"] = _one(
            con,
            """SELECT count(*) AS eligible_rows,
            (SELECT count(*) FROM january_trips) - count(*) AS excluded_rows,
            quantile_cont(minutes, 0.5) AS median_minutes,
            quantile_cont(minutes, 0.95) AS p95_minutes
            FROM durations WHERE minutes > 0 AND minutes <= 180""",
        )
        answers["transport-05"] = _one(
            con,
            """WITH periods AS (SELECT
            count(*) FILTER (WHERE lpep_pickup_datetime >= TIMESTAMP '2023-01-02'
            AND lpep_pickup_datetime < TIMESTAMP '2023-01-09') AS first_count,
            count(*) FILTER (WHERE lpep_pickup_datetime >= TIMESTAMP '2023-01-09'
            AND lpep_pickup_datetime < TIMESTAMP '2023-01-16') AS second_count FROM january_trips)
            SELECT *, second_count - first_count AS absolute_change,
            (second_count - first_count) / nullif(first_count, 0)::DOUBLE AS relative_change
            FROM periods""",
        )
        answers["transport-06"] = {"status": "cannot_answer", "missing_inputs": missing_profit}

        con.execute(
            """CREATE TABLE energy_raw AS SELECT * FROM read_csv(
            ?, delim=';', header=true, all_varchar=true)""",
            [str(raw / "household_power_consumption.txt")],
        )
        energy_columns = {row[0].lower() for row in con.execute("DESCRIBE energy_raw").fetchall()}
        missing_bill = ["fixed_fees", "taxes", "time_of_use_tariffs"]
        assert set(missing_bill).isdisjoint(energy_columns)
        assert not any(
            word in name for name in energy_columns for word in ("tariff", "tax", "fee", "price")
        ), "New billing columns require requalification of the refusal reference"
        con.execute(
            """CREATE TABLE energy AS SELECT
            strptime("Date" || ' ' || "Time", '%d/%m/%Y %H:%M:%S') AS recorded_minute,
            try_cast(Global_active_power AS DOUBLE) AS power_kw,
            try_cast(Sub_metering_1 AS DOUBLE) AS sub_1,
            try_cast(Sub_metering_2 AS DOUBLE) AS sub_2,
            try_cast(Sub_metering_3 AS DOUBLE) AS sub_3 FROM energy_raw"""
        )
        con.execute(
            """CREATE TABLE january_energy AS SELECT * FROM energy
            WHERE recorded_minute >= TIMESTAMP '2007-01-01'
            AND recorded_minute < TIMESTAMP '2007-02-01'"""
        )
        assert con.execute(
            """SELECT count(*) = count(DISTINCT recorded_minute)
            AND count(*) FILTER (WHERE date_trunc('minute', recorded_minute) != recorded_minute) = 0
            FROM january_energy"""
        ).fetchone()[0], "Minute coverage needs unique, minute-aligned source labels"
        assert (
            con.execute(
                """SELECT count(*) FROM january_energy
            WHERE (power_kw IS NOT NULL AND NOT isfinite(power_kw))
            OR (sub_1 IS NOT NULL AND NOT isfinite(sub_1))
            OR (sub_2 IS NOT NULL AND NOT isfinite(sub_2))
            OR (sub_3 IS NOT NULL AND NOT isfinite(sub_3))"""
            ).fetchone()[0]
            == 0
        ), "Nonfinite readings require explicit source qualification"
        con.execute(
            """CREATE TABLE coverage AS SELECT
            date_diff('minute', TIMESTAMP '2007-01-01', TIMESTAMP '2007-02-01') AS eligible_minute_slots,
            count(*) AS rows_present, count(power_kw) AS observed_minutes FROM january_energy"""
        )
        answers["energy-01"] = _one(
            con, "SELECT *, eligible_minute_slots - observed_minutes AS missing_minutes FROM coverage"
        )
        answers["energy-02"] = _one(
            con,
            """SELECT (SELECT fsum(power_kw) / 60.0 FROM january_energy) AS observed_kwh,
            observed_minutes, eligible_minute_slots,
            observed_minutes / eligible_minute_slots::DOUBLE AS coverage_fraction FROM coverage""",
        )
        answers["energy-03"] = _one(
            con,
            """SELECT count(*) AS eligible_minutes, fsum(power_kw) * 1000.0 / 60.0 AS global_wh,
            fsum(sub_1) AS submeter_1_wh, fsum(sub_2) AS submeter_2_wh, fsum(sub_3) AS submeter_3_wh,
            global_wh - submeter_1_wh - submeter_2_wh - submeter_3_wh AS residual_wh
            FROM january_energy WHERE power_kw IS NOT NULL AND sub_1 IS NOT NULL
            AND sub_2 IS NOT NULL AND sub_3 IS NOT NULL""",
        )
        answers["energy-04"] = {
            "days": _many(
                con,
                """SELECT CAST(CAST(recorded_minute AS DATE) AS VARCHAR) AS date,
                fsum(power_kw) / 60.0 AS observed_kwh, count(power_kw) AS observed_minutes,
                count(power_kw) / 1440.0 AS coverage_fraction
                FROM january_energy GROUP BY CAST(recorded_minute AS DATE)
                HAVING count(power_kw) * 100 >= 1440 * 95 ORDER BY observed_kwh DESC, date LIMIT 5""",
            )
        }
        answers["energy-05"] = _one(
            con,
            """WITH periods AS (SELECT
            count(power_kw) FILTER (WHERE recorded_minute >= TIMESTAMP '2007-01-01'
            AND recorded_minute < TIMESTAMP '2007-01-08') AS first_observed_minutes,
            count(power_kw) FILTER (WHERE recorded_minute >= TIMESTAMP '2007-01-08'
            AND recorded_minute < TIMESTAMP '2007-01-15') AS second_observed_minutes,
            fsum(power_kw) FILTER (WHERE recorded_minute >= TIMESTAMP '2007-01-01'
            AND recorded_minute < TIMESTAMP '2007-01-08') / first_observed_minutes AS first_mean_kw,
            fsum(power_kw) FILTER (WHERE recorded_minute >= TIMESTAMP '2007-01-08'
            AND recorded_minute < TIMESTAMP '2007-01-15') / second_observed_minutes AS second_mean_kw
            FROM january_energy)
            SELECT *, second_mean_kw - first_mean_kw AS absolute_change_kw FROM periods""",
        )
        answers["energy-06"] = {"status": "cannot_answer", "missing_inputs": missing_bill}
    return answers
