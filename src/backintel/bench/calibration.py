"""Blind human review packets; missing labels remain missing, never inferred."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from backintel.bench.judge import DECLINED_RUBRIC, RUBRIC


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def write_review_packet(records: list[dict], out_dir: Path) -> dict:
    """Publish answers separately from model ratings, with blank owner-label fields."""
    out_dir.mkdir(parents=True, exist_ok=False)
    cases, judges = [], {}
    for index, record in enumerate(records):
        answer = (record.get("outputs") or {}).get("answer")
        if answer is None:
            continue
        case_id = f"review-{index + 1:02d}"
        criteria = DECLINED_RUBRIC if answer["status"] == "cannot_answer" else RUBRIC
        case = {
            "id": case_id,
            "question": record["question"],
            "answer": answer,
            "criteria": criteria,
            "source_kind": record.get("source_kind", "recorded_agent_response"),
            "source_run_id": record.get("langsmith_run_id"),
            "scenario_id": record.get("scenario_id"),
            "source_digest": digest(record),
        }
        cases.append(case)
        judges[case_id] = {
            "judge_version": record.get("judge_version"),
            "score": record.get("scores", {}).get("judge_method"),
            "criteria": record.get("judge_criteria", {}),
            "comment": record.get("comments", {}).get("judge_method"),
        }
        # Existing raw records retain normalized per-criterion ratings at the end of comments.
        if not judges[case_id]["criteria"] and judges[case_id]["comment"]:
            comment = judges[case_id]["comment"]
            start = comment.rfind("{")
            if start >= 0:
                try:
                    candidate = json.loads(comment[start:])
                    if set(candidate) == set(criteria):
                        judges[case_id]["criteria"] = candidate
                except json.JSONDecodeError:
                    pass
    if not cases:
        raise ValueError("No structured answers available for human method review")
    packet = {"schema": 1, "cases": cases}
    packet["packet_hash"] = digest(packet)
    labels = {
        "packet_hash": packet["packet_hash"],
        "reviewer": None,
        "reviewer_type": "human",
        "reviewed_at": None,
        "cases": {c["id"]: {"ratings": dict.fromkeys(c["criteria"]), "comment": None} for c in cases},
    }
    for name, value in (
        ("packet.json", packet),
        ("human-labels.json", labels),
        ("judge-ratings.json", judges),
    ):
        (out_dir / name).write_text(json.dumps(value, indent=2, default=str) + "\n")
    lines = [
        "# BackIntel human explanation review",
        "",
        "Rate each criterion: **0 = fails/contradicts; 1 = partially supported or uncertain; "
        "2 = clearly satisfies**. Numerical reference matching is checked separately. "
        "Read the question, response and cited calculation; model grades are withheld.",
        "",
        "Reply in chat using `review-01: 2, 2, 2, 1 — your comment`, with ratings in each "
        "table's order. You can mark a case `unsure` and explain why. Alternatively fill "
        "human-labels.json and add your name and review timestamp. Blank means unreviewed.",
        "",
    ]
    for case in cases:
        answer = case["answer"]
        lines += [
            f"## {case['id']}",
            "",
            f"Source: {case['source_kind']}.",
            "",
            case["question"],
            "",
            f"**Status:** {answer['status']}",
            "",
        ]
        if answer.get("rows"):
            columns = list(dict.fromkeys(k for row in answer["rows"] for k in row))
            lines += ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
            lines += [
                "| " + " | ".join(str(row.get(k, "")).replace("|", "\\|") for k in columns) + " |"
                for row in answer["rows"]
            ]
            lines += [""]
        else:
            for key in ("value", "text", "items", "unit"):
                if answer.get(key) is not None:
                    lines += [f"**{key.capitalize()}:** {answer[key]}", ""]
        for key in ("method", "reason"):
            if answer.get(key):
                lines += [f"**{key.capitalize()}:** {answer[key]}", ""]
        if answer.get("caveats"):
            lines += ["**Caveats:**", "", *[f"- {v}" for v in answer["caveats"]], ""]
        for index, evidence in enumerate(answer.get("evidence", []), 1):
            lines += [
                "<details>",
                f"<summary>Evidence {index}: {evidence['kind']}</summary>",
                "",
                "```"
                + (
                    "sql"
                    if evidence["kind"] == "sql"
                    else "python"
                    if evidence["kind"] == "python"
                    else "json"
                ),
                evidence["code"],
                "```",
                "",
                evidence.get("note") or "",
                "",
                "</details>",
                "",
            ]
        lines += ["| Criterion, in rating order | What to assess | Your rating |", "| --- | --- | --- |"]
        lines += [f"| {key} | {text} | |" for key, text in case["criteria"].items()]
        lines += [""]
    (out_dir / "review.md").write_text("\n".join(lines))
    return {
        "cases": len(cases),
        "packet_hash": packet["packet_hash"],
        "review_path": str(out_dir / "review.md"),
    }


def assess_calibration(packet: dict, labels: dict, judges: dict) -> dict:
    """Report agreement and material disagreements; do not manufacture an approval verdict."""
    unsigned = {k: v for k, v in packet.items() if k != "packet_hash"}
    if digest(unsigned) != packet["packet_hash"] or labels.get("packet_hash") != packet["packet_hash"]:
        raise ValueError("Review packet changed or labels belong to another packet")
    if labels.get("reviewer_type") != "human":
        raise ValueError("Agent labels cannot be reported as human calibration")
    reviewed, missing, disagreements = [], [], []
    if set(labels.get("cases", {})) != {c["id"] for c in packet["cases"]}:
        raise ValueError("Human label case IDs differ from the packet")
    for case in packet["cases"]:
        ratings = labels["cases"][case["id"]]["ratings"]
        if set(ratings) != set(case["criteria"]):
            raise ValueError("Human criteria differ from the packet")
        for key, value in ratings.items():
            model = judges.get(case["id"], {}).get("criteria", {}).get(key)
            if value is None or model is None:
                missing.append({"case": case["id"], "criterion": key, "human": value, "judge": model})
                continue
            if type(value) is not int or value not in (0, 1, 2):
                raise ValueError("Human ratings must be integer 0, 1, 2 or null")
            if model not in (0, 0.5, 1):
                raise ValueError("Judge ratings must be normalized anchored 0/1/2 ratings")
            pair = {"case": case["id"], "criterion": key, "human": value, "judge": int(model * 2)}
            reviewed.append(pair)
            if pair["human"] != pair["judge"]:
                disagreements.append(pair)
    identified = bool(labels.get("reviewer") and labels.get("reviewed_at"))
    return {
        "packet_hash": packet["packet_hash"],
        "status": "reviewed" if reviewed and not missing and identified else "awaiting_human_review",
        "reviewer": labels.get("reviewer"),
        "reviewed_at": labels.get("reviewed_at"),
        "rated_criteria": len(reviewed),
        "exact_agreement": 1 - len(disagreements) / len(reviewed) if reviewed else None,
        "mean_absolute_rating_difference": (
            sum(abs(p["human"] - p["judge"]) for p in reviewed) / len(reviewed) if reviewed else None
        ),
        "disagreements": disagreements,
        "missing": missing,
        "interpretation": (
            "Descriptive agreement on this packet; no statistical reliability or owner approval inferred"
        ),
    }
