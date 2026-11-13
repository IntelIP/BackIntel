"""No-inference transport-package smoke: isolated raw files to independently graded artifacts.

This is deliberately scripted evaluator tooling, not a live model result. References
and mappings stay on the host; only selected raw files and source definitions enter the VM.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from build_unfamiliar_references import write_json
from grade_unfamiliar_report import grade_run
from run_analysis_demo import ScriptedAnalysisModel, call

from backintel.analysis import AnalysisBrief, run_analysis
from backintel.stores.package import PackageStore, digest

EVIDENCE = """import json, os
from datetime import datetime
from pathlib import Path
import polars as pl
frame = pl.scan_parquet(Path(os.environ['BACKINTEL_FILES_DIR']) / 'green_tripdata_2023-01.parquet')
inside = pl.col('lpep_pickup_datetime').is_between(
    datetime(2023,1,1), datetime(2023,2,1), closed='left').fill_null(False)
counts = frame.select(inside.sum().alias('inside'), (~inside).sum().alias('outside')).collect().row(0)
print(json.dumps({'columns': ['Population', 'Rows'],
    'rows': [['January pickups', counts[0]], ['Outside January', counts[1]]]}))
"""


def scripted_model(store: PackageStore) -> ScriptedAnalysisModel:
    isolation = f"""import json, os
from pathlib import Path
root = Path(os.environ['BACKINTEL_FILES_DIR'])
assert {{p.name for p in root.iterdir()}} == {set(store.files)!r}
assert not Path('/var/run/docker.sock').exists()
assert not Path({str(store.directory.parent)!r}).exists()
assert not any(name in os.environ for name in [
    'OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'OPENROUTER_API_KEY', 'LANGSMITH_API_KEY'])
assert not any(p.name == 'package.json' or 'evaluator' in p.name for p in root.iterdir())
for path in root.iterdir():
    try:
        with path.open('ab'):
            pass
    except OSError:
        continue
    raise AssertionError('Source unexpectedly writable')
print(json.dumps({{'isolation_checks_passed': True,
    'assigned_files': sorted(p.name for p in root.iterdir())}}))
"""
    program = f"""import contextlib, io, json
from pathlib import Path
code = {EVIDENCE!r}
captured = io.StringIO()
with contextlib.redirect_stdout(captured):
    exec(code)
table = json.loads(captured.getvalue())
table.update({{'id': 'population', 'title': 'Pickup timestamp population',
    'units': {{'Rows': 'trips'}}, 'evidence_ids': ['counts']}})
report = {{
    'title': 'January pickup population',
    'summary': 'Scripted transport integration: recorded pickup timestamps define the January population.',
    'findings': ['The two populations account for all records in the assigned trip file.'],
    'caveats': ['Offline scripted integration, not measured model competence.',
        'Recorded timestamps use the source convention; no timezone conversion is applied.'],
    'tables': [table],
    'charts': [{{'id': 'population', 'title': 'Trips by pickup timestamp window',
        'kind': 'bar', 'table': 'population', 'x': 'Population', 'y': 'Rows'}}],
    'evidence': [{{'id': 'counts', 'kind': 'python', 'code': code, 'source_ids': ['assigned']}}]
}}
Path('/workspace/report.json').write_text(json.dumps(report))
print(json.dumps({{'spec_written': True}}))
"""
    steps = [
        ("list_tables", {}),
        ("describe_table", {"table": "green_tripdata_2023-01.parquet"}),
        ("run_python", {"code": isolation}),
        ("run_python", {"code": program}),
        ("render_report", {"spec_path": "/workspace/report.json"}),
        ("inspect_chart", {"path": "/artifacts/report/charts/population.png"}),
        (
            "AnalysisCompletion",
            {
                "status": "completed",
                "summary": "The January pickup population is separated from out-of-window records.",
                "caveats": ["Scripted integration; no model capability claim."],
            },
        ),
    ]
    return ScriptedAnalysisModel(responses=[call(name, args, i) for i, (name, args) in enumerate(steps)])


async def run_smoke(package: Path, output: Path, references: Path) -> dict:
    store = PackageStore(package, dataset=package.name)
    if store.manifest.get("domain") != "transport":
        raise ValueError("This infrastructure demonstration requires the transport package")
    before = {name: digest(store.directory / name) for name in store.files}
    record = await run_analysis(
        AnalysisBrief(
            objective="Count trip records with pickup timestamps in January 2023 and outside it.",
            business_context="Offline package integration demonstration using NYC TLC raw records.",
            time_window="2023-01-01 inclusive to 2023-02-01 exclusive",
        ),
        model=scripted_model(store),
        model_id="scripted/unfamiliar-package-smoke",
        store=store,
        output=output,
        scripted=True,
        max_model_calls=10,
        max_tool_calls=12,
        timeout_s=240,
    )
    if record["status"] != "completed":
        raise RuntimeError(f"Scripted smoke failed: {record.get('error', record['status'])}")
    isolation_checked, chart_returned = False, False
    for message in record["messages"]:
        if message.get("type") != "tool":
            continue
        content = message.get("content", "")
        if message.get("name") in {"run_python", "render_report"}:
            result = json.loads(content)
            if result.get("exit_code") != 0:
                raise ValueError("Scripted smoke contains a failed command")
            isolation_checked |= '"isolation_checks_passed": true' in result.get("stdout", "")
        if message.get("name") == "inspect_chart":
            chart_returned |= "data:image/png;base64," in str(content)
    if not isolation_checked or not chart_returned:
        raise ValueError("Isolation assertions or chart delivery did not execute")
    if before != {name: digest(store.directory / name) for name in store.files}:
        raise ValueError("Assigned source changed")
    facts = []
    for row, key in enumerate(("eligible_rows", "excluded_rows")):
        scope = {
            "metric": "trip record count",
            "population": "assigned trip rows",
            "window": "pickup timestamp in [2023-01-01,2023-02-01)"
            if row == 0
            else "all other pickup timestamps",
            "grain": "trip record",
        }
        facts.append(
            {
                "reference_path": [key],
                "table_id": "population",
                "row": row,
                "column": "Rows",
                "expected_unit": "trips",
                "expected_scope": scope,
                "interpreted_scope": scope,
            }
        )
    mapping = {
        "schema_version": 1,
        "case_id": "transport-01",
        "run_sha256": digest(output / "run.json"),
        "reference_sha256": digest(references),
        "report_sha256": digest(output / "artifacts/report/report.json"),
        "facts": facts,
    }
    mapping_path = output / "evaluator-mapping.json"
    write_json(mapping_path, mapping)
    grade = grade_run(output, references, mapping_path)
    if not grade["fixed_reference_correct"]:
        raise ValueError("Scripted report differs from independent fixed reference")
    write_json(output / "evaluator-grade.json", grade)
    summary = {
        "execution": "scripted integration; not a model evaluation",
        "provider_calls": 0,
        "model_cost_usd": 0,
        "assigned_file_isolation": isolation_checked,
        "read_only_sources_unchanged": True,
        "chart_returned": chart_returned,
        "fixed_reference_correct": grade["fixed_reference_correct"],
        "delivery_consistent": grade["delivery_consistent"],
        "task_pass": None,
        "resources": record["resources"],
        "report": str(output / "artifacts/report/report.html"),
    }
    write_json(output / "smoke-summary.json", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--references", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(asyncio.run(run_smoke(args.package, args.output, args.references)), indent=2))


if __name__ == "__main__":
    main()
