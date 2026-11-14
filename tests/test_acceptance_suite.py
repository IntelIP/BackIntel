"""Fixture construction, answerability contrasts, and information cutoffs."""

import json
import sqlite3

import pytest

from backintel.bench.acceptance import build_acceptance, verify_acceptance_data
from backintel.settings import Settings
from backintel.stores import open_store


def build(tmp_path, split="development"):
    settings = Settings.from_env({"BACKINTEL_DATA_DIR": str(tmp_path / "data")})
    suite = build_acceptance(settings, split, output=tmp_path / "hidden")
    return settings, suite


def case(suite, suffix):
    return next(s for s in suite.scenarios if s.id == f"acceptance-v1-{suite.split}-{suffix}")


def facts(scenario):
    return {f["name"]: f["value"] for f in scenario.expected}


def test_splits_are_reproducible_but_do_not_share_worlds(tmp_path):
    settings, dev = build(tmp_path)
    _, rebuilt = build(tmp_path)
    _, reserved = build(tmp_path, "acceptance")
    assert dev.data_hash == rebuilt.data_hash
    assert dev.reference_hash == rebuilt.reference_hash
    assert dev.data_hash != reserved.data_hash
    assert {s.store for s in dev.scenarios}.isdisjoint(s.store for s in reserved.scenarios)
    assert case(dev, "profit-complete").expected != case(reserved, "profit-complete").expected
    assert verify_acceptance_data(dev, settings)
    for suite in (dev, reserved):
        manifest = json.loads(suite.manifest_path.read_text())
        assert len(manifest["reference_checks"]) == sum(s.answerable for s in suite.scenarios)
        assert all(check["matches"] for check in manifest["reference_checks"])


def test_cost_availability_controls_answerability_not_the_word_profit(tmp_path):
    settings, suite = build(tmp_path)
    complete, absent, partial, zero = (
        case(suite, f"profit-{suffix}") for suffix in ("complete", "missing", "partial", "zero")
    )
    assert complete.answerable and complete.expected > 0
    assert zero.answerable and zero.expected == 0
    assert not absent.answerable and not partial.answerable
    with sqlite3.connect(settings.stores_dir / "sqlite" / f"{absent.store.split(':')[1]}.sqlite") as con:
        tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        assert "expense_lines" not in tables
        assert not any("expected" in name or "answer" in name for name in tables)
    store = open_store(partial.store, settings)
    try:
        coverage = store.query(
            "SELECT period_end_exclusive, complete FROM ledger_coverage WHERE ledger='expense_lines'"
        )
        assert coverage.rows == [["2024-03-15", 0]]
    finally:
        store.close()
    assert case(suite, "revenue").expected == case(suite, "revenue-duplicates").expected


def test_future_delivery_observations_are_hidden_until_the_followup(tmp_path):
    settings, suite = build(tmp_path)
    first, later = (
        case(suite, f"replay-{name}") for name in ("late-observations", "late-observations-followup")
    )
    a, b = facts(first), facts(later)
    assert a["status"] == "NO_CHANGE"
    assert a["eligible_current"] == 2 and a["pending_current"] == 2
    assert b["status"] == "CHANGE_DETECTED"
    assert b["eligible_current"] == 4 and b["pending_current"] == 0
    store = open_store(first.store, settings)
    try:
        assert store.query("SELECT COUNT(*) FROM shipments WHERE delivered_at>='2024-07-01'").rows == [[0]]
        assert list(store.python_mounts()) == [str(store.path)]
    finally:
        store.close()
    assert not case(suite, "replay-unobserved-period").answerable


def test_duplicate_exports_and_mix_changes_are_not_business_change_alerts(tmp_path):
    _, suite = build(tmp_path)
    assert facts(case(suite, "replay-stable")) == facts(case(suite, "replay-duplicate-export"))
    assert facts(case(suite, "replay-shift"))["status"] == "CHANGE_DETECTED"
    assert facts(case(suite, "replay-price-mix-only"))["status"] == "NO_CHANGE"
    assert facts(case(suite, "replay-price-shift"))["status"] == "CHANGE_DETECTED"


def test_changed_fixture_is_detected_before_it_can_be_a_comparable_run(tmp_path):
    settings, suite = build(tmp_path)
    scenario = case(suite, "revenue")
    path = settings.stores_dir / "sqlite" / f"{scenario.store.split(':')[1]}.sqlite"
    with sqlite3.connect(path) as con:
        con.execute("UPDATE sales_lines SET amount_minor=0")
    assert not verify_acceptance_data(suite, settings)


def test_refreshed_reserved_worlds_preserve_old_evidence_and_have_independent_checks(tmp_path):
    settings, original = build(tmp_path, "acceptance")
    original_manifest = original.manifest_path.read_bytes()
    refreshed = build_acceptance(
        settings, "acceptance", output=tmp_path / "fresh-hidden", reserved_generation=2
    )
    assert len(refreshed.scenarios) == 17
    assert original.manifest_path.read_bytes() == original_manifest
    assert {s.store for s in original.scenarios}.isdisjoint(s.store for s in refreshed.scenarios)
    assert original.data_hash != refreshed.data_hash
    assert original.reference_hash != refreshed.reference_hash
    assert all(s.id.startswith("acceptance-v1-reserved-2-acceptance-") for s in refreshed.scenarios)
    old_profit = next(s for s in original.scenarios if s.id.endswith("-profit-complete"))
    new_profit = next(s for s in refreshed.scenarios if s.id.endswith("-profit-complete"))
    assert old_profit.expected != new_profit.expected
    manifest = json.loads(refreshed.manifest_path.read_text())
    assert len(manifest["reference_checks"]) == sum(s.answerable for s in refreshed.scenarios)
    assert all(check["matches"] for check in manifest["reference_checks"])
    assert verify_acceptance_data(original, settings) and verify_acceptance_data(refreshed, settings)
    rebuilt = build_acceptance(
        settings, "acceptance", output=tmp_path / "fresh-hidden", reserved_generation=2
    )
    assert refreshed.data_hash == rebuilt.data_hash
    assert refreshed.reference_hash == rebuilt.reference_hash


def test_third_reserved_generation_retains_both_consumed_generations(tmp_path):
    settings, first = build(tmp_path, "acceptance")
    second = build_acceptance(settings, "acceptance", output=tmp_path / "second", reserved_generation=2)
    original_files = {p: p.read_bytes() for p in (first.manifest_path, second.manifest_path)}
    third = build_acceptance(settings, "acceptance", output=tmp_path / "third", reserved_generation=3)
    assert len(third.scenarios) == 17
    assert all(p.read_bytes() == data for p, data in original_files.items())
    previous_stores = {s.store for suite in (first, second) for s in suite.scenarios}
    assert previous_stores.isdisjoint(s.store for s in third.scenarios)
    assert third.reference_hash not in {first.reference_hash, second.reference_hash}
    manifest = json.loads(third.manifest_path.read_text())
    assert len(manifest["reference_checks"]) == 13
    assert all(c["matches"] for c in manifest["reference_checks"])
    assert all(verify_acceptance_data(suite, settings) for suite in (first, second, third))


@pytest.mark.parametrize("split,generation", [("development", 2), ("acceptance", 4)])
def test_reserved_refresh_cannot_silently_replace_development_or_choose_arbitrary_worlds(
    tmp_path, split, generation
):
    with pytest.raises(ValueError, match="Reserved generation"):
        build_acceptance(
            Settings.from_env({"BACKINTEL_DATA_DIR": str(tmp_path)}),
            split,
            output=tmp_path / "hidden",
            reserved_generation=generation,
        )
