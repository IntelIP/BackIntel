"""Allowlist boundaries and grading counterexamples, using only synthetic inputs."""

import hashlib
import json
import sys
from copy import deepcopy
from pathlib import Path

import polars as pl
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from grade_unfamiliar_report import grade_mapped_report, grade_run  # noqa: E402
from package_unfamiliar_data import package_domain  # noqa: E402

from backintel.artifacts import render_report, validate_report  # noqa: E402
from backintel.settings import Settings  # noqa: E402
from backintel.stores import open_store  # noqa: E402
from backintel.stores.package import PackageStore, digest  # noqa: E402


@pytest.fixture
def source(tmp_path):
    raw = tmp_path / "data/raw"
    raw.mkdir(parents=True)
    (raw / "data.csv").write_text("value,label\n?,unknown\n0,zero\n")
    (raw / "reserved.csv").write_text("not assigned")
    (raw / "solution.py").write_text("not assigned")
    docs = tmp_path / "source-docs"
    docs.mkdir()
    (docs / "test.md").write_text("Ordinary source units, no answers.")
    entry = {
        "file": "data.csv",
        "bytes": (raw / "data.csv").stat().st_size,
        "sha256": digest(raw / "data.csv"),
    }
    manifest = tmp_path / "sources.json"
    manifest.write_text(
        json.dumps(
            {
                "assets": [entry],
                "domains": [
                    {
                        "id": "test",
                        "split": "development",
                        "assets": ["data.csv"],
                        "source": "synthetic",
                        "publisher": "fixture",
                        "rights": "test",
                        "source_url": "https://example.test",
                    }
                ],
            }
        )
    )
    return tmp_path / "data", manifest, docs


def package(source, output):
    data, manifest, docs = source
    return package_domain(data, output, "test", manifest=manifest, source_docs=docs)


def test_packages_only_allowlisted_assets_and_preserves_raw_labels(source, tmp_path):
    output = tmp_path / "stores/package/test"
    result = package(source, output)
    store = open_store("package:test", Settings.from_env({"BACKINTEL_DATA_DIR": str(tmp_path)}))
    assert result["files"] == 2
    assert set(path.name for path in output.iterdir()) == {"data.csv", "source-notes.md", "package.json"}
    assert store.python_mounts() == {
        str(output / name): f"/data/assigned/{name}" for name in ("data.csv", "source-notes.md")
    }
    assert all(Path(path).is_file() for path in store.python_mounts())
    assert store.list_tables()[0].row_count == 2
    assert store.describe_table("data.csv").sample == [
        {"value": "?", "label": "unknown"},
        {"value": "0", "label": "zero"},
    ]
    assert not (output / "data.csv").stat().st_mode & 0o222
    assert store.sandbox_network() is None
    with pytest.raises(ValueError, match="new package"):
        package(source, output)
    with pytest.raises(ValueError, match="simple"):
        open_store("package:../../secret", Settings.from_env({"BACKINTEL_DATA_DIR": str(tmp_path)}))


@pytest.mark.parametrize("change", ["hash", "symlink", "extra", "unsupported", "missing", "malformed"])
def test_package_rejects_changed_linked_extra_and_executable_files(source, tmp_path, change):
    output = tmp_path / "package"
    package(source, output)
    output.chmod(0o755)
    path = output / "data.csv"
    path.chmod(0o644)
    if change == "hash":
        path.write_text("different")
    elif change == "symlink":
        path.unlink()
        path.symlink_to(source[0] / "raw/data.csv")
    elif change == "extra":
        (output / "answer.json").write_text("{}")
    elif change == "missing":
        path.unlink()
    elif change == "malformed":
        manifest = output / "package.json"
        manifest.chmod(0o644)
        manifest.write_text("[]")
    else:
        manifest = output / "package.json"
        manifest.chmod(0o644)
        value = json.loads(manifest.read_text())
        value["files"][0]["format"] = "python"
        manifest.write_text(json.dumps(value))
    with pytest.raises((ValueError, FileNotFoundError)):
        PackageStore(output, dataset="test")


def test_parquet_package_discovery_is_bounded(tmp_path):
    pl.DataFrame({"n": list(range(10)), "s": ["x" * 300] * 10}).write_parquet(tmp_path / "data.parquet")
    path = tmp_path / "data.parquet"
    (tmp_path / "package.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "files": [
                    {
                        "file": path.name,
                        "format": "parquet",
                        "bytes": path.stat().st_size,
                        "sha256": digest(path),
                    }
                ],
            }
        )
    )
    table = PackageStore(tmp_path, dataset="fixture").describe_table("data.parquet")
    assert table.row_count == 10 and len(table.sample) == 3
    assert len(table.sample[0]["s"]) == 200


def test_discovery_rejects_unbounded_schema_before_a_run(source, tmp_path):
    raw = source[0] / "raw/data.csv"
    raw.write_text(",".join(f"c{i}" for i in range(65)) + "\n" + ",".join("1" for _ in range(65)) + "\n")
    document = json.loads(source[1].read_text())
    document["assets"][0].update(bytes=raw.stat().st_size, sha256=digest(raw))
    source[1].write_text(json.dumps(document))
    with pytest.raises(ValueError, match="1–64 scalar columns"):
        package(source, tmp_path / "package")


