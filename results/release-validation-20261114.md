# Clean-checkout validation for v0.0.1

Validated 2026-11-14 UTC on macOS ARM64, using a fresh local Git clone checked out at
`b0569942267e9530f0ff77fbd80263111085dbe5`. No private datasets or credentials were copied
into the clone. The host's already-prepared pinned SmolVM binary/image were reused for
the separately identified VM checks.

| Check | Observed result |
| --- | --- |
| `uv sync --frozen --python 3.12` | Installed the locked project and dependencies successfully |
| `uv run backintel --help` | CLI entry point loaded successfully |
| `uv run pytest -q` | 252 passed, 15 optional skips; no provider calls |
| Ruff lint and format | Passed; 103 source/test/script files already formatted |
| Vulture, minimum confidence 100 | Passed |
| `uv run backintel acceptance build --split development` | Rebuilt 17 cases; data hash `0b65012dc6217c5a77b8e8b5f64f84b6ebd53b3a85e7cd73faa17da7bc60c741`, matching the frozen campaign |
| Four-case scripted specialist integration | 4/4 passed through the real graph, SmolVM, artifact export and independent table/workbook checks; zero provider calls |
| Fresh benchmark VM probe | Python 3.12.16, successful exit, public TCP networking blocked |
| Native credential reuse | Read-only model retrieval returned HTTP 200 for both configured native model IDs; zero inference calls |
| Assembled review package | Runtime files match the frozen candidate; Gitleaks and diff checks passed |

The scripted specialist cases were sales/refunds, missing cost, irregular energy and
service availability. They exercise privileged reference decisions and establish
integration behavior, not autonomous model quality or visual-design acceptance. Three
cases delivered report bundles; the missing-cost case correctly declined. Report tables,
CSV/workbook contents and completion contracts were checked by the existing evaluator.

The native credential and VM probes were separate from the credential-free clean-clone
tests. API credentials remained in the approved host secret-manager path and were not
mounted into a VM. No login, key replacement, model fallback or credit purchase occurred.

Retained local evidence: the clean clone's
`data/output/v0001-clean-integration/comparison.json`, per-case `run.json` files and bundles;
the operator's tool receipts retain the installation/test output and read-only probes.
The clean clone remains available for direct inspection. Hosted CI for the first assembled
package passed at `5e1360101a934ab64beb470b5be82fa42efaf970` in
[run 43544176006](https://github.com/IntelIP/BackIntel/actions/runs/43544176006).
Any later publication head requires its own applicable hosted checks.

Analytical acceptance is determined separately by the
[frozen reliability campaign](../docs/reliability-campaign.md). These checks do not
replace live development/reserved results or authorize merge, release or deployment.
