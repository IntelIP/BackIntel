"""Four controlled analysis tasks; fixtures/solutions/references stay evaluator-side.

Only ``AnalysisCase.brief`` and its SQLite source enter the runtime. These cases cover
three source fixtures, not four independent datasets or unseen-domain competence.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import re
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from backintel.analysis import AnalysisBrief
from backintel.stores.sqlite import SQLiteStore
from scripts.run_analysis_demo import ANALYSIS_QUERIES, brief, create_source, independent_reference

CASE_IDS = ("sales-refunds", "missing-cost", "irregular-energy", "service-availability")


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _sha(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def _read_source(path: Path) -> dict[str, list]:
    with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as connection:
        names = [
            r[0]
            for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        ]
        return {name: connection.execute(f'SELECT * FROM "{name}"').fetchall() for name in names}


def _source_content_sha(path: Path) -> str:
    rows = _read_source(path)
    return hashlib.sha256(_canonical({k: sorted(v, key=_canonical) for k, v in rows.items()})).hexdigest()


@dataclass(frozen=True)
class AnalysisCase:
    case_id: str
    brief: AnalysisBrief
    source: Path
    reference: Path
    source_sha256: str
    source_content_sha256: str
    reference_sha256: str
    evaluator_sha256: str
    expected_status: str
    requirements: dict

    def open_store(self) -> SQLiteStore:
        return SQLiteStore(self.source, dataset=self.case_id)


def _energy_source(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        connection.executescript("""
            CREATE TABLE meters(meter_id TEXT PRIMARY KEY, site TEXT);
            CREATE TABLE readings(meter_id TEXT, observed_at TEXT, power REAL, unit TEXT, quality TEXT);
            CREATE TABLE windows(window_start_utc TEXT PRIMARY KEY, window_end_utc TEXT);
        """)
        connection.executemany(
            "INSERT INTO meters VALUES (?,?)", [("alpha", "East"), ("beta", "West"), ("gamma", "Annex")]
        )
        connection.executemany(
            "INSERT INTO windows VALUES (?,?)",
            [
                ("2026-03-15T00:00:00Z", "2026-03-15T01:00:00Z"),
                ("2026-03-15T01:00:00Z", "2026-03-15T02:00:00Z"),
                ("2026-03-15T02:00:00Z", "2026-03-15T03:00:00Z"),
            ],
        )
        connection.executemany(
            "INSERT INTO readings VALUES (?,?,?,?,?)",
            [
                ("alpha", "2026-03-14T23:55:00Z", 4000, "W", "good"),
                ("alpha", "2026-03-15T00:00:00Z", 1000, "W", "good"),
                ("alpha", "2026-03-15T00:07:00Z", 2, "kW", "good"),
                ("alpha", "2026-03-15T00:25:00Z", None, "kW", "missing"),
                ("alpha", "2026-03-15T00:40:00Z", 0, "W", "good"),
                ("alpha", "2026-03-15T01:00:00Z", 1.5, "kW", "good"),
                ("alpha", "2026-03-15T02:00:00Z", 500, "W", "good"),
                ("alpha", "2026-03-15T03:00:00Z", 999, "kW", "good"),
                ("beta", "2026-03-15T01:05:00+01:00", 0.5, "kW", "good"),
                ("beta", "2026-03-15T00:20:00Z", 750, "W", "good"),
                ("beta", "2026-03-15T00:50:00Z", 100, "kW", "bad"),
                ("beta", "2026-03-15T01:10:00Z", 1000, "W", "good"),
                ("beta", "2026-03-15T01:45:00Z", 2, "kW", "good"),
                ("beta", "2026-03-15T02:15:00Z", None, "W", "missing"),
            ],
        )


def _availability_source(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        connection.executescript("""
            CREATE TABLE services(service_id TEXT PRIMARY KEY, customer_weight INTEGER);
            CREATE TABLE reporting_window(window_start_utc TEXT, window_end_utc TEXT);
            CREATE TABLE incidents(incident_id TEXT, service_id TEXT, started_at TEXT, ended_at TEXT);
            CREATE TABLE maintenance(maintenance_id TEXT, service_id TEXT, started_at TEXT, ended_at TEXT);
        """)
        connection.executemany(
            "INSERT INTO services VALUES (?,?)", [("api", 5), ("batch", 2), ("chat", 1), ("search", 3)]
        )
        connection.execute(
            "INSERT INTO reporting_window VALUES (?,?)", ("2026-10-01T00:00:00Z", "2026-10-01T01:00:00Z")
        )
        connection.executemany(
            "INSERT INTO incidents VALUES (?,?,?,?)",
            [
                ("i1", "api", "2026-09-30T23:55:00Z", "2026-10-01T00:10:00Z"),
                ("i2", "api", "2026-10-01T00:05:00Z", "2026-10-01T00:20:00Z"),
                ("i3", "api", "2026-10-01T00:30:00Z", "2026-10-01T00:40:00Z"),
                ("i4", "api", "2026-10-01T00:35:00Z", "2026-10-01T00:45:00Z"),
                ("i5", "api", "2026-10-01T00:50:00Z", "2026-10-01T01:10:00Z"),
                ("i6", "batch", "2026-10-01T00:10:00Z", "2026-10-01T00:25:00Z"),
                ("i7", "batch", "2026-10-01T00:25:00Z", "2026-10-01T00:35:00Z"),
            ],
        )
        connection.executemany(
            "INSERT INTO maintenance VALUES (?,?,?,?)",
            [
                ("m1", "api", "2026-10-01T00:12:00Z", "2026-10-01T00:18:00Z"),
                ("m2", "api", "2026-10-01T00:16:00Z", "2026-10-01T00:22:00Z"),
                ("m3", "batch", "2026-10-01T00:20:00Z", "2026-10-01T00:30:00Z"),
                ("m4", "chat", "2026-10-01T00:00:00Z", "2026-10-01T01:00:00Z"),
            ],
        )


def _seconds(value: str) -> int:
    return int(datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC).timestamp())


def _energy_oracle(path: Path) -> dict:
    """Decimal interval integration over raw rows; independent of SQL windows/joins."""
    source = _read_source(path)
    rows = []
    total_energy, total_covered, total_eligible = Decimal(0), 0, 0
    for meter_id, _ in sorted(source["meters"]):
        observations = sorted(
            (r for r in source["readings"] if r[0] == meter_id), key=lambda r: _seconds(r[1])
        )
        for begin, end in sorted(source["windows"]):
            lower, upper = _seconds(begin), _seconds(end)
            energy, covered = Decimal(0), 0
            for index, (_, instant, power, unit, quality) in enumerate(observations):
                if quality != "good" or power is None:
                    continue
                start = _seconds(instant)
                next_start = _seconds(observations[index + 1][1]) if index + 1 < len(observations) else upper
                stop = min(next_start, start + 900)
                duration = max(0, min(stop, upper) - max(start, lower))
                watts = Decimal(str(power)) * (1000 if unit == "kW" else 1)
                energy += watts * duration / Decimal(3600000)
                covered += duration
            total_energy += energy
            total_covered += covered
            total_eligible += upper - lower
            rows.append(
                [
                    meter_id,
                    begin,
                    float(energy) if covered else None,
                    covered / 60,
                    covered * 100 / (upper - lower),
                ]
            )
    return {
        "energy_by_window": {
            "columns": ["Meter", "WindowStart", "Energy", "CoveredMinutes", "CoveragePercent"],
            "rows": rows,
        },
        "energy_total": {
            "columns": ["Energy", "ObservedMeterMinutes", "EligibleMeterMinutes", "CoveragePercent"],
            "rows": [
                [
                    float(total_energy),
                    total_covered / 60,
                    total_eligible / 60,
                    total_covered * 100 / total_eligible,
                ]
            ],
        },
    }


def _availability_oracle(path: Path) -> dict:
    """Independent exact per-second membership; fixture endpoints have whole-second precision."""
    source = _read_source(path)
    lower, upper = map(_seconds, source["reporting_window"][0])
    service_rows = []
    weighted_eligible = weighted_down = 0
    for service, weight in sorted(source["services"]):
        outages = [(_seconds(s), _seconds(e)) for _, sid, s, e in source["incidents"] if sid == service]
        maintenance = [(_seconds(s), _seconds(e)) for _, sid, s, e in source["maintenance"] if sid == service]
        eligible = down = 0
        for second in range(lower, upper):
            if any(start <= second < stop for start, stop in maintenance):
                continue
            eligible += 1
            down += any(start <= second < stop for start, stop in outages)
        weighted_eligible += eligible * weight
        weighted_down += down * weight
        service_rows.append(
            [
                service,
                eligible / 60,
                down / 60,
                (eligible - down) * 100 / eligible if eligible else None,
                weight,
            ]
        )
    return {
        "service_availability": {
            "columns": ["Service", "EligibleMinutes", "DowntimeMinutes", "Availability", "Weight"],
            "rows": service_rows,
        },
        "fleet_availability": {
            "columns": ["WeightedEligibleMinutes", "WeightedDowntimeMinutes", "Availability"],
            "rows": [
                [
                    weighted_eligible / 60,
                    weighted_down / 60,
                    (weighted_eligible - weighted_down) * 100 / weighted_eligible,
                ]
            ],
        },
    }


_ENERGY_SQL = """
WITH observations AS (
  SELECT meter_id, CAST(strftime('%s',observed_at) AS INTEGER) AS instant,
         CASE WHEN quality='good' AND power IS NOT NULL
              THEN power * CASE unit WHEN 'kW' THEN 1000 ELSE 1 END END AS watts
  FROM readings
), segments AS (
  SELECT meter_id, instant, watts, LEAD(instant) OVER (PARTITION BY meter_id ORDER BY instant) AS next_instant
  FROM observations
), bounds AS (
  SELECT meter_id, window_start_utc,
         CAST(strftime('%s',window_start_utc) AS INTEGER) AS lower,
         CAST(strftime('%s',window_end_utc) AS INTEGER) AS upper
  FROM meters CROSS JOIN windows
), pieces AS (
  SELECT b.*, s.watts,
         MAX(0, MIN(COALESCE(s.next_instant,s.instant+900),s.instant+900,b.upper)
                -MAX(s.instant,b.lower)) AS seconds
  FROM bounds b LEFT JOIN segments s ON s.meter_id=b.meter_id
      AND s.instant < b.upper AND s.instant+900 > b.lower
), hourly AS (
  SELECT meter_id AS Meter, window_start_utc AS WindowStart,
         CASE WHEN SUM(CASE WHEN watts IS NOT NULL THEN seconds ELSE 0 END)>0
              THEN SUM(CASE WHEN watts IS NOT NULL THEN watts*seconds/3600000.0 ELSE 0 END) END AS Energy,
         SUM(CASE WHEN watts IS NOT NULL THEN seconds ELSE 0 END)/60.0 AS CoveredMinutes,
         (upper-lower)/60.0 AS EligibleMinutes
  FROM pieces GROUP BY meter_id,window_start_utc
)
""".strip()

_AVAILABILITY_SQL = """
WITH bounds AS (
  SELECT CAST(strftime('%s',window_start_utc) AS INTEGER) AS lower,
         CAST(strftime('%s',window_end_utc) AS INTEGER) AS upper FROM reporting_window
), outages AS (
  SELECT service_id, CAST(strftime('%s',started_at) AS INTEGER) AS start,
         CAST(strftime('%s',ended_at) AS INTEGER) AS stop FROM incidents
), maintenance_intervals AS (
  SELECT service_id, CAST(strftime('%s',started_at) AS INTEGER) AS start,
         CAST(strftime('%s',ended_at) AS INTEGER) AS stop FROM maintenance
), endpoints AS (
  SELECT service_id,lower AS point FROM services CROSS JOIN bounds
  UNION SELECT service_id,upper FROM services CROSS JOIN bounds
  UNION SELECT service_id,MAX(lower,MIN(upper,start)) FROM outages CROSS JOIN bounds
  UNION SELECT service_id,MAX(lower,MIN(upper,stop)) FROM outages CROSS JOIN bounds
  UNION SELECT service_id,MAX(lower,MIN(upper,start)) FROM maintenance_intervals CROSS JOIN bounds
  UNION SELECT service_id,MAX(lower,MIN(upper,stop)) FROM maintenance_intervals CROSS JOIN bounds
), segments AS (
  SELECT service_id,point,LEAD(point) OVER (PARTITION BY service_id ORDER BY point) AS next_point
  FROM endpoints
), eligible AS (
  SELECT s.*, next_point-point AS duration,
         EXISTS(SELECT 1 FROM outages o WHERE o.service_id=s.service_id
                AND o.start<=s.point AND o.stop>s.point) AS is_down
  FROM segments s WHERE next_point IS NOT NULL AND NOT EXISTS(
    SELECT 1 FROM maintenance_intervals m WHERE m.service_id=s.service_id
             AND m.start<=s.point AND m.stop>s.point
  )
), totals AS (
  SELECT services.service_id AS Service,customer_weight AS Weight,
         COALESCE(SUM(e.duration),0)/60.0 AS EligibleMinutes,
         COALESCE(SUM(e.duration*e.is_down),0)/60.0 AS DowntimeMinutes
  FROM services LEFT JOIN eligible e ON e.service_id=services.service_id GROUP BY services.service_id
)
""".strip()


def reference_queries(case_id: str) -> dict[str, str]:
    """Host-only reference solution. Never include these queries in a live brief or mount."""
    if case_id == "sales-refunds":
        return dict(ANALYSIS_QUERIES)
    if case_id == "missing-cost":
        return {}
    if case_id == "irregular-energy":
        return {
            "energy_by_window": _ENERGY_SQL
            + (
                "\nSELECT "
                "Meter,WindowStart,Energy,CoveredMinutes,100.0*CoveredMinutes/EligibleMinutes AS "
                "CoveragePercent FROM hourly ORDER BY Meter,WindowStart"
            ),
            "energy_total": _ENERGY_SQL
            + (
                "\nSELECT SUM(Energy) AS Energy,SUM(CoveredMinutes) AS "
                "ObservedMeterMinutes,SUM(EligibleMinutes) AS "
                "EligibleMeterMinutes,100.0*SUM(CoveredMinutes)/SUM(EligibleMinutes) AS "
                "CoveragePercent FROM hourly"
            ),
        }
    if case_id == "service-availability":
        return {
            "service_availability": _AVAILABILITY_SQL
            + (
                "\nSELECT Service,EligibleMinutes,DowntimeMinutes,CASE WHEN EligibleMinutes>0 THEN"
                " 100.0*(EligibleMinutes-DowntimeMinutes)/EligibleMinutes END AS "
                "Availability,Weight FROM totals ORDER BY Service"
            ),
            "fleet_availability": _AVAILABILITY_SQL
            + (
                "\nSELECT SUM(Weight*EligibleMinutes) AS "
                "WeightedEligibleMinutes,SUM(Weight*DowntimeMinutes) AS WeightedDowntimeMinutes,"
                "100.0*(SUM(Weight*EligibleMinutes)-"
                "SUM(Weight*DowntimeMinutes))/SUM(Weight*EligibleMinutes) AS Availability FROM "
                "totals"
            ),
        }
    raise ValueError(f"Unknown analysis case: {case_id}")


def _requirements(case_id: str) -> dict:
    if case_id == "missing-cost":
        return {
            "tables": {},
            "metrics": [],
            "charts": [],
            "refusal": "Explain the absent cost inputs; do not substitute revenue for profit.",
        }
    if case_id == "sales-refunds":
        return {
            "tables": {
                "categories": {"columns": ["Category", "Revenue"], "units": {"Revenue": "USD"}},
                "daily": {"columns": ["Date", "Revenue"], "units": {"Revenue": "USD"}},
                "total": {"columns": ["Revenue"], "units": {"Revenue": "USD"}},
            },
            "metrics": [
                {
                    "id": "net-revenue",
                    "label": "Net revenue",
                    "table": "total",
                    "row": 0,
                    "column": "Revenue",
                    "definition": (
                        "Delivered-order revenue after exact-row deduplication and refunded units; USD."
                    ),
                }
            ],
            "charts": [
                {
                    "id": "category-revenue",
                    "title": "Delivered revenue by category",
                    "kind": "bar",
                    "table": "categories",
                    "x": "Category",
                    "y": "Revenue",
                },
                {
                    "id": "daily-revenue",
                    "title": "Delivered revenue by day",
                    "kind": "line",
                    "table": "daily",
                    "x": "Date",
                    "y": "Revenue",
                },
            ],
        }
    if case_id == "irregular-energy":
        return {
            "tables": {
                "energy_by_window": {
                    "columns": ["Meter", "WindowStart", "Energy", "CoveredMinutes", "CoveragePercent"],
                    "units": {"Energy": "kWh", "CoveredMinutes": "minutes", "CoveragePercent": "%"},
                },
                "energy_total": {
                    "columns": ["Energy", "ObservedMeterMinutes", "EligibleMeterMinutes", "CoveragePercent"],
                    "units": {
                        "Energy": "kWh",
                        "ObservedMeterMinutes": "meter-minutes",
                        "EligibleMeterMinutes": "meter-minutes",
                        "CoveragePercent": "%",
                    },
                },
            },
            "metrics": [
                {
                    "id": "observed-energy",
                    "label": "Energy during covered intervals",
                    "table": "energy_total",
                    "row": 0,
                    "column": "Energy",
                    "definition": (
                        "Integrated power only over valid, freshness-bounded intervals; not an "
                        "estimate for missing time."
                    ),
                }
            ],
            "charts": [
                {
                    "id": "coverage-grid",
                    "title": "Observation coverage by meter and hour",
                    "kind": "heatmap",
                    "table": "energy_by_window",
                    "x": "WindowStart",
                    "y": "Meter",
                    "z": "CoveragePercent",
                }
            ],
        }
    return {
        "tables": {
            "service_availability": {
                "columns": ["Service", "EligibleMinutes", "DowntimeMinutes", "Availability", "Weight"],
                "units": {
                    "EligibleMinutes": "minutes",
                    "DowntimeMinutes": "minutes",
                    "Availability": "%",
                    "Weight": "customer-weight",
                },
            },
            "fleet_availability": {
                "columns": ["WeightedEligibleMinutes", "WeightedDowntimeMinutes", "Availability"],
                "units": {
                    "WeightedEligibleMinutes": "weighted-minutes",
                    "WeightedDowntimeMinutes": "weighted-minutes",
                    "Availability": "%",
                },
            },
        },
        "metrics": [
            {
                "id": "weighted-availability",
                "label": "Weighted fleet availability",
                "table": "fleet_availability",
                "row": 0,
                "column": "Availability",
                "definition": (
                    "One minus weighted eligible downtime divided by weighted eligible service "
                    "time, expressed as a percentage."
                ),
            }
        ],
        "charts": [
            {
                "id": "service-downtime",
                "title": "Outage time outside planned maintenance",
                "kind": "bar",
                "table": "service_availability",
                "x": "Service",
                "y": "DowntimeMinutes",
            }
        ],
    }


def _case_brief(case_id: str, requirements: dict) -> AnalysisBrief:
    if case_id in {"sales-refunds", "missing-cost"}:
        result = brief(profit=case_id == "missing-cost")
    elif case_id == "irregular-energy":
        result = AnalysisBrief(
            objective=(
                "Report observed energy and time coverage for every assigned meter in every "
                "reporting window, including meters/windows with no usable observations. Produce "
                "a coverage heatmap, total observed-energy metric and supporting sheets."
            ),
            business_context=(
                "Synthetic facilities operations. Readings are instantaneous power samples, not "
                "cumulative energy. The meter inventory and windows define the eligible "
                "population."
            ),
            audience="Facilities operations manager",
            metric_definitions={
                "energy": (
                    "Normalize all timestamps to UTC and W/kW to watts. Hold a good, non-null "
                    "sample constant from its timestamp until the next observation for that meter"
                    " (including a bad/null observation), but for at most 15 minutes. Clip "
                    "intervals to each half-open reporting window. Integrate "
                    "watts*seconds/3600000 to kWh. Do not interpolate or fill missing coverage. A"
                    " valid zero sample counts as covered time; a window with no valid interval "
                    "has Energy=null, not zero."
                ),
                "coverage": (
                    "CoveredMinutes counts usable interval time. "
                    "CoveragePercent=100*covered/window duration. Include every meter/window "
                    "pair. Totals sum observed energy and covered meter-minutes; denominator is "
                    "every assigned meter times the full reporting duration. Never average per-"
                    "window percentages if durations differ."
                ),
            },
            time_window=(
                "2026-03-15T00:00:00Z inclusive to 2026-03-15T03:00:00Z exclusive; use the hourly"
                " windows table."
            ),
            known_limitations=[
                "Controlled synthetic source, not real building operations.",
                (
                    "Missing/bad samples and freshness gaps prevent full-window consumption "
                    "estimates. No tariff, cost or causal explanation is supported."
                ),
            ],
            required_outputs=["report", "coverage heatmap", "CSV", "XLSX"],
        )
    else:
        result = AnalysisBrief(
            objective=(
                "Report service and customer-weighted fleet availability outside planned "
                "maintenance. Reconcile eligible time and downtime, include every service, and "
                "produce a service-downtime chart and supporting sheets."
            ),
            business_context=(
                "Synthetic service-operations incident review. Incident and maintenance records "
                "are complete for the assigned window; an eligible service with no incident was "
                "available. Customer weights are fixed exposure weights, not counts of affected "
                "people."
            ),
            audience="Service operations lead",
            metric_definitions={
                "eligible_time": (
                    "Use half-open UTC intervals and clip everything to the reporting window. For"
                    " each service, union overlapping or adjacent maintenance intervals and "
                    "remove them from the reporting duration. Do not subtract overlaps twice."
                ),
                "downtime": (
                    "Union incidents per service. Count only their intersection with eligible "
                    "time, excluding maintenance even when an incident overlaps it. Overlapping "
                    "incidents count once."
                ),
                "availability": (
                    "Per service: 100*(eligible-downtime)/eligible; null if eligible=0. Fleet: "
                    "100*(1-SUM(weight*downtime)/SUM(weight*eligible)). Do not take an unweighted"
                    " average of service percentages. Fully maintained services have no eligible "
                    "exposure and must not become zero-percent availability."
                ),
            },
            time_window="2026-10-01T00:00:00Z inclusive to 2026-10-01T01:00:00Z exclusive.",
            known_limitations=[
                (
                    "Controlled synthetic, whole-second incident intervals. Completeness is a "
                    "declared fixture assumption, not a production monitoring guarantee."
                ),
                "Availability is exposure weighted; it does not estimate revenue loss or incident causes.",
            ],
            required_outputs=["report", "service downtime chart", "CSV", "XLSX"],
        )
    if requirements["tables"]:
        result.objective += " Required output contract (table/column order may vary): " + json.dumps(
            requirements
        )
    return result


def build_cases(root: Path) -> list[AnalysisCase]:
    """Create three source fixtures and four tasks in a new host-owned directory."""
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=False, mode=0o700)
    sources = root / "sources"
    private = root / "private-references"
    sources.mkdir()
    private.mkdir(mode=0o700)
    sales, energy, availability = (sources / f"{name}.sqlite" for name in ("sales", "energy", "availability"))
    create_source(sales)
    _energy_source(energy)
    _availability_source(availability)
    for source in (sales, energy, availability):
        source.chmod(0o444)
    source_by_case = dict(zip(CASE_IDS, (sales, sales, energy, availability), strict=True))
    evaluator_sha = _sha(Path(__file__))
    cases = []
    for case_id in CASE_IDS:
        source = source_by_case[case_id]
        requirements = _requirements(case_id)
        status = "cannot_answer" if case_id == "missing-cost" else "completed"
        tables = (
            independent_reference(source)
            if case_id == "sales-refunds"
            else _energy_oracle(source)
            if case_id == "irregular-energy"
            else _availability_oracle(source)
            if case_id == "service-availability"
            else {}
        )
        reference = {
            "schema_version": 1,
            "case_id": case_id,
            "expected_status": status,
            "source_sha256": _sha(source),
            "source_content_sha256": _source_content_sha(source),
            "tables": tables,
            "numeric_tolerance": {"rel": 1e-9, "abs": 1e-8},
            "requirements": requirements,
            "refusal_rule": (
                "An absent/missing/required cost input must be named; no report substituting "
                "revenue for profit."
            ),
        }
        path = private / f"{case_id}.json"
        path.write_bytes(_canonical(reference) + b"\n")
        path.chmod(0o600)
        cases.append(
            AnalysisCase(
                case_id=case_id,
                brief=_case_brief(case_id, requirements),
                source=source,
                reference=path,
                source_sha256=reference["source_sha256"],
                source_content_sha256=reference["source_content_sha256"],
                reference_sha256=_sha(path),
                evaluator_sha256=evaluator_sha,
                expected_status=status,
                requirements=requirements,
            )
        )
    (root / "manifest.json").write_bytes(
        _canonical(
            {
                "suite": "backintel-analysis-controlled-v1",
                "cases": [
                    {
                        "case_id": c.case_id,
                        "source": str(c.source.relative_to(root)),
                        "source_sha256": c.source_sha256,
                        "source_content_sha256": c.source_content_sha256,
                        "reference": str(c.reference.relative_to(root)),
                        "reference_sha256": c.reference_sha256,
                        "brief_sha256": hashlib.sha256(_canonical(c.brief.model_dump())).hexdigest(),
                        "evaluator_sha256": c.evaluator_sha256,
                        "expected_status": c.expected_status,
                    }
                    for c in cases
                ],
                "unique_source_fixtures": 3,
                "model_calls": 0,
            }
        )
        + b"\n"
    )
    return cases


def scripted_spec(case: AnalysisCase) -> dict:
    """Execute host-only SQL reference solution; no oracle values are copied into the report."""
    if case.expected_status != "completed":
        raise ValueError("A refusal case does not have a report solution")
    queries = reference_queries(case.case_id)
    store = case.open_store()
    tables = []
    try:
        for table_id, query in queries.items():
            result = store.query(query, max_rows=10001)
            if result.truncated:
                raise ValueError("Reference solution returned an unexpectedly truncated table")
            tables.append(
                {
                    "id": table_id,
                    "title": table_id.replace("_", " ").title(),
                    "columns": result.columns,
                    "rows": result.rows,
                    "units": case.requirements["tables"][table_id]["units"],
                    "evidence_ids": [table_id + "-query"],
                }
            )
    finally:
        store.close()
    return {
        "run_id": "case-" + case.case_id,
        "schema_version": 1,
        "title": {
            "sales-refunds": "Delivered revenue after refunds",
            "irregular-energy": "Observed energy and missing coverage",
            "service-availability": "Service availability outside planned maintenance",
        }[case.case_id],
        "summary": (
            "Controlled reference integration: calculated tables answer the declared business "
            "brief. This execution uses evaluator-written code and does not measure model "
            "reasoning."
        ),
        "findings": [],
        "caveats": list(case.brief.known_limitations),
        "sources": [
            {
                "id": "assigned",
                "snapshot": "sha256:" + case.source_sha256,
                "description": "Controlled SQLite source: " + case.case_id,
            }
        ],
        "evidence": [
            {"id": name + "-query", "kind": "sql", "code": query, "source_ids": ["assigned"]}
            for name, query in queries.items()
        ],
        "tables": tables,
        "metrics": copy.deepcopy(case.requirements["metrics"]),
        "charts": copy.deepcopy(case.requirements["charts"]),
    }


def _same_cell(actual, expected, tolerance: dict) -> bool:
    if type(expected) in (int, float):
        return (
            type(actual) in (int, float)
            and math.isfinite(actual)
            and math.isclose(actual, expected, rel_tol=tolerance["rel"], abs_tol=tolerance["abs"])
        )
    return type(actual) is type(expected) and actual == expected


def _matching_rows(actual: list, expected: list, tolerance: dict) -> bool:
    remaining = list(expected)
    for row in actual:
        for index, target in enumerate(remaining):
            if len(row) == len(target) and all(
                _same_cell(a, b, tolerance) for a, b in zip(row, target, strict=True)
            ):
                remaining.pop(index)
                break
        else:
            return False
    return not remaining


def verify_case_report(case: AnalysisCase, report: dict) -> None:
    """Check independent numbers/units/bindings, accepting equivalent computations/order.

    Bundle integrity, executable evidence and narrative/visual grading are separate checks.
    This function never requires a particular SQL program or tool sequence.
    """
    if case.expected_status != "completed":
        raise ValueError("This case requires refusal, not an analytical report")
    if _sha(case.source) != case.source_sha256 or _sha(case.reference) != case.reference_sha256:
        raise ValueError("Source or hidden reference changed after case preparation")
    reference = json.loads(case.reference.read_text())
    tables = report.get("tables", [])
    if not isinstance(tables, list) or any(not isinstance(t, dict) for t in tables):
        raise ValueError("Report tables must be objects")
    actual = {t.get("id"): t for t in tables}
    if len(actual) != len(tables):
        raise ValueError("Duplicate table identifiers")
    for name, expected in reference["tables"].items():
        table = actual.get(name)
        if table is None:
            raise ValueError(f"Missing required table {name}")
        columns = table.get("columns", [])
        if len(columns) != len(set(columns)) or set(columns) != set(expected["columns"]):
            raise ValueError(f"Table {name} has incorrect columns")
        order = [columns.index(c) for c in expected["columns"]]
        rows = table.get("rows", [])
        if any(not isinstance(r, list) or len(r) != len(columns) for r in rows):
            raise ValueError(f"Table {name} has malformed rows")
        arranged = [[r[i] for i in order] for r in rows]
        if not _matching_rows(arranged, expected["rows"], reference["numeric_tolerance"]):
            raise ValueError(f"Table {name} differs from the independent raw-source reference")
        if any(
            table.get("units", {}).get(c) != unit
            for c, unit in case.requirements["tables"][name]["units"].items()
        ):
            raise ValueError(f"Table {name} has incorrect units")
    for required in case.requirements["metrics"]:
        if not any(
            all(m.get(k) == required[k] for k in ("id", "table", "row", "column"))
            for m in report.get("metrics", [])
        ):
            raise ValueError("Required summary metric is missing or incorrectly bound")
    for required in case.requirements["charts"]:
        keys = [k for k in ("kind", "table", "x", "y", "z") if k in required]
        if not any(all(c.get(k) == required[k] for k in keys) for c in report.get("charts", [])):
            raise ValueError("Required analytical chart is missing or incorrectly bound")


def _explains_missing_cost(reason: str) -> bool:
    """Recognize explicit missing-input statements, not disconnected keywords.

    This is a conservative language check, not a semantic judge. Ambiguous wording
    remains a failed automatic check for review rather than an inferred pass.
    """
    cost = r"\b(?:costs?|expenses?|cogs)\b"
    absence = r"(?:missing|absent|unavailable|not\s+(?:provided|supplied|available|present|included))"
    modifiers = r"(?:(?:required|product|unit|operating|operational|purchase|actual|the|any)\s+)*"
    has_gap = False
    for clause in re.split(r"[.!?;\n]", reason.lower()):
        # Negating an absence (or asserting presence) cannot establish a data gap.
        if re.search(r"\b(?:not|never|isn't|aren't|isn’t|aren’t)\s+(?:missing|absent|unavailable)\b", clause):
            return False
        negative_subject = re.search(r"\b(?:no|without|lacks?|lacking)\s+" + modifiers + cost, clause)
        if not negative_subject and re.search(
            cost + r".{0,60}\b(?:are|is)\s+(?:present|available|provided|supplied)\b", clause
        ):
            return False
        if re.search(r"\bnot\s+(?:true|the case)\b", clause):
            continue
        # Costs may be qualified by units or grouped with other absent inputs.
        if re.search(cost + r".{0,100}\b(?:are|is|were|was)\s+" + absence + r"\b", clause):
            has_gap = True
        if re.search(r"\b" + absence + r"[:\s]+" + modifiers + cost, clause):
            has_gap = True
        if re.search(
            r"\b(?:no|without|lacks?|lacking)\s+"
            + modifiers
            + cost
            + r"(?:\s+(?:data|inputs?|fields?|records?|information))?"
            + r"(?=\s*(?:[,/:]|$|\b(?:is|are|for|to|in|and|or)\b))",
            clause,
        ):
            has_gap = True
    return has_gap


def verify_case_completion(case: AnalysisCase, completion: dict, report: dict | None = None) -> None:
    if _sha(case.source) != case.source_sha256 or _sha(case.reference) != case.reference_sha256:
        raise ValueError("Source or hidden reference changed after case preparation")
    if completion.get("status") != case.expected_status:
        raise ValueError(f"Expected {case.expected_status}, received {completion.get('status')}")
    if case.expected_status == "completed":
        if report is None:
            raise ValueError("Completed analysis has no report")
        verify_case_report(case, report)
        return
    reason = completion.get("reason") or ""
    if not isinstance(reason, str) or not _explains_missing_cost(reason):
        raise ValueError("Refusal must explain the absent required cost inputs")
    if report is not None:
        raise ValueError("Missing-cost refusal must not deliver a substitute profit report")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Prepare controlled analytical cases without calling a model"
    )
    parser.add_argument("output", type=Path, help="A new evaluator-owned directory")
    args = parser.parse_args()
    cases = build_cases(args.output)
    print(
        json.dumps(
            {
                "case_ids": [case.case_id for case in cases],
                "manifest": str(args.output / "manifest.json"),
                "model_calls": 0,
            },
            indent=2,
        )
    )
