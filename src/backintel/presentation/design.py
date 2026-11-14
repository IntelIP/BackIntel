"""Presentation-only edits. The retained analytical tables and values are immutable."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)


class ChartDesign(StrictModel):
    chart: int = Field(ge=0)
    title: str = Field(min_length=1, max_length=120)
    caption: str = Field(max_length=350)
    reading_guide: str = Field(default="", max_length=250)
    # Bindings, values, units and populations cannot be changed by presentation edits.
    encoding: Literal["original", "column"] = "original"
    x_label: str = Field(min_length=1, max_length=80)
    y_label: str = Field(min_length=1, max_length=80)


class Section(StrictModel):
    title: str = Field(min_length=1, max_length=45)
    takeaway: str = Field(max_length=350)
    columns: Literal[1, 2] = 1
    charts: list[ChartDesign] = Field(min_length=1, max_length=6)


class BusinessContext(StrictModel):
    audience: str = Field(min_length=1, max_length=160)
    decision: str = Field(min_length=1, max_length=250)
    coverage: str = Field(min_length=1, max_length=350)
    limitation: str = Field(min_length=1, max_length=250)


class DesignPlan(StrictModel):
    title: str = Field(min_length=1, max_length=100)
    introduction: str = Field(max_length=350)
    context: BusinessContext | None = None
    sections: list[Section] = Field(min_length=1, max_length=6)


def validate_plan(value: dict, data: dict) -> DesignPlan:
    plan = DesignPlan.model_validate(value)
    names = [s.title.casefold() for s in plan.sections]
    if len(set(names)) != len(names) or {"explore", "about the data"} & set(names):
        raise ValueError("Section names must be unique and distinct from Explore and About the data.")
    indexes = [c.chart for s in plan.sections for c in s.charts]
    if sorted(indexes) != list(range(len(data["charts"]))):
        raise ValueError("Every retained chart must appear exactly once; charts cannot be silently dropped.")
    for section in plan.sections:
        for design in section.charts:
            original = data["charts"][design.chart]
            if design.encoding == "column" and original["kind"] not in {"bar", "line"}:
                raise ValueError("Only an existing bar/line comparison may become columns.")
    return plan


CRITERIA = ("story", "charts", "organization", "craft", "usefulness")


class Rating(StrictModel):
    criterion: Literal["story", "charts", "organization", "craft", "usefulness"]
    evidence: str = Field(min_length=1, max_length=1200)
    views: list[str] = Field(min_length=1)
    score: int = Field(ge=1, le=5)


class DesignReview(StrictModel):
    ratings: list[Rating] = Field(min_length=5, max_length=5)
    blocking_issues: list[Annotated[str, Field(min_length=1, max_length=1200)]] = Field(max_length=12)
    revisions: list[Annotated[str, Field(min_length=1, max_length=1200)]] = Field(max_length=8)

    def checked(self, view_names: set[str]) -> DesignReview:
        if sorted(r.criterion for r in self.ratings) != sorted(CRITERIA):
            raise ValueError("Review must grade each criterion exactly once.")
        if any(not set(r.views) <= view_names for r in self.ratings):
            raise ValueError("Review cited a screenshot that was not supplied.")
        if self.passed and {view for rating in self.ratings for view in rating.views} != view_names:
            raise ValueError("A passing review must cover every supplied screenshot.")
        if not self.passed and not (self.blocking_issues or self.revisions):
            raise ValueError("A failing review must provide actionable feedback.")
        return self

    @property
    def passed(self) -> bool:
        # Fixed host-owned threshold; the writer cannot lower it to pass.
        return not self.blocking_issues and all(r.score >= 4 for r in self.ratings)

    @property
    def quality(self) -> tuple:
        return (
            -len(self.blocking_issues),
            min(r.score for r in self.ratings),
            sum(r.score for r in self.ratings),
        )
