"""Fixture construction, answerability contrasts, and information cutoffs."""

import json
import sqlite3

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
