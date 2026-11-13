"""Narrow evaluator checks for explicitly mapped report facts, not narrative grading.

The evaluator supplies a mapping from a report cell to an independently calculated
reference and its interpretation. The mapping must not be inferred from matching
numbers alone. Execution receipts come from existing sandbox reproduce_report;
this module does not execute untrusted analyst code on the host.
"""

from __future__ import annotations

from build_unfamiliar_references import differences

from backintel.artifacts import validate_report


def check_bound_fact(
    report: dict,
    *,
    table_id: str,
    row: int,
    column: str,
    expected_value: int | float,
    expected_unit: str,
    expected_scope: dict,
    interpreted_scope: dict,
    reproduction: dict,
) -> dict:
    """Require value, unit, independently interpreted scope and executed evidence.

    interpreted_scope is evaluator-owned annotation, not a trusted analyst claim.
    Scope keys are metric, population, window and grain. Equivalent wording/units
    can be normalized by the evaluator before calling; no numeric fallback matches.
    Passing this check certifies one bound fact only, never the surrounding prose.
    """
    normalized = validate_report(report)
    required_scope = {"metric", "population", "window", "grain"}
    if set(expected_scope) != required_scope or set(interpreted_scope) != required_scope:
        raise ValueError("Incomplete independent interpretation")
    if expected_scope != interpreted_scope:
        raise ValueError("Metric/population/window/grain differs from the independent reference")
    table = next((table for table in normalized["tables"] if table["id"] == table_id), None)
    if (
        table is None
        or column not in table["columns"]
        or type(row) is not int
        or not 0 <= row < len(table["rows"])
    ):
        raise ValueError("Fact must bind an existing table cell")
    if table["units"].get(column) != expected_unit:
        raise ValueError("Wrong or missing unit")
    actual = table["rows"][row][table["columns"].index(column)]
    if differences(expected_value, actual):
        raise ValueError("Fact differs from independent reference")
    if table_id not in reproduction.get("tables_reproduced", []):
        raise ValueError("Table has not been reproduced in the sandbox")
    if not set(table["evidence_ids"]).intersection(reproduction.get("executed_evidence", [])):
        raise ValueError("Cited evidence has not been executed")
    return {"bound_fact_supported": True, "narrative_assessed": False, "business_usefulness_assessed": False}
