# Sprint 2 — Install the available app and open its demo

Revised October 11, 2026. **Status: Done for the approved app installation scope.** See the [sprint review](sprint-2-review.md).

## Sprint goal

A reviewer can restore the supplied BackIntel app, follow written setup instructions, and open its recorded demo without the team's private workspace.

Hudson approved this target after supplying `backintel-resume.zip`. This explicitly replaces the original Sprint 2 toolkit target. The separate toolkit recovery and installation stories, S02 and S03, remain unfinished in the [backlog](agile-backlog.md). Opening this app does not close those stories or prove that new analyses work.

**Owner:** Codex executes and records results. **Timebox:** one focused working session. **Boundary:** $0 new provider or infrastructure spending; synthetic recorded examples only. Preserve the canonical checkout, existing services, data, and reviews.

## Selected source

- Supplied archive: `/Users/hudson/Desktop/backintel-resume.zip`.
- Archive SHA-256: `6caa0290c003140704d1b74f1e6386f14db839a190277cc737c8b43fa565697a`.
- Bundled source commit: `f5e2b693476541ce9fb7598d5d759a28b74af2b3`, branch `codex/backintel-analysis-validation`.
- Included recorded demo: `docs/demo/Packages/BackIntelDemoBusinessV4.zip`, SHA-256 `451e1f5183c65417ae5c665e2813278f37738a7d9feae9ccc94178e49e0be505`.

This is the earlier app recovery archive, not the reported `0.1.0a2` toolkit. Its embedded demo predates the canonical checkout's launcher repairs. Test the identified saved version in isolation; do not replace newer source or distribute it as a newly qualified release.

## Ordered user issues

APP-01 and APP-02 are local sprint labels, not external ticket IDs.

| Order | Issue | User problem | Observable result | Status |
| --- | --- | --- | --- | --- |
| 1 | APP-01 — Restore the supplied app | The ZIP is useful only if its source can be opened and identified. | A separate checkout matches the bundled commit; source and demo identities are recorded. | Done |
| 2 | APP-02 — Install and open the demo | A new reviewer needs complete instructions and a working first screen. | A fresh Python environment opens the recorded demo, and a missing-file setup failure has a tested remedy. | Done |

## APP-01 — Restore the supplied app

**Story:** As a maintainer, I need to restore the app we actually have, so that we can test it without guessing what another chat built.

1. Use the already inspected archive and verified manifest; retain its original source identity.
2. Copy only the Git source bundle into a separate validation folder and clone its recorded branch. Do not copy the separately supplied real dataset into the demo setup.
3. Confirm the checkout commit and inspect the included demo's entry point, imports, and instructions before running it.
4. Record the reuse decision: test this saved app separately, preserve the newer canonical implementation, and leave the separate toolkit stories open.

**Done when:** the identified source is restored separately, the included demo is located, and the reuse decision is recorded.

## APP-02 — Install and open the demo

**Story:** As a reviewer, I need to install the demo from written instructions, so that I can inspect saved findings without private setup help.

1. Create a new Python virtual environment with Python 3.10 or later. Do not reuse installed app dependencies or credentials.
2. Extract the included recorded demo into a new folder. Its built interface and local review service use Python's standard library; no additional package installation is needed.
3. From the extracted `BackIntelDemo` folder, run `RunDemo.py --check`, then `RunDemo.py` with an available local port.
4. Open the actual browser interface and confirm that its saved workspace loads. Identify synthetic data and historical results clearly.
5. Try an extraction missing `Frontend/index.html`; confirm that setup rejects it, then demonstrate the remedy by extracting a complete copy into a new folder.
6. Save the commands, Python version, observed results, and setup remedy in the sprint review. Close the automated browser after validation; leave the local demo available for Hudson to inspect. Stop only the test-created server when it is no longer needed.

**Done when:** the fresh environment validates the complete package, the browser shows the recorded workspace, and the missing-file remedy works.

## Setup handoff

The [sprint review](sprint-2-review.md) contains the tested recovery and launch commands, observed results, and local demo URL. The original ZIP's `RESUME.md` also describes broader analysis recovery; those instructions are source material, not authorization to download models, run paid analyses, or spend its historical budget.

For this sprint, use the recorded demo only. If `--check` reports a missing or changed file, extract the verified demo ZIP into a new empty folder and run the check again. If the default port is occupied, use `--port 2054` or another available port.

## Review and stop condition

Record APP-01 and APP-02 as Done or Blocked from actual results. Close this revised sprint once its installation, browser, and missing-file checks pass. Keep S02/S03 open; do not automatically advance to their dependent toolkit stories.

This sprint proves local setup of the saved demo. It does not prove fresh analysis, prediction accuracy, customer value, independent human reproduction, toolkit qualification, or release readiness.

## References

- [Ordered backlog](agile-backlog.md)
- [Product roadmap](README.md)
- [Sprint 1 results](sprint-1-review.md)
