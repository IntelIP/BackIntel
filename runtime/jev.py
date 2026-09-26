"""LangChain TypeSafe/Jev review classification with source and cost lineage."""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import time
import uuid
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import httpx2
import psycopg
from psycopg.types.json import Jsonb

from runtime.costs import begin_usage, finish_usage
from runtime.ledger import accept, admit, dsn

QUESTION_PATH = Path(__file__).resolve().parents[1] / "config" / "review_measurements.v1.json"


class _OpenRouterCaptureClient(httpx2.Client):
    """Capture OpenRouter's raw usage.cost/id while reusing LangChain TypeSafe parsing."""
    def __init__(self, **client_kwargs):
        super().__init__(**client_kwargs)
        self.last_metadata: dict = {}

    def post(self, *args, **kwargs):
        response = super().post(*args, **kwargs)
        try:
            body = response.json()
            usage = body.get("usage") or {}
            self.last_metadata = {
                "request_id": body.get("id"),
                "provider": body.get("provider"),
                "model": body.get("model"),
                "cost_usd": usage.get("cost"),
            }
        except Exception:
            self.last_metadata = {}
        return response


class OpenRouterJevClassifier:
    """LangChain TypeSafeClassifier routed through OpenRouter's System One API."""
    provider_name = "openrouter"
    def __init__(self, api_key: str, transport: Any | None = None):
        from langchain_typesafe import Choice, Noul, Score, TypeSafeClassifier
        if transport is not None:
            self._client = _OpenRouterCaptureClient(transport=transport)
        else:
            self._client = _OpenRouterCaptureClient(timeout=45.0)
        self._async_client = httpx2.AsyncClient(timeout=45.0)
        self._classifier = TypeSafeClassifier(
            api_key=api_key,
            base_url="https://openrouter.ai/api",
            model="jev-1.13",
            client=self._client,
            async_client=self._async_client,
        )
        self.question_types = type("QuestionTypes", (), {"Choice": Choice, "Noul": Noul, "Score": Score})
        self.last_metadata: dict = {}

    def invoke(self, request: dict) -> Any:
        self._client.last_metadata = {}
        response = self._classifier.invoke(request)
        self.last_metadata = dict(self._client.last_metadata)
        return response

    async def aclose(self) -> None:
        self._client.close()
        await self._async_client.aclose()


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def load_question_set(path: Path = QUESTION_PATH) -> tuple[dict, str]:
    definition = json.loads(path.read_text(encoding="utf-8"))
    if definition.get("schema") != "backintel-review-measurements/v1":
        raise ValueError("Unexpected measurement-set schema")
    digest = hashlib.sha256(canonical_json(definition).encode()).hexdigest()
    return definition, digest


def build_questions(definition: dict, typesafe: Any) -> dict:
    questions = {}
    for name, spec in definition["questions"].items():
        if spec["type"] == "noul":
            questions[name] = typesafe.Noul(instructions=spec["instructions"])
        elif spec["type"] == "choice":
            questions[name] = typesafe.Choice(instructions=spec["instructions"], criteria=spec["criteria"])
        elif spec["type"] == "score":
            questions[name] = typesafe.Score(instructions=spec["instructions"], criteria=spec["criteria"])
        else:
            raise ValueError(f"Unsupported Jev primitive: {spec['type']}")
    return questions


def answer_payload(response: Any) -> dict:
    answers = {}
    for group in ("nouls", "choices", "scores"):
        values = getattr(response, group, {}) or {}
        for name, answer in values.items():
            if hasattr(answer, "model_dump"):
                answers[name] = answer.model_dump(mode="json")
            elif isinstance(answer, dict):
                answers[name] = answer
            else:
                attrs = ("type", "noul", "choice", "score", "confidence", "probabilities", "legend")
                answers[name] = {key: getattr(answer, key) for key in attrs if hasattr(answer, key)}
    if not answers:
        raise ValueError("TypeSafe response contained no typed answers")
    return answers


def usage_counts(response: Any) -> tuple[int | None, int | None]:
    usage = getattr(response, "usage", None)
    if usage is None:
        return None, None
    def value(*names):
        for name in names:
            if isinstance(usage, dict) and usage.get(name) is not None:
                return int(usage[name])
            found = getattr(usage, name, None)
            if found is not None:
                return int(found)
        return None
    return value("input_tokens", "prompt_tokens"), value("output_tokens", "completion_tokens")


def request_id(response: Any) -> str | None:
    try:
        value = getattr(response, "request_id", None)
        return str(value) if value else None
    except Exception:
        return None


