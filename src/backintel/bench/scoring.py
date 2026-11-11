"""Deterministic scoring of an analyst answer against a scenario, plus evidence re-execution.

`score_correct` compares the answer with the reference within the scenario's tolerance.
`evidence_reproduces` re-runs the cited queries/programs read-only and checks that the answered
value appears in their output. `abstention_correct` checks that the agent answered when it
could and declined when it could not. None of this involves a model.
"""

from __future__ import annotations

import math
import re
from typing import Any

from backintel.contracts import AnalystAnswer, Cell, Scenario, Tolerance
from backintel.sandbox import PythonSandbox
from backintel.stores.base import QueryRefused, Store

NUMBER = re.compile(r"-?\d+(?:[.,]\d+)?")
RANK_LIKE = re.compile(r"^(rank|row|#|index|position|n)$", re.I)


def normalize_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value)).strip().casefold()


def within(actual: float, expected: float, tolerance: Tolerance) -> bool:
    if actual is None or expected is None or math.isnan(actual):
        return False
    if tolerance.abs is not None and abs(actual - expected) <= tolerance.abs + 1e-9:
        return True
    if tolerance.rel is not None:
        scale = max(abs(expected), 1e-12)
        return abs(actual - expected) / scale <= tolerance.rel
    return False


def to_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        match = NUMBER.search(value.replace(",", ""))
        if match:
            try:
                return float(match.group())
            except ValueError:
                return None
    return None


def item_label(item: str) -> str:
    """The label part of an annotated ranked item: 'SP — 41,746 rows' -> 'SP'."""
    return re.split(r"\s+[—–-]\s+|\s*[:(]", item, maxsplit=1)[0].strip()


def item_matches(got: str, expected: str) -> bool:
    """An answered item equals the expected label or starts with it followed by an annotation."""
    return got == expected or re.match(rf"^{re.escape(expected)}\b\s*[^a-z0-9]", got) is not None


def ranked_items(answer: AnalystAnswer) -> tuple[list[str], str | None]:
    """The ranked list, taken from `items`, else the first text column of `rows`, else `text`."""
    if answer.items:
        return [str(x) for x in answer.items], None
    if answer.rows:
        for column in answer.rows[0]:
            if isinstance(answer.rows[0][column], str):
                return [str(row.get(column)) for row in answer.rows], "rows"
    if answer.text:
        parts = [p.strip(" .") for p in re.split(r",|;|\n|\d+\.\s", answer.text) if p.strip(" .")]
        return parts, "text"
    return [], None


def _answer_number(answer: AnalystAnswer) -> float | None:
    if answer.value is not None:
        return float(answer.value)
    if answer.text:
        return to_number(answer.text)
    if answer.rows and len(answer.rows) == 1 and len(answer.rows[0]) == 1:
        return to_number(next(iter(answer.rows[0].values())))
    return None


def _match_table(
    expected: list[dict[str, Cell]], rows: list[dict[str, Cell]] | None, tolerance: Tolerance
) -> tuple[float, str]:
    if not rows:
        return 0.0, "no rows returned"
    keys = [k for k, v in expected[0].items() if isinstance(v, str)]
    numeric = [k for k, v in expected[0].items() if not isinstance(v, str)]

    def norm_keys(row: dict) -> tuple:
        return tuple(normalize_text(row.get(k)) for k in keys)

    # Column names may differ: map by position when names do not match.
    def lookup(row: dict, column: str, index: int) -> Any:
        if column in row:
            return row[column]
        lowered = {normalize_text(k): v for k, v in row.items()}
        if normalize_text(column) in lowered:
            return lowered[normalize_text(column)]
        values = list(row.values())
        return values[index] if index < len(values) else None

    expected_columns = list(expected[0].keys())
    matched = 0
    for exp_row in expected:
        target = tuple(normalize_text(exp_row[k]) for k in keys)
        candidates = (
            [
                r
                for r in rows
                if tuple(normalize_text(lookup(r, k, expected_columns.index(k))) for k in keys) == target
            ]
            if keys
            else rows
        )
        ok = False
        for cand in candidates:
            ok = all(
                within(
                    (
                        number
                        if (number := to_number(lookup(cand, col, expected_columns.index(col)))) is not None
                        else float("nan")
                    ),
                    float(exp_row[col]),
                    tolerance,
                )
                for col in numeric
            )
            if ok:
                break
        matched += ok
    fraction = matched / len(expected)
    extra = len(rows) - len(expected)
    comment = f"{matched}/{len(expected)} expected rows matched" + (
        f"; {extra} extra rows" if extra > 0 else ""
    )
    return fraction, comment


