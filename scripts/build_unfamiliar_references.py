"""Offline evaluator references, outside analyst mounts and runtime imports.

Persist both independently calculated paths and any discrepancies before failing.
The three refusal answers are source-availability judgments, not human-calibrated
semantic graders. Missing-column guards detect schema drift; they do not prove that
an arbitrary model refusal explained the correct source limitation.
"""

from __future__ import annotations

import argparse
import json
import math
from datetime import UTC, datetime
from pathlib import Path

from qualify_unfamiliar_data import MANIFEST, ROOT, digest, verify_sources
from unfamiliar_python_references import calculate as calculate_python


def differences(first, second, path: str = "") -> list[dict]:
    """Counts/labels/sets exact; finite continuous quantities use frozen tolerances."""
    if isinstance(first, dict) and isinstance(second, dict):
        found = []
        if first.keys() != second.keys():
            found.append({"path": path, "reason": "keys", "first": sorted(first), "second": sorted(second)})
        for key in first.keys() & second.keys():
            found.extend(differences(first[key], second[key], f"{path}/{key}"))
        return found
    if isinstance(first, list) and isinstance(second, list):
        if len(first) != len(second):
            return [{"path": path, "reason": "length", "first": len(first), "second": len(second)}]
        return [
            item
            for i, (a, b) in enumerate(zip(first, second, strict=True))
            for item in differences(a, b, f"{path}/{i}")
        ]
    if type(first) is float and type(second) in (int, float):
        equal = (
            math.isfinite(first)
            and math.isfinite(second)
            and math.isclose(first, second, abs_tol=1e-6, rel_tol=1e-8)
        )
    else:
        equal = type(first) is type(second) and first == second
    return [] if equal else [{"path": path, "reason": "value/type", "first": first, "second": second}]


def write_json(path: Path, value: dict) -> None:
    with path.open("x") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")


def save_comparison(output: Path, first: dict, second: dict, *, inputs: dict) -> dict:
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "python.json", first)
    write_json(output / "sql.json", second)
    discrepancies = differences(first, second)
    write_json(output / "discrepancies.json", {"differences": discrepancies})
    receipt = {
        "created_at": datetime.now(UTC).isoformat(),
        "inputs": inputs,
        "cases": len(first),
        "numeric_cases": sum(case.get("status") != "cannot_answer" for case in first.values()),
        "insufficient_data_cases": sum(case.get("status") == "cannot_answer" for case in first.values()),
        "difference_count": len(discrepancies),
        "python_sha256": digest(output / "python.json"),
        "sql_sha256": digest(output / "sql.json"),
        "counts_and_labels": "exact",
        "continuous_numbers": {"absolute_tolerance": 1e-6, "relative_tolerance": 1e-8},
        "model_calls": 0,
        "human_calibration": False,
    }
    write_json(output / "receipt.json", receipt)
    return receipt


def main() -> None:
    from unfamiliar_sql_references import calculate as calculate_sql

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data/unfamiliar-v1")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    verify_sources(args.data_dir, download=False)
    raw = args.data_dir / "raw"
    receipt = save_comparison(
        args.output,
        calculate_python(raw),
        calculate_sql(raw),
        inputs={
            "sources_sha256": digest(MANIFEST),
            "tasks_sha256": digest(ROOT / "benchmarks/unfamiliar/unfamiliar-v1/development-tasks.json"),
            "python_implementation_sha256": digest(
                Path(__file__).with_name("unfamiliar_python_references.py")
            ),
            "sql_implementation_sha256": digest(Path(__file__).with_name("unfamiliar_sql_references.py")),
            "comparison_implementation_sha256": digest(Path(__file__)),
        },
    )
    print(json.dumps(receipt))
    if receipt["difference_count"]:
        raise SystemExit("Reference paths disagree; preserve files and investigate before grading")


if __name__ == "__main__":
    main()
