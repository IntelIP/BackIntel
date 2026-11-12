"""The analyst's answer contract and the benchmark scenario contract.

The answer is a box: every number must be traceable to the evidence the agent cites, and
code (not the model) re-executes that evidence to check it. Scenarios carry the expected
answer and tolerance; the agent never sees them.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

AnswerType = Literal["number", "text", "ranked_list", "table", "report"]
Cell = str | float | int | bool | None


class Evidence(BaseModel):
    """One query or program whose output the answer rests on, exactly as executed."""

    model_config = ConfigDict(extra="forbid")
    kind: Literal["sql", "python", "query"]
    code: str = Field(min_length=1, description="The exact SQL or Python that produced the result")
    store: str | None = Field(
        default=None, description="For SQL when several stores are connected: the store id it ran on"
    )
    note: str | None = Field(default=None, description="What this evidence establishes")


class AnalystAnswer(BaseModel):
    """What the analyst returns for one question.

    Set `status` to `cannot_answer` when the data lacks what the question needs; then give
    `reason`. Fill exactly the value field that matches `answer_type`: `value` for a number,
    `text` for a name or label, `items` for a ranked list (best first), `rows` for a table. For a
    standing problem that asks for several metrics (`report`), give one row per metric in `rows`
    with keys `metric`, `value` and `unit`, and put the story the numbers tell in `method`.
    """

    model_config = ConfigDict(extra="forbid")
    status: Literal["answered", "cannot_answer"]
    answer_type: AnswerType | None = None
    value: float | None = Field(default=None, description="Numeric answer, unrounded")
    text: str | None = Field(default=None, description="Text answer, e.g. a country name")
    items: list[str] | None = Field(default=None, description="Ranked list, best first")
    rows: list[dict[str, Cell]] | None = Field(default=None, description="Table answer")
    unit: str | None = Field(default=None, description="Unit of the number, e.g. GBP or orders")
    method: str = Field(description="How the answer was computed: filters, cleaning rules, joins, formulas")
    evidence: list[Evidence] = Field(
        default_factory=list,
        description="The exact queries/programs that produce the answer; at least one if answered",
    )
    caveats: list[str] = Field(
        default_factory=list, description="Data limitations that affect how to read the answer"
    )
    reason: str | None = Field(default=None, description="Why the question cannot be answered")


class Tolerance(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rel: float | None = None  # relative tolerance, e.g. 0.005 for 0.5 percent
    abs: float | None = None  # absolute tolerance, e.g. 0 for exact counts


class Scenario(BaseModel):
    """One benchmark question with its reference answer (never shown to the agent)."""

    model_config = ConfigDict(extra="forbid")
    id: str
    dataset: str
    level: int = Field(ge=1, le=7)
    question: str
    answer_type: AnswerType
    expected: float | str | list[str] | list[dict[str, Cell]] | None
    tolerance: Tolerance = Field(default_factory=lambda: Tolerance(rel=0.005))
    unit: str | None = None
    answerable: bool = True
    tags: list[str] = Field(default_factory=list)
    notes: str | None = None  # what this scenario tests; for reviewers
    store: str | None = None  # store id this scenario must run on (replay snapshots); else the run's store