@pytest.fixture
def grading_case():
    report = {
        "run_id": "fixture",
        "title": "Sample",
        "summary": "An observed sum.",
        "sources": [{"id": "s", "snapshot": "sha256:fixture", "description": "Synthetic"}],
        "evidence": [{"id": "e", "kind": "python", "code": "print('bounded result')", "source_ids": ["s"]}],
        "tables": [
            {
                "id": "t",
                "title": "Totals",
                "columns": ["group", "amount"],
                "rows": [["A", 33.0]],
                "units": {"amount": "USD"},
                "evidence_ids": ["e"],
            }
        ],
    }
    scope = {
        "metric": "signed recorded amount",
        "population": "all assigned records",
        "window": "assigned",
        "grain": "group",
    }
    facts = [
        {
            "reference_path": [key],
            "table_id": "t",
            "row": 0,
            "column": column,
            "expected_unit": "USD",
            "expected_scope": deepcopy(scope),
            "interpreted_scope": deepcopy(scope),
        }
        for key, column in [("group", "group"), ("amount", "amount")]
    ]
    return (
        report,
        {"group": "A", "amount": 33.0},
        {"facts": facts},
        {"tables_reproduced": ["t"], "executed_evidence": ["e"]},
    )


def test_reference_coverage_does_not_certify_extra_claims_or_narrative(grading_case):
    report, reference, mapping, reproduction = grading_case
    report["findings"] = ["An unassessed causal assertion."]
    result = grade_mapped_report(report, reference, mapping, reproduction)
    assert result["fixed_reference_correct"]
    assert result["task_pass"] is None and not result["causality_assessed"]
    partial = grade_mapped_report(report, reference, {"facts": mapping["facts"][:1]}, reproduction)
    assert not partial["fixed_reference_correct"]
    assert partial["unmapped_numeric_cells"] == [["t", 0, "amount"]]


def test_valid_alternative_layout_uses_explicit_mapping_not_table_names(grading_case):
    report, reference, mapping, reproduction = grading_case
    table = report["tables"][0]
    table.update(id="alternative", columns=["Observed amount", "Segment"], rows=[[33.0, "A"]])
    table["units"] = {"Observed amount": "USD"}
    for fact, column in zip(mapping["facts"], ["Segment", "Observed amount"], strict=True):
        fact.update(table_id="alternative", column=column)
    reproduction["tables_reproduced"] = ["alternative"]
    assert grade_mapped_report(report, reference, mapping, reproduction)["fixed_reference_correct"]


@pytest.mark.parametrize(
    "change", ["wrong_value", "wrong_unit", "wrong_label", "cherry_pick", "broken_evidence"]
)
def test_wrong_values_units_labels_population_and_evidence_fail(grading_case, change):
    report, reference, mapping, reproduction = grading_case
    if change == "wrong_value":
        report["tables"][0]["rows"][0][1] = 99
    elif change == "wrong_unit":
        report["tables"][0]["units"]["amount"] = "EUR"
    elif change == "wrong_label":
        report["tables"][0]["rows"][0][0] = "B"
    elif change == "cherry_pick":
        mapping["facts"][1]["interpreted_scope"]["population"] = "positive rows only"
    else:
        reproduction["executed_evidence"] = []
    assert not grade_mapped_report(report, reference, mapping, reproduction)["fixed_reference_correct"]


def test_delivered_run_grading_binds_host_spec_and_detects_inappropriate_refusal(grading_case, tmp_path):
    report, reference, mapping, reproduction = grading_case
    report = validate_report(report)
    bundle = tmp_path / "artifacts/report"
    render_report(report, bundle)
    record = {
        "status": "completed",
        "run_id": "fixture",
        "completion": {"status": "completed"},
        "render_spec_sha256": hashlib.sha256(json.dumps(report, sort_keys=True).encode()).hexdigest(),
        "reproduction": reproduction,
    }
    run = tmp_path / "run.json"
    run.write_text(json.dumps(record))
    refs = tmp_path / "references.json"
    refs.write_text(json.dumps({"case": reference}))
    path = tmp_path / "mapping.json"
    mapping.update(
        schema_version=1,
        case_id="case",
        run_sha256=digest(run),
        reference_sha256=digest(refs),
        report_sha256=digest(bundle / "report.json"),
    )
    path.write_text(json.dumps(mapping))
    result = grade_run(tmp_path, refs, path)
    assert result["fixed_reference_correct"] and result["delivery_consistent"]
    assert result["task_pass"] is None
    record["render_spec_sha256"] = "wrong"
    run.write_text(json.dumps(record))
    mapping["run_sha256"] = digest(run)
    path.write_text(json.dumps(mapping))
    with pytest.raises(ValueError, match="reproduced specification"):
        grade_run(tmp_path, refs, path)
    record.update(status="cannot_answer", completion={"status": "cannot_answer"})
    run.write_text(json.dumps(record))
    mapping["run_sha256"] = digest(run)
    path.write_text(json.dumps(mapping))
    assert grade_run(tmp_path, refs, path)["task_pass"] is False
    refs.write_text(json.dumps({"case": {"status": "cannot_answer", "missing_inputs": ["costs"]}}))
    mapping["reference_sha256"] = digest(refs)
    path.write_text(json.dumps(mapping))
    result = grade_run(tmp_path, refs, path)
    assert result["status_correct"] and result["task_pass"] is None
    assert not result["refusal_semantics_assessed"]