def score_correct(scenario: Scenario, answer: AnalystAnswer | None) -> dict:
    """Return {"correct": 0/1, "partial": 0..1, "comment": str}."""
    if answer is None:
        return {"correct": 0.0, "partial": 0.0, "comment": "no structured answer produced"}
    if not scenario.answerable:
        ok = answer.status == "cannot_answer"
        return {
            "correct": float(ok),
            "partial": float(ok),
            "comment": "declined correctly"
            if ok
            else f"answered an unanswerable question: {answer.value or answer.text}",
        }
    if answer.status != "answered":
        return {
            "correct": 0.0,
            "partial": 0.0,
            "comment": f"declined an answerable question: {answer.reason}",
        }
    kind = scenario.answer_type
    if kind == "number":
        actual = _answer_number(answer)
        ok = actual is not None and within(actual, float(scenario.expected), scenario.tolerance)
        return {
            "correct": float(ok),
            "partial": float(ok),
            "comment": f"answered {actual}, expected {scenario.expected} "
            f"(tol {scenario.tolerance.model_dump(exclude_none=True)})",
        }
    if kind == "text":
        got = answer.text or (answer.items[0] if answer.items else None) or ""
        exp = normalize_text(scenario.expected)
        ok = normalize_text(got) == exp or (
            len(exp) > 3 and re.search(rf"\b{re.escape(exp)}\b", normalize_text(got)) is not None
        )
        return {
            "correct": float(ok),
            "partial": float(ok),
            "comment": f"answered {got!r}, expected {scenario.expected!r}",
        }
    if kind == "ranked_list":
        items, derived = ranked_items(answer)
        got = [normalize_text(x) for x in items]
        exp = [normalize_text(x) for x in scenario.expected]
        exact = len(got) == len(exp) and all(item_matches(g, e) for g, e in zip(got, exp, strict=True))
        overlap = (
            sum(any(item_matches(g, e) for g in got[: len(exp)]) for e in exp) / len(exp) if exp else 0.0
        )
        return {
            "correct": float(exact),
            "partial": overlap if not exact else 1.0,
            "comment": f"answered {items}{' (derived from ' + derived + ')' if derived else ''}, "
            f"expected {scenario.expected}",
        }
    if kind == "table":
        fraction, comment = _match_table(scenario.expected, answer.rows, scenario.tolerance)
        return {
            "correct": float(fraction == 1.0 and len(answer.rows or []) == len(scenario.expected)),
            "partial": fraction,
            "comment": comment,
        }
    if kind == "report":
        found, missing = report_facts_found(scenario.expected, answer)
        recall = len(found) / len(scenario.expected)
        names = [normalize_text(row.get("metric", "")) for row in answer.rows or []]
        expected_names = {normalize_text(f["name"]) for f in scenario.expected}
        exact = len(names) == len(expected_names) and set(names) == expected_names
        comment = f"{len(found)}/{len(scenario.expected)} facts present"
        if missing:
            comment += "; missing: " + ", ".join(missing)
        if not exact:
            comment += "; missing, duplicate or unexpected metric identifiers"
        return {"correct": float(recall == 1.0 and exact), "partial": recall, "comment": comment}
    raise ValueError(f"Unknown answer type {kind}")


def answer_cells(answer: AnalystAnswer) -> list[Any]:
    """Every value the answer states, from rows, value, text and items."""
    cells: list[Any] = []
    for row in answer.rows or []:
        cells.extend(row.values())
    if answer.value is not None:
        cells.append(answer.value)
    if answer.text:
        cells.append(answer.text)
    cells.extend(answer.items or [])
    return cells


def report_facts_found(facts: list[dict], answer: AnalystAnswer) -> tuple[list[dict], list[str]]:
    """Which expected facts appear in the answer (numbers within tolerance, text by containment)."""
    found, missing = [], []
    for fact in facts:
        # A correct number attached to the wrong metric is a wrong finding.
        cells = [
            row.get("value")
            for row in answer.rows or []
            if normalize_text(row.get("metric", "")) == normalize_text(fact["name"])
        ]
        if isinstance(fact["value"], str):
            target = normalize_text(fact["value"])
            ok = any(
                isinstance(c, str)
                and (normalize_text(c) == target if len(target) <= 3 else target in normalize_text(c))
                for c in cells
            )
        else:
            # Numbers may sit in numeric cells or inside a text cell ("April average 11.12 days").
            tolerance = Tolerance(rel=fact.get("rel"), abs=fact.get("abs"))
            numbers = [float(c) for c in cells if isinstance(c, (int, float)) and not isinstance(c, bool)]
            for c in cells:
                if isinstance(c, str):
                    numbers.extend(float(m.replace(",", "")) for m in NUMBER.findall(c))
            ok = any(within(n, float(fact["value"]), tolerance) for n in numbers)
        (found if ok else missing).append(fact if ok else fact["name"])
    return found, missing


