"""Business meaning for connected-source goals; no credentials or pipeline code."""
from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


Text = Annotated[str, Field(min_length=1, max_length=2000)]
SchemaName = Annotated[str, Field(pattern=r'^[A-Za-z_][A-Za-z0-9_]{0,62}$')]


class ObjectiveLimits(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)

    max_source_bytes: int = Field(gt=0, le=104857600)
    timeout_seconds: int = Field(gt=0, le=900)


class ObjectiveContract(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)

    source_ref: str = Field(pattern=r'^[a-z][a-z0-9_-]{0,63}$')
    expected_source_sha256: str | None = Field(default=None, pattern=r'^[0-9a-f]{64}$')
    allowed_schemas: list[SchemaName] = Field(min_length=1, max_length=20)
    allowed_actions: list[Literal['read']] = Field(default_factory=lambda: ['read'], min_length=1, max_length=1)
    metric: Text
    population: Text
    period: Text
    target: Text | None = None
    expected_checks: list[Text] = Field(min_length=1, max_length=20)
    freshness: Text
    output_destination: Literal['local'] = 'local'
    limits: ObjectiveLimits
    open_questions: list[Text] = Field(default_factory=list, max_length=20)


class PlanStep(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)

    purpose: Text
    action: Literal['discover', 'collect', 'prepare', 'check', 'analyze', 'report']
    expected_result: Text


class PlanProposal(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)

    summary: Text
    data_needs: list[Text] = Field(min_length=1, max_length=20)
    steps: list[PlanStep] = Field(min_length=1, max_length=12)
    assumptions: list[Text] = Field(max_length=20)
    open_questions: list[Text] = Field(max_length=20)


class DocumentCitation(BaseModel):
    model_config = ConfigDict(extra='forbid')
    document_id: str = Field(pattern=r'^[a-f0-9]{64}$')
    passage_id: str = Field(pattern=r'^[a-f0-9]{64}$')
    quote: str = Field(min_length=1, max_length=1600)


class FieldMeaning(BaseModel):
    model_config = ConfigDict(extra='forbid', json_schema_serialization_defaults_required=True)
    name: Text
    meaning: Text
    role: Literal['identifier', 'quantity', 'unit_price', 'measure', 'date', 'category', 'text', 'unknown']
    unit: Text | None
    date_format: Literal['month_first', 'day_first', 'iso'] | None
    basis: Literal['objective', 'observed_format', 'inferred_name', 'unresolved']
    confidence: Literal['supported', 'proposed', 'ambiguous']
    limitations: list[Text] = Field(max_length=10)
    citations: list[DocumentCitation] = Field(default_factory=list, max_length=4)


class TableMeaning(BaseModel):
    model_config = ConfigDict(extra='forbid')
    schema_name: Text
    table_name: Text
    grain: Text
    identity_columns: list[Text] = Field(min_length=1, max_length=10)
    fields: list[FieldMeaning] = Field(min_length=1, max_length=256)


class RelationshipMeaning(BaseModel):
    model_config = ConfigDict(extra='forbid')
    from_schema: Text
    from_table: Text
    from_column: Text
    to_schema: Text
    to_table: Text
    to_column: Text
    meaning: Text
    confidence: Literal['proposed', 'ambiguous']


class SemanticProposal(BaseModel):
    model_config = ConfigDict(extra='forbid')
    summary: Text
    tables: list[TableMeaning] = Field(min_length=1, max_length=40)
    relationships: list[RelationshipMeaning] = Field(max_length=40)
    unresolved: list[Text] = Field(max_length=40)


def normalize_objective(value):
    """Validate service callers as well as HTTP requests."""
    if value is None:
        return None
    return ObjectiveContract.model_validate(value).model_dump(mode='json')


def objective_definitions(objective):
    return {name: objective[name] for name in ('source_ref', 'metric', 'population', 'period', 'freshness')} | {
        'target': objective['target'] or 'No business threshold supplied',
    }
