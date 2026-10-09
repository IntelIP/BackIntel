"""Check real-predictor packaging using previously validated, explicitly fixture Jev data."""

import argparse
import json
import os
from pathlib import Path
import stat
import uuid

import psycopg

from runtime.ledger import dsn
from runtime.simulation import encoded
from scripts.capability_demo import domain_snapshot
from scripts.package_capabilities import package


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture-receipt",type=Path,required=True)
    args = parser.parse_args()
    if not os.environ.get("BACKINTEL_TEST_DATABASE_URL") or dsn() != os.environ["BACKINTEL_TEST_DATABASE_URL"] or not psycopg.conninfo.conninfo_to_dict(dsn())["dbname"].startswith("test_"):
        raise PermissionError("Packaging checks require an explicitly isolated fixture database")
    prior = json.loads(args.fixture_receipt.read_text())
    if prior["status"] != "passed" or "fixture" not in prior["provider"]:
        raise ValueError("A passed and clearly labelled provider-fixture receipt is required")
    tasks = [r["task_id"] for r in prior["checks"]]
    output = Path(__file__).resolve().parents[2]/"artifacts/validation/RealPackages"/("Attempt"+uuid.uuid4().hex[:12])
    output.mkdir(parents=True,mode=0o700)
    receipt = {"status":"running","candidate":"uncommitted-working-tree","semantic_provider":"fixture",
               "actual_paid_provider_calls":0,"checks":[]}
    try:
        with psycopg.connect(dsn(),autocommit=True) as connection:
            before = domain_snapshot(connection,tasks)
            for mode in ("development","real"):
                try:
                    package(connection,tasks,output/("Rejected"+mode.title()),mode=mode)
                except ValueError:
                    receipt["checks"].append({"mode":mode,"relabeling_rejected":True})
                else:
                    raise AssertionError("Fixture semantic results were relabelled as real Jev or simulated predictors")
            assert domain_snapshot(connection,tasks) == before
            packaged = package(connection,tasks,output/"Package",mode="predictor_fixture")
            assert packaged["paid_provider_calls"] == packaged["provider_usd"] == 0
            assert packaged["provider_fixture_requests"] == 54
            assert abs(packaged["fixture_provider_usd"]-.054) < 1e-10
            assert packaged["semantic_observations"] == "fixture"
            reports = list((output/"Package/Reports").glob("*/*/Report.html"))
            assert reports
            for report in reports:
                html = report.read_text()
                assert "Text findings: deterministic test fixtures" in html
                assert "<form" not in html and "href='/" not in html
            for generated in (output/"Package/Reports").glob("*/operator/GeneratedView.html"):
                assert "Text findings: deterministic test fixtures" in generated.read_text()
            access = output/"Package/AudienceAccess.json"
            assert stat.S_IMODE(access.stat().st_mode) == 0o600
            after = domain_snapshot(connection,tasks)
            assert before["jobs"] == after["jobs"] and set(before["evidence"]).issubset(after["evidence"])
            receipts_before = connection.execute("SELECT count(*) FROM backintel.capability_model_requests WHERE task_id=ANY(%s)",(tasks,)).fetchone()[0]
            package(connection,tasks,output/"ReplayPackage",mode="predictor_fixture")
            assert domain_snapshot(connection,tasks) == after
            assert connection.execute("SELECT count(*) FROM backintel.capability_model_requests WHERE task_id=ANY(%s)",(tasks,)).fetchone()[0] == receipts_before
            receipt.update(status="passed",reports=len(reports),files=len(packaged["files"]),package=str(output/"Package/Package.json"),
                           replay_unchanged=True,private_grants_mode="0600",fixture_provider_requests=54)
    except Exception as exc:
        receipt.update(status="failed",error={"type":type(exc).__name__,"message":str(exc)})
        raise
    finally:
        path = output/"Checks.json"
        path.write_bytes(encoded(receipt))
        print(json.dumps({"status":receipt["status"],"receipt":str(path)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
