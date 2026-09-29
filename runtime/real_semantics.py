"""Real Jev boundary with durable paid-request admission and fail-closed replay.

No credential is loaded and no network call occurs without a matching, approved,
unexpired authorization. Unknown pricing permits only an explicitly approved
single-request probe; a money ceiling is not claimed for an unpriced request.
"""
from __future__ import annotations

import asyncio
import os
import json
import math
from pathlib import Path
import time
from decimal import Decimal, InvalidOperation

import psycopg
from psycopg.types.json import Jsonb

from runtime.evidence import canonical_body
from runtime.jev import OpenRouterJevClassifier, answer_payload, request_id, usage_counts
from runtime.ledger import dsn
from runtime.observations import validate_response
from runtime.simulation import digest, encoded


def questions_for(task: dict, types) -> dict:
    questions = {}
    for question in task["questions"]:
        if question["type"] == "boolean":
            questions[question["id"]] = types.Noul(instructions=question["prompt"])
        else:
            scale = task["policy"]["signal_scale"]
            if scale != int(scale) or not 1 <= scale <= 10:
                raise ValueError("Real Jev numeric questions require an explicit 1..10 ordinal scale")
            questions[question["id"]] = types.Score(instructions=question["prompt"],criteria=list(range(int(scale)+1)))
    return questions


def typed_answer(question: dict, answer: dict) -> dict:
    if question["type"] == "boolean":
        probability = answer["noul"]
        response = {"status":"known","value":probability >= .5,
                    "distribution":{"true":probability,"false":1-probability},"reason":"actual_jev_response"}
    else:
        legend = {int(k):v for k,v in answer["legend"].items()}
        probabilities = {int(k):v for k,v in answer["probabilities"].items()}
        if set(probabilities) - set(legend):
            raise ValueError("Jev score probability has no matching legend")
        values = [legend[k] for k in sorted(probabilities)]
        weights = [probabilities[k] for k in sorted(probabilities)]
        response = {"status":"known","value":sum(v*p for v,p in zip(values,weights)),
                    "distribution":{"values":values,"probabilities":weights},"reason":"actual_jev_ordinal_expectation"}
    validate_response(question,response)
    return response


def scope_for(task_record: dict, sources: list[dict]) -> dict:
    return {"task_sha256":task_record["sha256"],"source_sha256s":sorted(r["sha256"] for r in sources),
            "questions_sha256":digest(task_record["body"]["questions"])}


def runtime_credential(task_id):
    key = os.environ.get("OPENROUTER_API_KEY")
    if key:
        return key
    path = os.environ.get("BACKINTEL_PROVIDER_CREDENTIAL_FILE")
    if not path or not Path(path).is_file():
        return None
    try:
        record = json.loads(Path(path).read_text())
        expiry, tasks = record["expires_at"],record["task_ids"]
        if type(expiry) not in (int,float) or not math.isfinite(expiry) or not isinstance(tasks,list) or not all(isinstance(t,str) for t in tasks):
            raise ValueError("Invalid credential bounds")
        if expiry <= time.time() or task_id not in tasks:
            return None
        key = record["key"]
        return key if isinstance(key,str) and key.strip() else None
    except (OSError,KeyError,TypeError,ValueError):
        raise RuntimeError("Ephemeral provider credential record is invalid") from None


def _default_classifier(model: str, key):
    if not key:
        raise RuntimeError("Approved provider request requires ephemeral credential injection")
    return OpenRouterJevClassifier(key,model=model)


def _verified_metadata(metadata: dict, requested_model: str) -> None:
    expected_models = {requested_model, "typesafe/" + requested_model}
    if requested_model == "jev-1.13":
        # Exact alias resolution returned by the approved 2026-09-28 probe.
        # Keep other dated revisions blocked until their identity is checked.
        expected_models.add("typesafe/jev-1.13-20260917")
    if not metadata.get("request_id") or metadata.get("model") not in expected_models:
        raise RuntimeError("Actual Jev request/model identity is missing or differs; response retained without retry")
    try:
        cost = Decimal(str(metadata["cost_usd"]))
        if not cost.is_finite() or cost < 0:
            raise ValueError("Invalid charge")
    except (KeyError,InvalidOperation,ValueError) as error:
        raise RuntimeError("Actual provider charge unavailable; response retained and further calls blocked") from error


