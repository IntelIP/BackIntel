"""Evaluator-only source facts. Never read reference answers into a model prompt."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta
from pathlib import Path

from backintel.settings import repo_root
from backintel.stores.sqlite import SQLiteStore

# These are observation fields used by the two repository-owned snapshot builders.
# Predicted delivery dates may legitimately extend beyond the observation cutoff.
OBSERVATIONS = {
    "orders": (
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
    ),
    "order_reviews": ("review_creation_date", "review_answer_timestamp"),
    "shipments": ("purchased_at", "delivered_at"),
}


def context_version() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:12]


def _quoted(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _declaration(store: SQLiteStore, case_id: str, source_hash: str, root: Path) -> dict:
    match = re.fullmatch(r"sqlite:olist_asof_(\d{4}-\d{2}(?:-\d{2})?)", store.id)
    if match:
        period = match[1]
        start = datetime.fromisoformat(period if len(period) == 10 else period + "-01")
        end = (
            (start + timedelta(days=1))
            if len(period) == 10
            else datetime(start.year + (start.month == 12), start.month % 12 + 1, 1)
        )
        return {"cutoff_exclusive": end.isoformat(), "origin": "replay store identifier"}
    for manifest_path in sorted(root.glob("*.json")):
        manifest = json.loads(manifest_path.read_text())
        world = manifest.get("worlds", {}).get(case_id, {})
        cutoff = manifest.get("planted_changes", {}).get(case_id, {}).get("cutoff_exclusive")
        if cutoff and world.get("store") == store.id:
            if world.get("file_sha256") != source_hash:
                raise ValueError("Snapshot manifest does not match the bound source")
            return {
                "cutoff_exclusive": datetime.fromisoformat(cutoff).isoformat(),
                "origin": "source-hash-matched acceptance manifest",
            }
    return {}


def build_judge_context(store, case_id: str, *, manifest_root: Path | None = None) -> dict:
    """Profile the actual bound store, retaining uncertainty for unqualified sources.

    Only schema and aggregate source facts are included. No sample rows, oracle SQL,
    expected answers, planted changes or reference values leave the evaluator.
    """
    context = {
        "version": context_version(),
        "store": getattr(store, "id", None),
        "tables": [],
        "snapshot": {"status": "unknown", "scope": "No validated observation cutoff."},
        "limits": "Observed key counts do not establish business semantics or require a join.",
    }
    if store is None:
        return context
    tables = store.list_tables()
    declaration = {}
    if isinstance(store, SQLiteStore):
        with store.path.open("rb") as stream:
            context["source_sha256"] = hashlib.file_digest(stream, "sha256").hexdigest()
        declaration = _declaration(
            store,
            case_id,
            context["source_sha256"],
            manifest_root or repo_root() / "benchmarks/acceptance/acceptance-v1",
        )
    observed = []
    for table in tables:
        profile = {
            "name": table.name,
            "row_count": table.row_count,
            "columns": [{"name": c.name, "type": c.type} for c in table.columns],
            "key_counts": {},
        }
        if isinstance(store, SQLiteStore):
            for column in table.columns:
                key, name = column.name, _quoted(column.name)
                if key == "id" or key.endswith("_id"):
                    row = store.query(
                        f"SELECT COUNT({name}), COUNT(DISTINCT {name}) FROM {_quoted(table.name)}"
                    ).rows[0]
                    profile["key_counts"][key] = {"non_null": row[0], "distinct": row[1]}
                if declaration and key in OBSERVATIONS.get(table.name, ()):
                    # ISO cutoff originates in evaluator metadata, normalized above.
                    cutoff = declaration["cutoff_exclusive"]
                    row = store.query(
                        f"SELECT MIN({name}), MAX({name}), COUNT({name}), "
                        f"COALESCE(SUM({name} IS NOT NULL AND julianday({name}) IS NULL),0), "
                        f"COALESCE(SUM(julianday({name}) >= julianday('{cutoff}')),0) "
                        f"FROM {_quoted(table.name)}"
                    ).rows[0]
                    observed.append(
                        {
                            "table": table.name,
                            "column": key,
                            "min": row[0],
                            "max": row[1],
                            "non_null": row[2],
                            "nulls": table.row_count - row[2],
                            "invalid_timestamps": row[3],
                            "at_or_after_cutoff": row[4],
                        }
                    )
        context["tables"].append(profile)
    if declaration:
        purchase = [c for c in observed if c["column"] in ("purchased_at", "order_purchase_timestamp")]
        verified = (
            bool(purchase)
            and not any(c["nulls"] for c in purchase)
            and not any(c["invalid_timestamps"] or c["at_or_after_cutoff"] for c in observed)
        )
        context["snapshot"] = {
            **declaration,
            "status": "verified" if verified else "not_verified",
            "observations": observed,
            "scope": (
                "Only the listed observation columns; "
                "estimated future dates are predictions, not observations."
            ),
        }
    context["payload_sha256"] = hashlib.sha256(json.dumps(context, sort_keys=True).encode()).hexdigest()
    return context
