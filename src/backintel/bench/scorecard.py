"""Aggregate run records into a scorecard (Markdown and JSON) by dataset, store, model and level."""

from __future__ import annotations

import json
import statistics
from collections import defaultdict
from pathlib import Path

from backintel.settings import repo_root

RAW_DIR = repo_root() / "results" / "raw"
OUT_DIR = repo_root() / "results"
SCORE_KEYS = [
    "correct",
    "evidence_reproduces",
    "abstention_correct",
    "judge_method",
    "fully_supported",
]


def load_records(raw_dir: Path = RAW_DIR, *, experiments: list[str] | None = None) -> list[dict]:
    records = []
    for path in sorted(raw_dir.glob("*.jsonl")):
        if experiments and path.stem not in experiments:
            continue
        for line in path.read_text().splitlines():
            if line.strip():
                record = json.loads(line)
                record["experiment"] = path.stem
                records.append(record)
    return records


def _mean(values: list) -> float | None:
    values = [v for v in values if v is not None]
    return round(statistics.fmean(values), 3) if values else None


def aggregate(records: list[dict]) -> list[dict]:
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for record in records:
        groups[
            (
                record["experiment"],
                record["dataset"],
                record["store"],
                record["model"],
                record["level"],
            )
        ].append(record)
    rows = []
    for (experiment, dataset, store, model, level), items in sorted(groups.items()):
        metrics = [r["outputs"].get("metrics", {}) for r in items]
        row = {
            "recorded_at": max(r["recorded_at"] for r in items),
            "experiment": experiment,
            "dataset": dataset,
            "store": store,
            "model": model,
            "level": level,
            "n": len(items),
        }
        for key in SCORE_KEYS:
            row[key] = _mean([r["scores"].get(key) for r in items])
        row["errors"] = sum(1 for r in items if r["outputs"].get("error"))
        row["median_latency_s"] = (
            round(statistics.median([m.get("latency_s", 0) for m in metrics]), 1) if metrics else None
        )
        row["total_cost_usd"] = round(sum(m.get("cost_usd") or 0 for m in metrics), 4)
        row["incomplete_cost_runs"] = sum(m.get("cost_complete") is False for m in metrics)
        row["mean_tool_calls"] = _mean([m.get("tool_calls") for m in metrics])
        row["mean_tokens"] = _mean(
            [(m.get("input_tokens") or 0) + (m.get("output_tokens") or 0) for m in metrics]
        )
        rows.append(row)
    return rows


def failures(records: list[dict]) -> list[dict]:
    out = []
    for record in records:
        if record["scores"].get("fully_supported") != 1.0:
            error = record["outputs"].get("error") or ""
            kind = (
                "infrastructure"
                if any(
                    s in error.lower()
                    for s in ("credits", "payment_required", "provider_unavailable", "api_key")
                )
                else "agent execution limit"
                if "GraphRecursionError" in error
                else "historical harness error"
                if error
                else "answer/format"
                if record["scores"].get("correct") != 1
                else "evidence"
            )
            out.append(
                {
                    "kind": kind,
                    "experiment": record["experiment"],
                    "scenario_id": record["scenario_id"],
                    "level": record["level"],
                    "error": record["outputs"].get("error"),
                    "correct": record["comments"].get("correct"),
                    "evidence": record["comments"].get("evidence_reproduces"),
                    "abstention": record["comments"].get("abstention_correct"),
                }
            )
    return out


def coverage(rows: list[dict]) -> list[dict]:
    """Latest experiment per (dataset, store kind, level): the store-by-level matrix the goal asks for."""
    latest: dict[tuple, dict] = {}
    for row in rows:
        kind = row["store"].split(":")[0]
        key = (row["dataset"], kind, row["level"])
        # A later smoke run must not replace a complete level with fewer questions.
        if key not in latest or (row["n"], row["recorded_at"]) > (
            latest[key]["n"],
            latest[key]["recorded_at"],
        ):
            latest[key] = row
    return [latest[key] for key in sorted(latest)]


