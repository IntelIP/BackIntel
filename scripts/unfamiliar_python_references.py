"""Evaluator-only development references; no runtime or model calls.

This path loads raw files using Polars and calculates independently of SQL.
Shared dependencies are frozen source bytes, task contracts and output field names.
"""

from __future__ import annotations

from datetime import datetime
from math import fsum
from pathlib import Path

import polars as pl


def interval(frame: pl.DataFrame, field: str, start: str, stop: str) -> pl.DataFrame:
    return frame.filter(
        (pl.col(field) >= datetime.fromisoformat(start)) & (pl.col(field) < datetime.fromisoformat(stop))
    )


def calculate(raw: Path) -> dict:
    result = {}
    trips = pl.read_parquet(raw / "green_tripdata_2023-01.parquet")
    january = interval(trips, "lpep_pickup_datetime", "2023-01-01", "2023-02-01")
    result["transport-01"] = {
        "eligible_rows": january.height,
        "excluded_rows": trips.height - january.height,
    }
    payments = (
        january.with_columns(pl.col("payment_type").cast(pl.Int64).cast(pl.String).fill_null("unknown"))
        .group_by("payment_type")
        .agg(pl.col("total_amount").alias("amounts"))
        .sort("payment_type")
    )
    payments = pl.DataFrame(
        [
            {
                "payment_type": row["payment_type"],
                "total_usd": fsum(v for v in row["amounts"] if v is not None),
            }
            for row in payments.to_dicts()
        ]
    )
    if "unknown" not in payments["payment_type"]:
        payments = pl.concat(
            [
                payments,
                pl.DataFrame({"payment_type": ["unknown"], "total_usd": [0.0]}),
            ]
        ).sort("payment_type")
    result["transport-02"] = {
        "by_payment": payments.to_dicts(),
        "total_usd": january["total_amount"].sum(),
    }
    zones = pl.read_csv(raw / "taxi_zone_lookup.csv", infer_schema=False).with_columns(
        pl.col("LocationID").cast(pl.Int64)
    )
    if zones["LocationID"].n_unique() != zones.height:
        raise ValueError("Zone lookup violates many-to-one join contract")
    zones = zones.with_columns(pl.lit(True).alias("zone_matched"))
    joined = january.join(zones, left_on="PULocationID", right_on="LocationID", how="left")
    unmatched = joined["zone_matched"].null_count()
    joined = joined.with_columns(
        pl.when(pl.col("zone_matched").is_null())
        .then(pl.lit("unmatched"))
        .when(
            pl.col("Borough").fill_null("").str.strip_chars().str.to_lowercase().is_in(["", "unknown", "n/a"])
        )
        .then(pl.lit("unknown"))
        .otherwise(pl.col("Borough").str.strip_chars())
        .alias("borough")
    )
    result["transport-03"] = {
        "by_borough": joined.group_by("borough").len(name="trip_count").sort("borough").to_dicts(),
        "input_rows": january.height,
        "joined_rows": joined.height,
        "unmatched_rows": unmatched,
        "unknown_borough_rows": joined.filter(pl.col("borough").str.to_lowercase() == "unknown").height,
    }
    minutes = january.select(
        ((pl.col("lpep_dropoff_datetime") - pl.col("lpep_pickup_datetime")).dt.total_seconds() / 60).alias(
            "minutes"
        )
    ).filter((pl.col("minutes") > 0) & (pl.col("minutes") <= 180))["minutes"]
    result["transport-04"] = {
        "eligible_rows": len(minutes),
        "excluded_rows": january.height - len(minutes),
        "median_minutes": minutes.quantile(0.5, interpolation="linear"),
        "p95_minutes": minutes.quantile(0.95, interpolation="linear"),
    }
    first = interval(trips, "lpep_pickup_datetime", "2023-01-02", "2023-01-09").height
    second = interval(trips, "lpep_pickup_datetime", "2023-01-09", "2023-01-16").height
    result["transport-05"] = {
        "first_count": first,
        "second_count": second,
        "absolute_change": second - first,
        "relative_change": (second - first) / first,
    }
    transport_missing = ["complete_tips", "fuel_costs", "platform_or_lease_costs", "vehicle_costs"]
    if set(transport_missing) & set(trips.columns):
        raise ValueError("Review refusal contract: source now contains additional expense/tip fields")
    result["transport-06"] = {"status": "cannot_answer", "missing_inputs": transport_missing}

    energy = pl.read_csv(
        raw / "household_power_consumption.txt", separator=";", infer_schema=False, null_values=["?"]
    ).with_columns(
        (pl.col("Date") + " " + pl.col("Time"))
        .str.strptime(pl.Datetime, "%d/%m/%Y %H:%M:%S")
        .alias("timestamp"),
        *[
            pl.col(column).cast(pl.Float64, strict=False)
            for column in ("Global_active_power", "Sub_metering_1", "Sub_metering_2", "Sub_metering_3")
        ],
    )
    january_energy = interval(energy, "timestamp", "2007-01-01", "2007-02-01")
    if january_energy["timestamp"].n_unique() != january_energy.height:
        raise ValueError("Repeated minute labels require resolution before coverage calculation")
    expected = int((datetime(2007, 2, 1) - datetime(2007, 1, 1)).total_seconds() / 60)
    observed = january_energy.filter(pl.col("Global_active_power").is_not_null())
    result["energy-01"] = {
        "eligible_minute_slots": expected,
        "rows_present": january_energy.height,
        "observed_minutes": observed.height,
        "missing_minutes": expected - observed.height,
    }
    result["energy-02"] = {
        "observed_kwh": observed["Global_active_power"].sum() / 60,
        "observed_minutes": observed.height,
        "eligible_minute_slots": expected,
        "coverage_fraction": observed.height / expected,
    }
    complete = january_energy.drop_nulls(
        subset=["Global_active_power", "Sub_metering_1", "Sub_metering_2", "Sub_metering_3"]
    )
    global_wh = complete["Global_active_power"].sum() * 1000 / 60
    subs = [complete[f"Sub_metering_{i}"].sum() for i in range(1, 4)]
    result["energy-03"] = {
        "eligible_minutes": complete.height,
        "global_wh": global_wh,
        "submeter_1_wh": subs[0],
        "submeter_2_wh": subs[1],
        "submeter_3_wh": subs[2],
        "residual_wh": global_wh - sum(subs),
    }
    days = (
        observed.with_columns(pl.col("timestamp").dt.strftime("%Y-%m-%d").alias("date"))
        .group_by("date")
        .agg(
            (pl.col("Global_active_power").sum() / 60).alias("observed_kwh"),
            pl.len().alias("observed_minutes"),
        )
        .with_columns((pl.col("observed_minutes") / 1440).alias("coverage_fraction"))
        .filter(pl.col("coverage_fraction") >= 0.95)
        .sort(["observed_kwh", "date"], descending=[True, False])
        .head(5)
    )
    result["energy-04"] = {"days": days.to_dicts()}
    first_energy = interval(observed, "timestamp", "2007-01-01", "2007-01-08")
    second_energy = interval(observed, "timestamp", "2007-01-08", "2007-01-15")
    mean_first = first_energy["Global_active_power"].mean()
    mean_second = second_energy["Global_active_power"].mean()
    result["energy-05"] = {
        "first_observed_minutes": first_energy.height,
        "second_observed_minutes": second_energy.height,
        "first_mean_kw": mean_first,
        "second_mean_kw": mean_second,
        "absolute_change_kw": mean_second - mean_first,
    }
    energy_missing = ["fixed_fees", "taxes", "time_of_use_tariffs"]
    if set(energy_missing) & set(energy.columns):
        raise ValueError("Review refusal contract: source now includes pricing fields")
    result["energy-06"] = {"status": "cannot_answer", "missing_inputs": energy_missing}
    return result
