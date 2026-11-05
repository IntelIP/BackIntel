# Sprint 1 review — Recorded demo and alpha source

October 10, 2026. **Closed; Hudson accepted the results and continuation.**

The accepted [Sprint 1 plan](sprint-1.md) is archived. Sprint 2 is now the [current sprint](current-sprint.md).

The reviewer can inspect the recorded support finding, compare prediction methods, and save a decision that survives a restart. The existing toolkit alpha has a specific recovery locator, but its contents are not accessible in this local chat. This sprint does not qualify the alpha.

## User issues and dispositions

| Item | User issue | Result | Status |
| --- | --- | --- | --- |
| S01 | A reviewer needs to know what works and retain a review. | Recorded browser journey, saved-review restart, and package rejection checked. Instructions corrected. | Done; accepted October 10 |
| S02 discovery task | A maintainer needs the existing candidate's location before continuing it. | Cloud locator and expected identity found; exact access blocker and retrieval action recorded. | Done for bounded discovery |
| Full S02 | A maintainer needs recovered source and a reconciliation decision. | Candidate payload unavailable here; recovery and comparison have not run. | Blocked |
| S03 | A developer needs a clean installation. | Depends on full S02. | Not started; outside this sprint |

## S01 — What was directly checked

1. Extracted the canonical business-v4 ZIP into a new sprint folder. The trusted-checkout launcher accepted all 341 packaged files.
2. Opened the actual packaged browser interface. The workflow shows completed, five comparison rows, and recorded playback with no new model calls.
3. Opened Access's original evidence and interpretation. The synthetic report describes failed login; the saved interpretation says `risk: True`. Its displayed experimental estimate is 79%.
4. Opened corrected Accounts evidence. It describes working service and an information request; the saved interpretation says `risk: False`. Its displayed estimate is 26%.
5. Saved a uniquely labelled **automated synthetic review** for Access through the interface. Stopped and restarted the server for the same extraction. Reviewed / Access retained the exact reason and Follow up decision. This was not Hudson's review or a customer action.
6. Removed `Frontend/index.html` from a separate disposable copy. The trusted launcher rejected it with `ValueError: Package file set differs from its manifest`. The normal extraction and canonical ZIP were preserved.

No browser page errors were observed during the saved-review journey. Package-rejection reporting initially expected different error wording; the actual rejection output is retained in the evidence record.

The fresh extraction showed **Reviewed 0**. The old instructions promised a preloaded current Access review. The checkout's package guide and narration now tell the reviewer to create a current review first. They also distinguish packaged launch instructions from the original recording's services. The ZIP's embedded instructions remain historical.

## Capability boundary

| Surface | What this sprint establishes |
| --- | --- |
| Recorded demonstration | Confirmed browser inspection and local review retention. Inputs are synthetic; analytical results are saved from the original execution. The scenario's Simulated badge does not mean a new model execution occurred. |
| Workflow simulation | Separate entry point: `python3 -m scripts.simulate`. Uses synthetic data and simulated model responses. Not run in this sprint. |
| Known-dataset analysis workspace | Existing development entry point: [analysis workspace runbook](../architecture/analysis-workspace-runbook.md). Its database, workers, source permissions, and hosted-analysis setup are separate from playback. No new live analysis ran here. |
| Optional Python review interface | Documented in [DemoPackage.txt](../demo/DemoPackage.txt). Not installed or independently checked in this sprint. |
| Toolkit alpha | Historical chat-reported candidate. Current source, installation, and release qualification remain unverified. |
| Customer benefit | Customer accuracy, preparation time, savings, and complete operating cost remain unmeasured. |

## S02 discovery — Source blocker and retrieval action

The last completed turn in **“Review testing and demo workflows”** reports this candidate:

- Chat ID: `01a10eb2-7340-7052-bf28-f16577c3901a`; host: `durable`.
- Cloud file: `/workspace/backintel-agent-toolkit-0.1.0a2-candidate.zip`.
- Candidate commit: `f0a3d2573fb3da9469d81e35691f60a42a0d9a1b`.
- Expected archive SHA-256: `eefa76c68d7664100f512e94a456daef0c1f9fde94ece39273cf6c40216f67e0`.
- Reported archive size: 5,629,318 bytes; 248 verified payload files.

These identities come from the historical chat, not a newly inspected archive. That chat leaves independent developer reproduction, hosted checks, and release review pending.

**Confirmed access blocker:** the cloud file is not present at that path on this local host. The exact candidate commit is absent from this checkout. GitHub's commit lookup returned HTTP 422 and its `codex/agent-toolkit-alpha` branch lookup returned HTTP 404. This local chat has no exposed cross-host file download for that cloud path. Earlier bounded checks did not find the exact filename in Downloads, Desktop, the GitHub parent folder, or this checkout; that is not a whole-machine absence claim.

**Continuation checks after acceptance:** An exact-name Spotlight lookup returned no indexed match in Hudson's home folder. The saved project registry lists only the canonical BackIntel checkout. A fresh read of GitHub's alpha branch returned no matching reference. These bounded checks did not expose a recoverable candidate; they do not establish absence everywhere.

**Retrieval owner:** Hudson, using the original cloud chat's file download/export. Preserve the ZIP separately; use the expected hash to identify it. Codex can then complete S02's manifest/source check and comparison with canonical source. Do not replace it with the older `backintel-resume.zip` or recreate the alpha from chat summaries. Refine S03 only after that recovery succeeds.

## Review evidence and retained state

- [Recorded workflow and comparison](sprint-1-evidence/01-recorded-workflow.png)
- [Original Access evidence](sprint-1-evidence/02-original-access-evidence.png)
- [Saved synthetic Access review](sprint-1-evidence/03-saved-access-review.png)
- [Corrected Accounts result](sprint-1-evidence/04-corrected-accounts.png)
- [Same review after server restart](sprint-1-evidence/05-review-after-restart.png)
- [Browser observations and exact review-store path](sprint-1-evidence/demo-check.json)
- [Package rejection result](sprint-1-evidence/package-rejection.json)

The sprint's demo server is stopped. The normal extraction and its separate local review database are retained. Only disposable rejection copies were removed. New provider/infrastructure spending: **$0**. All documentation and evidence changes remain local and uncommitted.

To repeat the retained demonstration from the trusted checkout:

```sh
cd /Users/hudson/Documents/GitHub/Products/BackIntel
python3 -m scripts.package_business_demo --package-root /tmp/backintel-sprint-1-demo.vpegTH/BackIntelDemo --port 2053
```

Open `http://127.0.0.1:2053/`, select Reviewed / Access, and inspect the saved synthetic note. Keep the extraction path unchanged to reuse that review store. Stop with Ctrl-C.

**Sprint review accepted:** Hudson said “Proceed” on October 10, 2026 after the results handoff. This accepts the documented sprint result and authorizes continuation. It does not establish that Hudson independently reproduced the demonstration or qualified the toolkit alpha.

**Next delivery step:** retrieve the existing candidate and finish full S02; then select a bounded S03 installation task. The [current sprint](current-sprint.md) and [ordered backlog](agile-backlog.md) retain these dependencies.
