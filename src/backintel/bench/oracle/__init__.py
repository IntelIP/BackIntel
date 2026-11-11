"""Reference answers, computed independently of any store with polars over the canonical data.

Each dataset module declares `SCENARIOS`: (Scenario fields, compute function). `build_answers`
runs every compute function and writes `benchmarks/answers/<dataset>.json`. The agent never
reads these files: it only sees the store through its tools.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import polars as pl

from backintel.bench.datasets import load_canonical, sha256_file
from backintel.contracts import Scenario, Tolerance
from backintel.settings import Settings, repo_root

Frames = dict[str, pl.DataFrame]
ANSWERS_DIR = repo_root() / "benchmarks" / "answers"

EXACT = Tolerance(abs=0)
MONEY = Tolerance(rel=0.002)
RATIO = Tolerance(rel=0.005)


@dataclass
class Spec:
    id: str
    level: int
    question: str
    answer_type: str
    compute: Callable[[Frames], Any] | None
    tolerance: Tolerance = field(default_factory=lambda: Tolerance(rel=0.005))
    unit: str | None = None
    tags: list[str] = field(default_factory=list)
    notes: str | None = None
    store: str | None = None

    @property
    def answerable(self) -> bool:
        return self.compute is not None


def _scalar(frame: pl.DataFrame) -> Any:
    value = frame.item()
    return float(value) if isinstance(value, (int, float)) else value


def build_answers(dataset: str, settings: Settings, *, out_dir: Path = ANSWERS_DIR) -> list[Scenario]:
    if dataset == "online_retail_ii":
        from backintel.bench.oracle import online_retail_ii as module
    elif dataset == "olist":
        from backintel.bench.oracle import olist as module
    elif dataset.startswith("tpch_sf"):
        from backintel.bench.oracle import tpch as module
    else:
        raise ValueError(f"No oracle for dataset {dataset!r}.")
    if dataset.startswith("tpch_sf"):
        frames = {
            p.stem: pl.scan_parquet(p) for p in sorted((settings.canonical_dir / dataset).glob("*.parquet"))
        }
    else:
        frames = load_canonical(dataset, settings)
    scenarios = []
    for spec in module.SCENARIOS:
        expected = spec.compute(frames) if spec.compute else None
        if isinstance(expected, pl.DataFrame):
            expected = expected.to_dicts()
        scenarios.append(
            Scenario(
                id=spec.id,
                dataset=dataset,
                level=spec.level,
                question=(
                    spec.question
                    + " Use these metric identifiers in rows: "
                    + ", ".join(f["name"] for f in expected)
                    + "."
                    if spec.answer_type == "report" and "planted-change" not in spec.tags
                    else spec.question
                ),
                answer_type=spec.answer_type,
                expected=expected,
                tolerance=spec.tolerance,
                unit=spec.unit,
                answerable=spec.compute is not None,
                tags=spec.tags,
                notes=spec.notes,
                store=spec.store,
            )
        )
    manifest = json.loads((settings.canonical_dir / dataset / "MANIFEST.json").read_text())
    out_dir.mkdir(parents=True, exist_ok=True)
    planted = []
    if dataset == "olist":
        from backintel.bench.replay import MATERIAL_CHANGE, MIN_ORDERS, PERIODS, PLANTED

        planted = [
            {
                "periods": PERIODS,
                "min_orders": MIN_ORDERS,
                "material_change": MATERIAL_CHANGE,
                "changes": PLANTED,
            }
        ]
    payload = {
        "dataset": dataset,
        "archive_sha256": manifest["archive_sha256"],
        "planted_changes": planted,
        "built_at": datetime.now(UTC).isoformat(),
        "oracle": "polars over canonical parquet",
        "scenarios": [s.model_dump() for s in scenarios],
    }
    (out_dir / f"{dataset}.json").write_text(json.dumps(payload, indent=2, default=str) + "\n")
    return scenarios


def load_answers(dataset: str, *, answers_dir: Path = ANSWERS_DIR) -> list[Scenario]:
    payload = json.loads((answers_dir / f"{dataset}.json").read_text())
    return [Scenario.model_validate(item) for item in payload["scenarios"]]


__all__ = [
    "EXACT",
    "MONEY",
    "RATIO",
    "Frames",
    "Spec",
    "build_answers",
    "load_answers",
    "sha256_file",
    "_scalar",
]