def usage_for(store, *, excluding=(), strict=True) -> dict:
    records = store.connection.execute("""SELECT request_key,state,model,metadata FROM backintel.capability_model_requests
        WHERE task_id=%s AND NOT (request_key=ANY(%s::text[]))""", (store.task_id, list(excluding))).fetchall()
    spent = Decimal(0)
    uncertain_calls = unknown_cost = False
    for _, state, model, metadata in records:
        try:
            if state != "completed":
                uncertain_calls = True
                raise RuntimeError("Uncertain provider request prevents accepting a complete-cost result")
            _verified_metadata(metadata, model)
            spent += Decimal(str(metadata["cost_usd"]))
        except RuntimeError:
            if strict:
                raise
            unknown_cost = True
    return {"provider_calls": None if uncertain_calls else len(records),
            "provider_fixture_requests": sum(bool((r[3] or {}).get("test_fixture")) for r in records),
            "provider_usd": None if unknown_cost else float(spent), "local_compute_usd": None,
            "provider_requests_admitted": len(records), "provider_request_keys": [r[0] for r in records]}


def request_real(task_record: dict, source: dict, authorization_id: str, classifier_factory=None) -> dict:
    task, provider = task_record["body"], task_record["body"]["observation_provider"]
    if provider["implementation_mode"] != "real" or provider["name"] != "openrouter-jev":
        raise ValueError("Real Jev execution requires the explicit OpenRouter provider contract")
    content = source["body"]["content"]
    key = digest({"task":task_record["sha256"],"source":source["sha256"],"provider":provider})
    with psycopg.connect(dsn(),autocommit=True) as connection:
        # Session lock spans the external request without keeping an SQL transaction open.
        connection.execute("SELECT pg_advisory_lock(hashtextextended(%s,71))",(authorization_id,))
        existing = connection.execute("SELECT state,response,metadata FROM backintel.capability_model_requests WHERE request_key=%s",(key,)).fetchone()
        if existing:
            if existing[0] != "completed":
                raise RuntimeError("Previous provider request is uncertain/blocked; automatic paid retry prohibited")
            _verified_metadata(existing[2],provider["version"])
            return {"request_key":key,"response":existing[1],"metadata":existing[2],"cached":True}
        with connection.transaction():
            authorization = connection.execute("""SELECT model,max_requests,max_input_characters,max_measured_usd,
                price_ceiling_known,approved,scope,scope_sha256,expires_at>now()
                FROM backintel.capability_provider_authorizations WHERE authorization_id=%s FOR UPDATE""",(authorization_id,)).fetchone()
            if not authorization or not authorization[5] or not authorization[8]:
                raise PermissionError("Provider execution lacks current explicit approval")
            model,limit,max_characters,max_usd,priced,_,scope,scope_sha,_ = authorization
            if model != provider["version"] or digest(scope) != scope_sha or scope.get("task_sha256") != task_record["sha256"] or source["sha256"] not in scope.get("source_sha256s",[]) or scope.get("questions_sha256") != digest(task["questions"]):
                raise PermissionError("Provider request exceeds approved source/question/model scope")
            if not isinstance(content,str) or not content.strip() or len(content)>max_characters:
                raise ValueError("Provider input violates approved character bound")
            previous = connection.execute("SELECT state,metadata FROM backintel.capability_model_requests WHERE authorization_id=%s",(authorization_id,)).fetchall()
            if len(previous)>=limit or (not priced and (limit != 1 or previous)):
                raise RuntimeError("Provider request budget exhausted or unpriced multi-request execution prohibited")
            spent = Decimal(0)
            for state,metadata in previous:
                if state != "completed":
                    raise RuntimeError("Uncertain prior provider request blocks further spend")
                _verified_metadata(metadata,model)
                spent += Decimal(str(metadata["cost_usd"]))
            if max_usd is not None and spent >= max_usd:
                raise RuntimeError("Measured provider budget exhausted")
            # Record exact primitive definitions; the factory is created only after authorization checks.
            from langchain_typesafe import Noul, Score
            types = type("Questions",(),{"Noul":Noul,"Score":Score})
            question_objects = questions_for(task,types)
            request_doc = {"model":model,"state":content,"questions":{k:v.model_dump(mode="json") for k,v in question_objects.items()}}
            if len(encoded(request_doc))>25_000:
                raise ValueError("Bounded provider payload exceeded")
            credential = runtime_credential(task["id"]) if classifier_factory is None else None
            if classifier_factory is None and not credential:
                raise RuntimeError("Approved provider request requires ephemeral credential injection")
            # The foreign key requires source admission to have committed before a paid request.
            connection.execute("SET LOCAL lock_timeout='2s'")
            connection.execute("""INSERT INTO backintel.capability_model_requests
                (request_key,task_id,source_sha256,model,request,state,authorization_id)
                VALUES (%s,%s,%s,%s,%s,'admitted',%s)""",(key,task["id"],source["sha256"],model,Jsonb(request_doc),authorization_id))
        classifier = None
        started = time.perf_counter()
        try:
            classifier = classifier_factory(model) if classifier_factory else _default_classifier(model,credential)
            response = classifier.invoke({"state":content,"questions":question_objects})
            answers = answer_payload(response)
            metadata = dict(classifier.last_metadata)
            metadata["request_id"] = metadata.get("request_id") or request_id(response)
            metadata["model"] = metadata.get("model") or getattr(response,"model",None)
            metadata["input_tokens"],metadata["output_tokens"] = usage_counts(response)
            metadata.update(wall_ms=(time.perf_counter()-started)*1000,provider="openrouter",implementation_mode="real",
                            requested_model=model,provider_calls=1,local_compute_usd=None)
            metadata["test_fixture"] = classifier_factory is not None
            saved = canonical_body({"answers":answers,"raw_response":getattr(classifier,"last_response",{})})
            # Preserve a valid response even if charge/model checks subsequently block acceptance.
            connection.execute("""UPDATE backintel.capability_model_requests SET state='completed',response=%s,metadata=%s,finished_at=now()
                WHERE request_key=%s""",(Jsonb(saved),Jsonb(canonical_body(metadata)),key))
        except Exception as error:
            connection.execute("""UPDATE backintel.capability_model_requests SET state='blocked',error=%s,finished_at=now()
                WHERE request_key=%s AND state='admitted'""",(type(error).__name__,key))
            raise
        finally:
            if classifier is not None:
                asyncio.run(classifier.aclose())
        _verified_metadata(metadata,model)
        return {"request_key":key,"response":saved,"metadata":metadata,"cached":False}