def replay_status(answer: AnalystAnswer) -> str | None:
    """The replay's declared 25% rule is derivable from its reproduced per-state changes.

    Printing False for every material-change test and reporting NO_CHANGE is a valid
    alternative to printing that literal label; the values still need to reproduce.
    """
    changes = [
        to_number(row.get("value"))
        for row in answer.rows or []
        if str(row.get("metric", "")).startswith("relative_change_")
    ]
    if not changes or any(value is None for value in changes):
        return None
    return "CHANGE_DETECTED" if any(abs(value) > 0.25 for value in changes) else "NO_CHANGE"


def abstention_correct(scenario: Scenario, answer: AnalystAnswer | None) -> dict:
    if answer is None:
        return {"score": 0.0, "comment": "no structured answer"}
    expected = "answered" if scenario.answerable else "cannot_answer"
    ok = answer.status == expected
    return {"score": float(ok), "comment": f"status {answer.status}, expected {expected}"}


def _cells_from_sql(store: Store, code: str, target: str | None = None) -> tuple[list[Any], str | None]:
    from backintel.stores.multi import DIRECTIVE, MultiStore

    if isinstance(store, MultiStore) and not DIRECTIVE.match(code):
        if target is None:
            return [], "evidence names no store, so it could not be re-executed"
        code = f"-- store: {target}\n{code}"
    try:
        result = store.query(code, max_rows=5000)
    except (QueryRefused, NotImplementedError) as error:
        return [], f"query failed on re-execution: {error}"
    return [cell for row in result.rows for cell in row], None


def _cells_from_python(sandbox: PythonSandbox, store: Store, code: str) -> tuple[list[Any], str | None]:
    result = sandbox.run(
        code, env=store.python_environment(), mounts=store.python_mounts(), network=store.sandbox_network()
    )
    if result.exit_code != 0:
        return [], f"program failed on re-execution: {result.stderr[-300:]}"
    text = result.stdout
    numbers = [float(m.replace(",", "")) for m in NUMBER.findall(text)]
    tokens = [t for t in re.split(r"[\s,;|\[\]()'\"]+", text) if t]
    return [*numbers, *tokens, text], None


def evidence_reproduces(
    scenario: Scenario, answer: AnalystAnswer | None, store: Store, sandbox: PythonSandbox
) -> dict:
    """Does re-running the cited evidence yield the answered value? Not applicable when declined."""
    if answer is None:
        return {"score": 0.0, "comment": "no structured answer"}
    if answer.status != "answered":
        return {"score": None, "comment": "not applicable: question declined"}
    if not answer.evidence:
        return {"score": 0.0, "comment": "no evidence cited"}
    cells: list[Any] = []
    problems = []
    for item in answer.evidence:
        got, problem = (
            _cells_from_sql(store, item.code, item.store)
            if item.kind in ("sql", "query")
            else _cells_from_python(sandbox, store, item.code)
        )
        cells.extend(got)
        if problem:
            problems.append(problem)
    tight = Tolerance(rel=1e-4, abs=0.011)  # the agent's own value, allowing display rounding

    def has_number(target: float) -> bool:
        return any((n := to_number(c)) is not None and within(n, target, tight) for c in cells)

    def has_text(target: str) -> bool:
        """The answered text equals, contains, or is contained in some output cell (3+ characters)."""
        norm = normalize_text(target)
        for c in cells:
            if not isinstance(c, str):
                continue
            cell = normalize_text(c)
            if cell == norm or norm in cell or (len(cell) >= 3 and cell in norm):
                return True
        return False

    # Verify what the benchmark asked for: a ranked list returned as a table is still a ranked list.
    kind = scenario.answer_type
    if kind == "report":
        values = [(row.get("metric"), row.get("value")) for row in answer.rows or []]
        derived = replay_status(answer) if "planted-change" in scenario.tags else None
        ok = bool(values) and all(
            (has_text(v) or (key == "status" and v == derived))
            if isinstance(v, str)
            else v is not None and has_number(float(v))
            for key, v in values
        )
    elif kind == "number":
        value = _answer_number(answer)
        ok = value is not None and has_number(value)
    elif kind == "text":
        ok = bool(answer.text) and has_text(answer.text)
    elif kind == "ranked_list":
        items, _ = ranked_items(answer)
        ok = bool(items) and all(has_text(x) or has_text(item_label(x)) for x in items)
    else:
        ok = bool(answer.rows) and all(
            (
                has_number(n)
                if (n := to_number(v)) is not None and not isinstance(v, str)
                else has_text(str(v))
            )
            for row in answer.rows
            for key, v in row.items()
            if v is not None and not RANK_LIKE.match(str(key))
        )
    found = "found" if ok else "not found"
    comment = f"{len(answer.evidence)} evidence item(s) re-executed; value {found} in output"
    if problems:
        comment += "; " + "; ".join(problems)
    return {"score": float(ok and not problems), "comment": comment}
