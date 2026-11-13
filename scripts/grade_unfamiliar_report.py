"""Grade evaluator-mapped facts in a completed specialist run, without model calls.

Mappings and reference outputs are evaluator-owned. Never give either to the
analyst. This verifies cells/units/interpretation annotations and delivered files;
it does not infer that a correct cell makes surrounding prose or a refusal sound.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from build_unfamiliar_references import differences, write_json
from qualify_unfamiliar_data import digest
from unfamiliar_fact_checks import check_bound_fact

from backintel.analysis import _same_cells
from backintel.artifacts import validate_report, verify_bundle


def leaves(value, path=()) -> dict[tuple, object]:
    if isinstance(value, dict):
        return {
            leaf: item for key, child in value.items() for leaf, item in leaves(child, (*path, key)).items()
        }
    if isinstance(value, list):
        return {
            leaf: item for i, child in enumerate(value) for leaf, item in leaves(child, (*path, i)).items()
        }
    return {path: value}


def grade_mapped_report(report: dict, reference: dict, mapping: dict, reproduction: dict) -> dict:
    """Return separate reference coverage and fact correctness, never a prose pass.

    Each fact supplies reference_path plus the independently interpreted metric,
    population, time window and grain. Counts/labels follow exact typed comparison;
    continuous values keep the predeclared reference tolerance. No value-based matching.
    """
    report = validate_report(report)
    expected = leaves(reference)
    facts = mapping.get("facts")
    if not isinstance(facts, list) or not facts:
        raise ValueError("An evaluator mapping must contain facts")
    seen, cells, results = set(), set(), []
    for fact in facts:
        path = tuple(fact["reference_path"])
        if path not in expected or path in seen:
            raise ValueError("Reference paths must be unique existing leaves")
        seen.add(path)
        cell = (fact["table_id"], fact["row"], fact["column"])
        cells.add(cell)
        try:
            value = expected[path]
            if type(value) in (int, float):
                check_bound_fact(
                    report,
                    expected_value=value,
                    reproduction=reproduction,
                    **{
                        key: fact[key]
                        for key in (
                            "table_id",
                            "row",
                            "column",
                            "expected_unit",
                            "expected_scope",
                            "interpreted_scope",
                        )
                    },
                )
            else:
                # Label/null fields are still part of the fixed reference contract.
                table = next(table for table in report["tables"] if table["id"] == fact["table_id"])
                if type(fact["row"]) is not int or fact["row"] < 0:
                    raise ValueError("Invalid table row")
                actual = table["rows"][fact["row"]][table["columns"].index(fact["column"])]
                if differences(value, actual):
                    raise ValueError("Label/null differs from independent reference")
                scope = {"metric", "population", "window", "grain"}
                if (
                    set(fact["expected_scope"]) != scope
                    or fact["expected_scope"] != fact["interpreted_scope"]
                ):
                    raise ValueError("Independent interpretation differs")
                if table["id"] not in reproduction.get("tables_reproduced", []) or not set(
                    table["evidence_ids"]
                ).intersection(reproduction.get("executed_evidence", [])):
                    raise ValueError("Cited evidence and table have not been reproduced")
            results.append({"reference_path": list(path), "passed": True})
        except (ValueError, KeyError, IndexError, StopIteration) as error:
            results.append({"reference_path": list(path), "passed": False, "reason": str(error)})
    all_numeric = {
        (table["id"], row_index, column)
        for table in report["tables"]
        for row_index, row in enumerate(table["rows"])
        for column, value in zip(table["columns"], row, strict=True)
        if type(value) in (int, float)
    }
    coverage = len(seen) == len(expected)
    correct = coverage and all(item["passed"] for item in results)
    return {
        "fixed_reference_correct": correct,
        "fixed_reference_coverage": {"mapped": len(seen), "required": len(expected), "complete": coverage},
        "facts": results,
        "unmapped_numeric_cells": [list(cell) for cell in sorted(all_numeric - cells)],
        "narrative_assessed": False,
        "causality_assessed": False,
        "task_pass": None,
        "remaining": "Evaluate every additional material claim and narrative/refusal semantics separately.",
    }


def grade_run(run_directory: Path, reference_path: Path, mapping_path: Path) -> dict:
    """Consume a trusted host run record and evaluator annotation; never execute its code."""
    record_path = run_directory / "run.json"
    record = json.loads(record_path.read_text())
    mapping = json.loads(mapping_path.read_text())
    if mapping.get("schema_version") != 1:
        raise ValueError("Evaluator mapping needs schema_version 1")
    if mapping.get("run_sha256") != digest(record_path) or mapping.get("reference_sha256") != digest(
        reference_path
    ):
        raise ValueError("Run or reference identity changed")
    reference = json.loads(reference_path.read_text())[mapping["case_id"]]
    if record.get("status") not in {"completed", "cannot_answer"}:
        return {
            "evaluation_valid": False,
            "task_pass": None,
            "failure_class": "requires_runtime_layer_classification",
            "run_status": record.get("status"),
        }
    completion = record.get("completion") or {}
    if completion.get("status") != record["status"]:
        raise ValueError("Structured completion and run status disagree")
    if reference.get("status") == "cannot_answer":
        return {
            "evaluation_valid": True,
            "status_correct": record["status"] == "cannot_answer",
            "refusal_semantics_assessed": False,
            "task_pass": None,
            "remaining": "Verify the stated data gap, exact requested metric, and absence of fabrication.",
        }
    if record["status"] != "completed":
        return {
            "evaluation_valid": True,
            "status_correct": False,
            "fixed_reference_correct": False,
            "task_pass": False,
            "reason": "The frozen fixed challenge is answerable.",
        }
    bundle = run_directory / "artifacts/report"
    report_path = bundle / "report.json"
    if mapping.get("report_sha256") != digest(report_path):
        raise ValueError("Mapping does not bind this delivered report")
    verify_bundle(bundle)
    report = validate_report(json.loads(report_path.read_text()))
    if report["run_id"] != record["run_id"]:
        raise ValueError("Delivered report belongs to a different run")
    expected_spec = hashlib.sha256(json.dumps(report, sort_keys=True).encode()).hexdigest()
    if record.get("render_spec_sha256") != expected_spec:
        raise ValueError("Delivered report differs from the host-retained reproduced specification")
    from openpyxl import load_workbook

    workbook = load_workbook(bundle / "supporting.xlsx", read_only=True, data_only=True)
    try:
        for index, table in enumerate(report["tables"], 1):
            sheet = workbook[f"T{index}-{table['id']}"[:31]]
            if not _same_cells([list(row) for row in sheet.values], [table["columns"], *table["rows"]]):
                raise ValueError("Workbook differs from the analytical tables")
    finally:
        workbook.close()
    result = grade_mapped_report(report, reference, mapping, record.get("reproduction") or {})
    return {
        "evaluation_valid": True,
        "delivery_consistent": True,
        "status_correct": True,
        **result,
        "case_id": mapping["case_id"],
        "run_sha256": digest(record_path),
        "reference_sha256": digest(reference_path),
        "mapping_sha256": digest(mapping_path),
        "model_calls": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--references", type=Path, required=True)
    parser.add_argument("--mapping", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = grade_run(args.run, args.references, args.mapping)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_json(args.output, result)
    print(json.dumps({key: value for key, value in result.items() if key not in {"facts"}}, indent=2))


if __name__ == "__main__":
    main()