async def register_question_set(conn: psycopg.AsyncConnection, definition: dict, digest: str) -> None:
    await conn.execute("""
        INSERT INTO backintel.semantic_question_sets (version, content_sha256, definition)
        VALUES (%s, %s, %s) ON CONFLICT (version) DO NOTHING
    """, (definition["version"], digest, Jsonb(definition)))
    row = await (await conn.execute(
        "SELECT content_sha256 FROM backintel.semantic_question_sets WHERE version=%s",
        (definition["version"],))).fetchone()
    if row[0].strip() != digest:
        raise ValueError("Question-set version already exists with different content; increment its version")


async def classify_one(*, partition_id: str, review: dict, definition: dict,
                       question_digest: str, classifier: Any, question_objects: dict) -> dict:
    review_id = review["review_record_id"]
    message = review["message"]
    text_digest = hashlib.sha256(message.encode("utf-8")).hexdigest()
    lock_key = f"{partition_id}:{review_id}:{definition['version']}"
    # Session advisory lock prevents two local workers from billing twice for an
    # identical pending review. A hard process kill releases the lock; if the API
    # accepted the call before the result was saved, a retry may still call twice.
    async with await psycopg.AsyncConnection.connect(dsn(), autocommit=True) as conn:
        await conn.execute("SELECT pg_advisory_lock(hashtextextended(%s, 0))", (lock_key,))
        try:
            existing = await (await conn.execute("""
                SELECT observation_id, answers, request_id, model FROM backintel.jev_observations
                 WHERE partition_id=%s AND review_record_id=%s AND question_set_version=%s
            """, (partition_id, review_id, definition["version"]))).fetchone()
            if existing:
                return {"observation_id": str(existing[0]), "answers": existing[1], "request_id": existing[2],
                        "model": existing[3], "reused": True}

            if classifier is None:
                raise ValueError("Recorded observation missing; reuse-only mode never calls a provider")

            provider = getattr(classifier, "provider_name", "typesafe")
            usage_id = await begin_usage(partition_id=partition_id, stage="jev", provider=provider,
                                         model="jev-1.13" if provider == "openrouter" else "jev-latest", record_count=1)
            started = time.monotonic()
            try:
                response = await asyncio.to_thread(
                    classifier.invoke, {"state": message, "questions": question_objects})
                answers = answer_payload(response)
                metadata = getattr(classifier, "last_metadata", {}) or {}
                req_id = request_id(response) or metadata.get("request_id")
                in_tokens, out_tokens = usage_counts(response)
                actual_model = str(metadata.get("model") or getattr(response, "model", None) or ("typesafe/jev-1.13" if provider == "openrouter" else "jev-latest"))
                charge = None
                if metadata.get("cost_usd") is not None:
                    try:
                        charge = Decimal(str(metadata["cost_usd"]))
                    except (InvalidOperation, ValueError):
                        charge = None
                await finish_usage(usage_id, outcome="success", wall_ms=round((time.monotonic()-started)*1000),
                                   request_id=req_id, input_tokens=in_tokens, output_tokens=out_tokens,
                                   model=actual_model,
                                   charge_status="measured" if charge is not None else "unknown",
                                   charge_usd=charge,
                                   price_ref="OpenRouter response usage.cost" if charge is not None else None)
            except asyncio.CancelledError:
                await asyncio.shield(finish_usage(usage_id, outcome="cancelled",
                                                  wall_ms=round((time.monotonic()-started)*1000),
                                                  charge_status="unknown"))
                raise
            except Exception:
                await finish_usage(usage_id, outcome="error", wall_ms=round((time.monotonic()-started)*1000),
                                   charge_status="unknown")
                raise

            observation_id = uuid.uuid4()
            async with await psycopg.AsyncConnection.connect(dsn()) as write_conn:
                await write_conn.execute("""
                    INSERT INTO backintel.jev_observations
                      (observation_id, partition_id, review_record_id, question_set_version,
                       input_text_sha256, source_language, translation_method, model,
                       request_id, answers, usage_event_id)
                    VALUES (%s, %s, %s, %s, %s, %s, NULL, %s, %s, %s, %s)
                    ON CONFLICT (partition_id, review_record_id, question_set_version) DO NOTHING
                """, (observation_id, partition_id, review_id, definition["version"], text_digest,
                      review.get("source_language", "pt-BR-assumed-from-dataset"), actual_model,
                      req_id, Jsonb(answers), usage_id))
                persisted = await (await write_conn.execute("""
                    SELECT observation_id, answers, request_id, model FROM backintel.jev_observations
                     WHERE partition_id=%s AND review_record_id=%s AND question_set_version=%s
                """, (partition_id, review_id, definition["version"]))).fetchone()
            return {"observation_id": str(persisted[0]), "answers": persisted[1],
                    "request_id": persisted[2], "model": persisted[3], "reused": False}
        finally:
            await conn.execute("SELECT pg_advisory_unlock(hashtextextended(%s, 0))", (lock_key,))


