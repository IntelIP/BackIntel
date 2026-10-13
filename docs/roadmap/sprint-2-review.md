# Sprint 2 review — Install the available app and open its demo

Completed October 11, 2026. **Status: Done for the revised, user-approved app setup scope.**

## Result for the user

The app from the supplied recovery ZIP opens in a fresh Python environment. A reviewer can follow the setup instructions below and inspect its saved support workflow. An incomplete extraction fails the package check; extracting the complete demo into a new folder fixes it.

No app source fix was needed. The useful setup clarification is that `backintel-resume.zip` contains a Git source bundle; the runnable demo ZIP is inside that restored source, not at the outer archive's top level.

Hudson approved changing Sprint 2 from toolkit recovery to this app setup check. APP-01 and APP-02 are Done. Toolkit stories S02/S03 remain unfinished; this result does not qualify the separate toolkit or run a new analysis.

## Identified source and reuse decision

| Item | Observed identity |
| --- | --- |
| Supplied archive | `/Users/hudson/Desktop/backintel-resume.zip` |
| Archive SHA-256 | `6caa0290c003140704d1b74f1e6386f14db839a190277cc737c8b43fa565697a` |
| Source bundle | `backintel-analysis-source.bundle` |
| Bundled branch | `codex/backintel-analysis-validation` |
| Recovered commit | `f5e2b693476541ce9fb7598d5d759a28b74af2b3` |
| Included demo | `docs/demo/Packages/BackIntelDemoBusinessV4.zip` |
| Demo SHA-256 | `451e1f5183c65417ae5c665e2813278f37738a7d9feae9ccc94178e49e0be505` |
| Local validation folder | `/Users/hudson/Library/Application Support/BackIntel/Validation/Sprint2/20261011-app-uazd8sff` |

The supplied manifest's six listed payload files matched their sizes and hashes during inspection. A separate clone reproduced the bundled source commit. Only the source bundle was copied from the outer archive; its separately supplied real dataset was not installed for this demo.

**Reuse decision:** keep this older source and demo isolated for the requested installation check. Preserve the canonical checkout's newer launcher and review-state repairs. Do not merge the old source back into the current branch or present its self-check as release qualification. The archive is different from the reported toolkit candidate.

## Observed setup checks

| Check | Result | What it establishes |
| --- | --- | --- |
| Restore source from supplied bundle | Confirmed | Separate checkout at the recorded commit. |
| Create a fresh environment | Confirmed | Python 3.11.9; system site packages disabled; only the environment's default pip 24.0 and setuptools 65.5.0 were present. No additional packages were installed. |
| Check the complete demo | Confirmed | `{"status": "passed", "files": 342, "new_provider_calls": 0}`. |
| Reject an extraction missing `Frontend/index.html` | Confirmed | Exit 1 with `ValueError: Package file is missing or changed: Frontend/index.html`. |
| Apply the setup remedy | Confirmed | Complete extraction into a different new folder passed the same package check and opened successfully. |
| Open an actual browser | Confirmed | Page and workspace endpoint returned HTTP 200; the browser rendered the completed workflow and two recorded support cases, with no JavaScript errors. |
| Inspect the visible interface | Confirmed | Screenshot shows the support workflow, its recorded stages, and its synthetic-data label. |
| New analysis or model execution | Not exercised | Opening the demo reads saved results. No provider credentials were supplied, and no new paid calls were made. |
| Independent human installation | Unverified | Codex performed this reproduction; a second person's reproduction is still separate work. |

The older package starts with one supplied synthetic review. That saved review was not created by a person during this sprint and is not evidence of independent human acceptance.

## Reproduce the setup

Requirements: Git, Python 3.10 or later, an unzip utility, and a browser. Use a new empty folder. Compare the archive hash and recovered commit with the identities above before running package code.

These commands reproduce the tested process. Validation used Python's standard-library `venv` and `zipfile` APIs for environment creation and extraction, plus the Git and app commands shown here.

```sh
backintel_resume_zip="/Users/hudson/Desktop/backintel-resume.zip"
backintel_sprint_dir="/absolute/path/to/a/new/sprint-2-folder"

mkdir -p "$backintel_sprint_dir"
shasum -a 256 "$backintel_resume_zip"
unzip -j "$backintel_resume_zip" backintel-analysis-source.bundle -d "$backintel_sprint_dir"
git clone --quiet --branch codex/backintel-analysis-validation \
  "$backintel_sprint_dir/backintel-analysis-source.bundle" "$backintel_sprint_dir/source"
git -C "$backintel_sprint_dir/source" rev-parse HEAD

python3 -m venv "$backintel_sprint_dir/.venv"
unzip "$backintel_sprint_dir/source/docs/demo/Packages/BackIntelDemoBusinessV4.zip" \
  -d "$backintel_sprint_dir/demo"
cd "$backintel_sprint_dir/demo/BackIntelDemo"
"$backintel_sprint_dir/.venv/bin/python" RunDemo.py --check
"$backintel_sprint_dir/.venv/bin/python" -u RunDemo.py --port 2054
```

Open <http://127.0.0.1:2054/>. Stop the server with Ctrl-C. If that port is occupied, select another available port and use it in the URL too. The built demo needs no Node installation, separate database server, downloaded model, or provider key.

**Missing-file remedy:** if the check names a missing or changed file, extract the verified demo ZIP completely into another new empty folder. Run `--check` there, then launch the server. Do not edit the manifest to make a damaged copy pass.

## Retained evidence and local handoff

- [Setup receipt](</Users/hudson/Library/Application Support/BackIntel/Validation/Sprint2/20261011-app-uazd8sff/setup-receipt.json>) records source identity, environment versions, the failing setup case, and the successful complete extraction.
- [Browser receipt](</Users/hudson/Library/Application Support/BackIntel/Validation/Sprint2/20261011-app-uazd8sff/browser-receipt.json>) records the actual page, workspace response, and visible content.
- [Browser screenshot](</Users/hudson/Library/Application Support/BackIntel/Validation/Sprint2/20261011-app-uazd8sff/demo-browser.png>) shows the opened recorded workflow.

The automated browser was closed after the check. The isolated local demo server was left running at <http://127.0.0.1:2054/> for Hudson to inspect; opening it in the Codex browser panel was queued by the app. Its reviews are stored only in this new extraction's `.demo-state/Reviews.sqlite3`. Existing services and review histories were not changed. The server belongs to this test and can be stopped when the demo is no longer needed.

## Remaining work

The revised sprint's setup outcome is complete. Fresh business analysis, prediction accuracy, customer usefulness, and release readiness remain untested by this sprint. The separate toolkit still needs accessible original source before S02/S03 and their dependent qualification stories can finish. Do not advance those stories using this demo result.

See the [completed Sprint 2 plan](sprint-2.md), [current sprint](current-sprint.md), [ordered backlog](agile-backlog.md), and [roadmap](README.md).