def extract_real(store, task_record: dict, source: dict, at: int, *, authorization_id=None,classifier_factory=None) -> list[dict]:
    authorization_id = authorization_id or os.environ.get("BACKINTEL_PROVIDER_AUTHORIZATION")
    if not authorization_id:
        raise PermissionError("Real extraction requires a named approved provider authorization")
    reply = request_real(task_record,source,authorization_id,classifier_factory)
    provider = task_record["body"]["observation_provider"]
    response_record = store.find("provider_response",reply["request_key"])
    if not response_record:
        response_record = store.put("provider_response",reply["request_key"],{
            "provider":provider,"request_key":reply["request_key"],"response":reply["response"],"metadata":reply["metadata"],
            "source":source["sha256"],"task":task_record["sha256"]},at,[task_record["sha256"],source["sha256"]])
    observations = []
    for question in task_record["body"]["questions"]:
        answer = reply["response"]["answers"].get(question["id"])
        if answer is None:
            raise ValueError("Real Jev response omitted a required question")
        response = typed_answer(question,answer)
        key = digest({"source":source["sha256"],"task":task_record["sha256"],"question":question,"provider":provider})
        previous = store.find("observation",key)
        observations.append(previous or store.put("observation",key,{
            "source":source["sha256"],"question_id":question["id"],"question":question,"provider":provider,
            "response":response,"task":task_record["sha256"],"request_key":reply["request_key"],
            "request_id":reply["metadata"]["request_id"],"actual_model":reply["metadata"]["model"]},at,
            [source["sha256"],task_record["sha256"],response_record["sha256"]]))
    return observations
