"""Prepare a reviewable one-request Jev probe; execution requires recorded approval."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import time

import psycopg
from psycopg.types.json import Jsonb

from runtime.bootstrap import initialize
from runtime.contracts import admit_source,current_sources,register_task
from runtime.evidence import Evidence
from runtime.ledger import dsn
from runtime.real_semantics import extract_real,scope_for
from runtime.simulation import digest,encoded
from runtime.synthetic import history

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT/"artifacts"/"validation"/"RealModelPreparation"


def prepare(scenario: str) -> dict:
    if os.environ.get("BACKINTEL_TEST_DATABASE_URL") != dsn() or not psycopg.conninfo.conninfo_to_dict(dsn())["dbname"].startswith("test_"):
        raise RuntimeError("Real-model preparation requires the isolated test database")
    initialize()
    task,rows,_ = history(scenario)
    task["id"] = scenario+"-real-probe"
    task["observation_provider"] = {"name":"openrouter-jev","version":"jev-1.13","implementation_mode":"real"}
    with psycopg.connect(dsn(),autocommit=True) as connection:
        store = Evidence(connection,task["id"])
        task_record = register_task(store,task)
        admit_source(store,task_record,{"format":"json","data":[rows[0]]},0)
        source = current_sources(store,0,task_record["sha256"])[0]
        scope = scope_for(task_record,[source])
        authorization = "jev-probe-"+digest(scope)[:24]
        connection.execute("""INSERT INTO backintel.capability_provider_authorizations
            (authorization_id,provider,model,max_requests,max_input_characters,max_measured_usd,
             price_ceiling_known,approved,scope_sha256,scope,expires_at)
            VALUES (%s,'openrouter','jev-1.13',1,5000,NULL,false,false,%s,%s,to_timestamp(%s))
            ON CONFLICT (authorization_id) DO NOTHING""",(authorization,digest(scope),Jsonb(scope),time.time()+86400))
        approved = connection.execute("SELECT approved FROM backintel.capability_provider_authorizations WHERE authorization_id=%s",(authorization,)).fetchone()[0]
    config = json.loads((ROOT/"config"/"real_models.json").read_text())
    plan = {"schema":"backintel-real-model-proposal/v1","provider_authorization_id":authorization,
            "provider_execution_approved":approved,"scenario":scenario,"task_id":task["id"],"task_sha256":task_record["sha256"],
            "source_sha256":source["sha256"],"synthetic_text":source["body"]["content"],"questions":task["questions"],
            "provider":{"name":"OpenRouter","requested_model":"jev-1.13","max_requests":1,"max_input_characters":5000,
                        "input_characters":len(source["body"]["content"]),"known_price":None,"enforceable_dollar_cap":False,
                        "automatic_retry":False,"credential_store":"macOS Keychain: BackIntel OpenRouter / runtime"},
            "model_use":{"approved":False,"configuration_sha256":digest(config),"routes":["catboost","tabiclv2"],
                         "catboost_license":"Apache-2.0","tabiclv2_license":config["tabiclv2"]["license"],
                         "checkpoints":config["tabiclv2"]["checkpoints"],
                         "download_bytes":sum(c["bytes"] for c in config["tabiclv2"]["checkpoints"].values()),
                         "device":"cpu","threads":2,"training_records_per_scenario":24},
            "limits":["The first Jev probe requires explicit approval because its price is not publicly available.",
                      "One successful probe does not authorize the full real-model comparison.",
                      "Synthetic-data model results do not establish real-world quality or savings."]}
    OUTPUT.mkdir(parents=True,exist_ok=True)
    (OUTPUT/"proposal.json").write_bytes(encoded(plan))
    return plan


def execute(plan: dict) -> dict:
    if os.environ.get("BACKINTEL_TEST_DATABASE_URL") != dsn() or not psycopg.conninfo.conninfo_to_dict(dsn())["dbname"].startswith("test_"):
        raise RuntimeError("Real-model probe requires the isolated test database")
    with psycopg.connect(dsn(),autocommit=True) as connection:
        authorization = connection.execute("SELECT approved,expires_at>now() FROM backintel.capability_provider_authorizations WHERE authorization_id=%s",
                                           (plan["provider_authorization_id"],)).fetchone()
        if authorization != (True,True):
            raise PermissionError("Explicit, current approval is required before credential retrieval")
        store = Evidence(connection,plan["task_id"])
        task_record,source = store.get(plan["task_sha256"]),store.get(plan["source_sha256"])
        credential = subprocess.run(["security","find-generic-password","-s","BackIntel OpenRouter","-a","runtime","-w"],
                                    capture_output=True,text=True,check=True).stdout.rstrip("\n")
        previous = os.environ.get("OPENROUTER_API_KEY")
        try:
            os.environ["OPENROUTER_API_KEY"] = credential
            observations = extract_real(store,task_record,source,0,authorization_id=plan["provider_authorization_id"])
        finally:
            if previous is None:
                os.environ.pop("OPENROUTER_API_KEY",None)
            else:
                os.environ["OPENROUTER_API_KEY"] = previous
        responses = store.list("provider_response")
        result = {"status":"passed","observations":[r["sha256"] for r in observations],
                  "metadata":[r["body"]["metadata"] for r in responses],"full_model_comparison":"unfinished"}
        (OUTPUT/"probe-result.json").write_bytes(encoded(result))
        return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action",choices=("prepare","execute"))
    parser.add_argument("--scenario",choices=("support","equipment"),default="support")
    args = parser.parse_args()
    try:
        if args.action == "prepare":
            plan = prepare(args.scenario)
            result = {"proposal":str(OUTPUT/"proposal.json"),"provider_authorization_id":plan["provider_authorization_id"],
                      "paid_calls":0,"credential_retrieved":False,"execution_approved":plan["provider_execution_approved"]}
        else:
            result = execute(json.loads((OUTPUT/"proposal.json").read_text()))
        print(json.dumps(result,indent=2))
        return 0
    except Exception as error:
        # Provider exceptions may contain arbitrary transport details; never echo credentials.
        print(json.dumps({"status":"blocked","error_type":type(error).__name__,
                          "message":"Execution stopped. Inspect the sanitized request ledger; do not retry an uncertain paid request."}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
