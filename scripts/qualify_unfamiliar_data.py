"""Verify and profile the frozen unfamiliar-domain sources; never invokes a model.

Raw files and the profile stay under ignored data/. This evaluator-owned script is
not mounted into the analyst. Optional downloads are bounded and checksum-verified.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

import duckdb
import httpx
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "benchmarks/unfamiliar/unfamiliar-v1/sources.json"


def digest(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def verify_sources(data_dir: Path, *, download: bool) -> dict:
    document = json.loads(MANIFEST.read_text())
    raw = data_dir / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    for item in document["assets"]:
        path = raw / item["file"]
        if not path.exists() and download:
            partial = path.with_suffix(path.suffix + ".partial")
            with httpx.stream("GET", item["url"], follow_redirects=True, timeout=45) as response:
                response.raise_for_status()
                size = 0
                with partial.open("xb") as handle:
                    for chunk in response.iter_bytes():
                        size += len(chunk)
                        if size > item["bytes"]:
                            raise ValueError(f"Source grew beyond its frozen size: {path.name}")
                        handle.write(chunk)
            if size != item["bytes"] or digest(partial) != item["sha256"]:
                raise ValueError(f"Source changed; preserve partial bytes for review: {path.name}")
            partial.rename(path)
        if path.stat().st_size != item["bytes"] or digest(path) != item["sha256"]:
            raise ValueError(f"Frozen source mismatch: {path.name}")
    # Extract only the expected member; do not trust arbitrary archive paths.
    target = raw / "household_power_consumption.txt"
    expected = document["extracted_energy"]
    if not target.exists():
        with zipfile.ZipFile(raw / "household_power.zip") as archive:
            info = archive.getinfo(target.name)
            if info.file_size != expected["bytes"]:
                raise ValueError("Unexpected uncompressed source size")
            with archive.open(info) as source, target.open("xb") as output:
                while chunk := source.read(1024 * 1024):
                    output.write(chunk)
    if target.stat().st_size != expected["bytes"] or digest(target) != expected["sha256"]:
        raise ValueError("Extracted source mismatch")
    return document


def domain_csv_files(data_dir: Path, document: dict, domain_id: str) -> list[Path]:
    """Use only verified manifest assets; unrelated matching filenames are not inputs."""
    domain = next(domain for domain in document["domains"] if domain["id"] == domain_id)
    verified = {asset["file"] for asset in document["assets"]}
    names = [name for name in domain["assets"] if name.endswith(".csv")]
    if not names or any(name not in verified or Path(name).name != name for name in names):
        raise ValueError("Domain references an unverified or invalid asset name")
    return [data_dir / "raw" / name for name in names]


def profile(data_dir: Path, document: dict) -> dict:
    raw = data_dir / "raw"
    connection = duckdb.connect(":memory:")
    connection.execute("SET memory_limit='512MB'")
    connection.execute("SET threads=2")

    def query(sql: str) -> dict:
        result = connection.execute(sql)
        columns = [column[0] for column in result.description]
        return dict(zip(columns, result.fetchone(), strict=True))

    def csv_view(table: str, paths: list[Path], *, delim: str = ",") -> None:
        files = ",".join("'" + str(path).replace("'", "''") + "'" for path in paths)
        connection.execute(
            f"CREATE VIEW {table} AS SELECT * FROM read_csv([{files}], "
            f"header=true, all_varchar=true, delim='{delim}')"
        )

    trip_path = str(raw / "green_tripdata_2023-01.parquet").replace("'", "''")
    connection.execute(f"CREATE VIEW trips AS SELECT * FROM read_parquet('{trip_path}')")
    csv_view("zones", [raw / "taxi_zone_lookup.csv"])
    csv_view("energy", [raw / "household_power_consumption.txt"], delim=";")
    csv_view("weather", domain_csv_files(data_dir, document, "weather"))
    profiles = {}
    for table in ("trips", "zones", "energy", "weather"):
        schema = connection.execute(f"DESCRIBE {table}").fetchall()
        profiles[table] = {
            "rows": query(f"SELECT count(*) AS n FROM {table}")["n"],
            "schema": [{"name": row[0], "type": row[1]} for row in schema],
            "nulls": query(
                "SELECT "
                + ",".join(f'count(*) FILTER (WHERE "{row[0]}" IS NULL) AS "{row[0]}"' for row in schema)
                + f" FROM {table}"
            ),
        }
    profiles["trips"]["checks"] = query("""
        SELECT min(lpep_pickup_datetime) AS min_pickup, max(lpep_pickup_datetime) AS max_pickup,
          count(*) FILTER (WHERE lpep_pickup_datetime < '2023-01-01'
            OR lpep_pickup_datetime >= '2023-02-01') AS pickups_outside_partition_month,
          count(*) FILTER (WHERE lpep_dropoff_datetime <= lpep_pickup_datetime) AS nonpositive_duration,
          count(*) FILTER (WHERE trip_distance < 0) AS negative_distance,
          count(*) FILTER (WHERE total_amount < 0) AS negative_total,
          count(*) - (SELECT count(*) FROM (SELECT DISTINCT * FROM trips)) AS exact_duplicate_surplus,
          count(*) FILTER (WHERE NOT EXISTS
            (SELECT 1 FROM zones z WHERE try_cast(z.LocationID AS INTEGER)=trips.PULocationID))
            AS unmatched_pickup_zone,
          count(*) FILTER (WHERE NOT EXISTS
            (SELECT 1 FROM zones z WHERE try_cast(z.LocationID AS INTEGER)=trips.DOLocationID))
            AS unmatched_dropoff_zone
        FROM trips
    """)
    profiles["zones"]["duplicate_keys"] = query("SELECT count(*)-count(DISTINCT LocationID) AS n FROM zones")[
        "n"
    ]
    profiles["energy"]["checks"] = query("""
        SELECT min(strptime(Date || ' ' || Time, '%d/%m/%Y %H:%M:%S')) AS first_timestamp,
          max(strptime(Date || ' ' || Time, '%d/%m/%Y %H:%M:%S')) AS last_timestamp,
          count(*) - count(DISTINCT (Date, Time)) AS duplicate_timestamps,
          count(*) FILTER (WHERE try_cast(Global_active_power AS DOUBLE) IS NULL) AS missing_active_power,
          count(*) FILTER (WHERE Global_active_power = '?') AS question_mark_active_power,
          count(*) FILTER (WHERE try_cast(Global_active_power AS DOUBLE) < 0) AS negative_active_power
        FROM energy
    """)
    profiles["weather"]["checks"] = query("""
        SELECT count(DISTINCT STATION) AS stations, min(DATE) AS first_date, max(DATE) AS last_date,
          count(*) - count(DISTINCT (STATION, DATE)) AS duplicate_station_dates,
          count(*) FILTER (WHERE try_cast(TEMP AS DOUBLE) = 9999.9) AS sentinel_temperature,
          count(*) FILTER (WHERE try_cast(PRCP AS DOUBLE) = 99.99) AS sentinel_precipitation,
          count(*) FILTER (WHERE PRCP_ATTRIBUTES IN ('H','I')) AS incomplete_precipitation_flags,
          count(*) FILTER (WHERE NAME NOT LIKE '% US') AS non_us_station_rows
        FROM weather
    """)
    metadata = pq.read_metadata(raw / "green_tripdata_2023-01.parquet")
    profiles["trips"]["parquet_uncompressed_column_bytes"] = sum(
        metadata.row_group(i).total_byte_size for i in range(metadata.num_row_groups)
    )
    connection.close()
    return profiles


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data/unfamiliar-v1")
    parser.add_argument("--download", action="store_true", help="Fetch only missing pinned sources")
    parser.add_argument("--output", type=Path, required=True, help="New evaluator-only profile JSON")
    args = parser.parse_args()
    document = verify_sources(args.data_dir.resolve(), download=args.download)
    result = {
        "source_manifest_sha256": digest(MANIFEST),
        "source_version": document["version"],
        "profiles": profile(args.data_dir.resolve(), document),
        "analyst_calls": 0,
        "judge_calls": 0,
        "reference_answers_generated": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as handle:
        json.dump(result, handle, default=str, indent=2)
        handle.write("\n")
    print(f"Verified seven source assets; evaluator-only profile saved to {args.output}")


if __name__ == "__main__":
    main()