async def record_correction(*, observation_id: str, corrected_by: str,
                            corrected_answers: dict, rationale: str) -> str:
    """Append a human correction without changing the original model observation."""
    try:
        target = uuid.UUID(observation_id)
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError("observation_id must be a UUID") from exc
    if not corrected_by.strip() or not rationale.strip() or not isinstance(corrected_answers, dict):
        raise ValueError("A reviewer, non-empty rationale, and structured corrected answers are required")
    correction_id = uuid.uuid4()
    async with await psycopg.AsyncConnection.connect(dsn()) as conn:
        exists = await (await conn.execute(
            "SELECT 1 FROM backintel.jev_observations WHERE observation_id=%s", (target,))).fetchone()
        if not exists:
            raise ValueError("Cannot correct an unknown Jev observation")
        await conn.execute("""
            INSERT INTO backintel.jev_observation_corrections
              (correction_id, observation_id, corrected_by, corrected_answers, rationale)
            VALUES (%s, %s, %s, %s, %s)
        """, (correction_id, target, corrected_by.strip(), Jsonb(corrected_answers), rationale.strip()))
    return str(correction_id)


async def process_review_ids(*, partition_id: str, review_record_ids: list[int],
                             classifier: Any | None = None, definition_path: Path = QUESTION_PATH,
                             reuse_only: bool = False) -> dict:
    if not partition_id or len(partition_id) > 80:
        raise ValueError("partition_id must be nonempty and at most 80 characters")
    if not review_record_ids or len(review_record_ids) > 100 or any(type(i) is not int or i < 1 for i in review_record_ids):
        raise ValueError("review_record_ids must contain 1..100 positive integer IDs")
    if len(set(review_record_ids)) != len(review_record_ids):
        raise ValueError("review_record_ids must be unique")
    if reuse_only and classifier is not None:
        raise ValueError("reuse_only cannot be combined with a classifier")
    owned_classifier = classifier is None and not reuse_only
    typesafe = None
    if owned_classifier:
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise RuntimeError("OPENROUTER_API_KEY is not configured; no Jev request was made")
        classifier = OpenRouterJevClassifier(api_key=api_key)
        typesafe = classifier.question_types
    elif classifier is not None:
        typesafe = getattr(classifier, "question_types", None)
        if typesafe is None:
            raise ValueError("Injected classifier must provide `question_types` for isolated tests")
    try:
        definition, question_digest = load_question_set(definition_path)
        questions = build_questions(definition, typesafe) if typesafe is not None else {}
        async with await psycopg.AsyncConnection.connect(dsn()) as conn:
            await register_question_set(conn, definition, question_digest)
            rows = await (await conn.execute("""
                SELECT r.review_record_id, r.message, sb.file_sha256, sr.source_row_number
                  FROM backintel.reviews r
                  JOIN backintel.source_batches sb ON sb.batch_id=r.source_batch_id
                  JOIN backintel.source_records sr ON sr.batch_id=r.source_batch_id AND sr.source_row_number=r.source_row_number
                 WHERE r.review_record_id = ANY(%s) AND r.message IS NOT NULL AND r.message ~ '[^[:space:]]'
                 ORDER BY r.review_record_id
            """, (review_record_ids,))).fetchall()
        if len(rows) != len(review_record_ids):
            raise ValueError("One or more requested review IDs are absent or have no text")
        reviews = [{"review_record_id": row[0], "message": row[1], "file_sha256": row[2],
                    "source_row_number": row[3], "source_language": "pt-BR-assumed-from-dataset"} for row in rows]
        input_manifest = [{"review_record_id": r["review_record_id"],
                           "message_sha256": hashlib.sha256(r["message"].encode()).hexdigest(),
                           "source_file_sha256": r["file_sha256"], "source_row_number": r["source_row_number"]}
                          for r in reviews]
        input_digest = hashlib.sha256(canonical_json({"measurement_set": question_digest, "reviews": input_manifest}).encode()).hexdigest()
        await admit(partition_id, len(reviews), input_digest)
        results = []
        for review in reviews:
            results.append(await classify_one(partition_id=partition_id, review=review, definition=definition,
                                              question_digest=question_digest, classifier=classifier,
                                              question_objects=questions))
        result_digest = hashlib.sha256(canonical_json([
            {key: result[key] for key in ("observation_id", "answers", "request_id", "model")}
            for result in results
        ]).encode()).hexdigest()
        await accept(partition_id, len(reviews), input_digest, result_digest=result_digest)
        return {"partition_id": partition_id, "question_set_version": definition["version"],
                "question_set_sha256": question_digest, "input_sha256": input_digest,
                "result_sha256": result_digest, "processed_reviews": len(results),
                "reused_observations": sum(r["reused"] for r in results),
                "observations": results}
    finally:
        if owned_classifier:
            await classifier.aclose()