def render_markdown(rows: list[dict], fails: list[dict], records: list[dict]) -> str:
    def pct(value):
        return "–" if value is None else f"{100 * value:.0f}%"

    matrix = coverage(rows)
    lines = [
        "# BackIntel v2 scorecard",
        "",
        "## Coverage: largest observed cohort per dataset, store and level",
        "",
        "Levels: 1 single table, 2 joins/multi-step, 3 messy data, 4 cross-store, 5 standing problems, "
        "6 ambient replay with planted changes, 7 scale. Stores named `multi:` connect two stores at once.",
        "For each level the largest observed cohort is used, then the latest such experiment. "
        "Subset probes stay in the experiment list. Legacy and revised judges have different versions; "
        "their method scores are not directly comparable. Cost is provider-reported analyst cost only; "
        "JSON also records runs with incomplete cost telemetry. Subset probes are not full suites.",
        "",
        "| dataset | store | level | n | fully supported | correct | evidence | judge | median s | cost USD |",  # noqa: E501
        "|---|---|---|---|---|---|---|---|---|---|",
        *[
            f"| {r['dataset']} | {r['store'].split(':')[0]} | {r['level']} | {r['n']} | "
            f"{pct(r['fully_supported'])} | "
            f"{pct(r['correct'])} | {pct(r['evidence_reproduces'])} | "
            f"{r['judge_method'] if r['judge_method'] is not None else '–'} | {r['median_latency_s']} | "
            f"{r['total_cost_usd']:.4f} |"
            for r in matrix
        ],
        "",
        "## All experiments",
        "",
        "Scores are means over scenarios. `correct` compares the answer with the independently computed "
        "reference within tolerance; `evidence` re-executes the cited queries and checks they produce the "
        "answered value; `abstention` checks the agent answered when it could and declined when it could "
        "not; `judge` is an LLM rubric on method and caveats (0–1); `fully supported` requires correct + "
        "evidence + abstention.",
        "",
        "| experiment | level | n | correct | evidence | abstention | judge | fully supported | errors "
        "| median s | cost USD | tool calls |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r['experiment']} | {r['level']} | {r['n']} | {pct(r['correct'])} | "
            f"{pct(r['evidence_reproduces'])} | {pct(r['abstention_correct'])} | "
            f"{r['judge_method'] if r['judge_method'] is not None else '–'} | "
            f"{pct(r['fully_supported'])} | {r['errors']} | {r['median_latency_s']} | "
            f"{r['total_cost_usd']:.4f} | {r['mean_tool_calls']} |"
        )
    meta = {}
    for record in records:
        meta.setdefault(
            record["experiment"],
            {
                k: record.get(k)
                for k in (
                    "dataset",
                    "store",
                    "model",
                    "judge_model",
                    "method_version",
                    "source_version",
                    "reference_version",
                    "judge_version",
                    "sandbox",
                    "git_sha",
                )
            },
        )
    lines += ["", "## Experiments", ""]
    for name, info in meta.items():
        lines.append(f"- **{name}**: " + ", ".join(f"{k}={v}" for k, v in info.items()))
    lines += ["", f"## Failures and partial results ({len(fails)})", ""]
    for f in fails:
        reason = f["error"] or f["correct"] or ""
        lines.append(
            f"- `{f['scenario_id']}` (L{f['level']}, {f['experiment']}; {f['kind']}): {reason[:160]}"
            + (
                f" | evidence: {f['evidence'][:120]}"
                if f["evidence"] and "found in" in (f["evidence"] or "") and "not found" in f["evidence"]
                else ""
            )
        )
    return "\n".join(lines) + "\n"


def build_scorecard(
    raw_dir: Path = RAW_DIR, out_dir: Path = OUT_DIR, *, experiments: list[str] | None = None
) -> Path:
    records = load_records(raw_dir, experiments=experiments)
    rows = aggregate(records)
    fails = failures(records)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "scorecard.json").write_text(json.dumps({"rows": rows, "failures": fails}, indent=2) + "\n")
    path = out_dir / "scorecard.md"
    path.write_text(render_markdown(rows, fails, records))
    return path
