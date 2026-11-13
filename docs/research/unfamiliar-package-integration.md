# Unfamiliar-domain execution and grading integration

Implemented and exercised offline on 2026-11-13 from main `51846a4`, for INT-442/INT-443.
This records integration evidence. Linear remains the authority for issue status. No model
provider was invoked, no source was downloaded, and no reserved question or answer was used.

## What can run now

`scripts/package_unfamiliar_data.py` copies one domain's explicitly named, checksum-pinned
raw files and ordinary source definitions into a new package. It never mounts the shared
acquisition directory. For energy it uses the already qualified extracted text member; it
does not mount the ZIP or extract arbitrary archive members. No notebooks, scripts, solutions,
profiles or evaluator files are included. Existing package paths cannot be overwritten.

The new `package:<dataset>` Store validates the package manifest, names, bytes, hashes and
exact inventory before a run. Each asset is an individual read-only source mount at
`/data/assigned/<name>`; the operator manifest itself stays outside the VM. Later sibling
files cannot broaden those mounts. The same analyst tools and existing raw-file skill are
used; no prompt, provider, agent architecture or runtime dependencies changed.

This path admits at most 30 files, 1 GiB of encoded inputs, and 64 scalar columns per data
file with names up to 128 characters. Discovery returns actual names/types and row counts;
description returns null counts and three samples with string cells clipped to 200 characters.
CSV fields stay strings so source sentinels and labels remain visible. Data grain,
relationships, date/numeric interpretations and business filters remain analyst discoveries.
Unsupported/nested/oversized schemas, malformed manifests, extra files, changed bytes,
symlinks and missing assets are rejected. These limits qualify the selected small sources,
not a general >=10 GiB, arbitrary-archive or arbitrary-schema loader.

Existing `AnalysisSandbox` supplies no-public-network enforcement, resource/output limits,
per-command deadlines, cancellation, source isolation and clean final rendering. A source
mount is not a prompt-injection defense: the existing analyst policy treats source contents
as data. The coding worker must still keep evaluator materials out of model inputs.

## Reproduce the readiness check

From this checkout with the already acquired raw files and existing SmolVM image:

```bash
uv run python scripts/package_unfamiliar_data.py \
  --domain transport --output data/stores/package/unfamiliar-transport-v1
uv run python scripts/package_unfamiliar_data.py \
  --domain building-energy --output data/stores/package/unfamiliar-energy-v1
uv run python scripts/run_unfamiliar_smoke.py \
  --package data/stores/package/unfamiliar-transport-v1 \
  --references data/unfamiliar-v1/evaluator/references-development-v3/python.json \
  --output results/raw/unfamiliar-transport-smoke-new
uv run pytest tests/test_unfamiliar_package.py tests/test_unfamiliar_references.py -q
```

Package commands intentionally fail if their output exists. Reuse the verified package for
subsequent runs, or select a new package name when preparing a new immutable revision. The
tests are synthetic and do not require the source downloads, VM or private evaluator files.
The smoke requires SmolVM and explicitly uses a fake scripted model; its analysis program
computes from the mounted raw file, and its independent references are read only afterward
by host evaluator tooling. It cannot be presented as a live model or discovery benchmark.

Retained packages:

| Package | Allowed assets | Total bytes including source notes | Manifest SHA-256 |
| --- | --- | ---: | --- |
| `unfamiliar-transport-v1` | Trip Parquet, zone CSV, ordinary notes | 1,440,710 | `19319d05dda8c15056877c6d5ab53d99eb71d33582e7fee83262513f1967c68d` |
| `unfamiliar-energy-v1` | Extracted energy text, ordinary notes | 132,962,009 | `541ab2cec5cf52f7a19161eed95f8d249538af18c3a380fd395d12ff13f362f5` |

The real transport smoke is retained at
`results/raw/unfamiliar-transport-smoke-20261113/`. It completed with:

- Only the three allowlisted files visible; opening each for append was denied. No operator
  manifest, sibling/evaluator path, Docker socket or provider API key was visible. All source
  hashes were unchanged after execution.
- Source discovery, report computation, sandbox evidence reproduction, PNG tool delivery,
  clean VM rendering and verified export completed. HTML/CSV/workbook agreed with the report.
- Both mapped population counts matched the independent development reference. The result
  remains `task_pass: null`: scripted decisions and correct cells do not establish live
  analytical competence or certify arbitrary prose.
- Zero provider calls and USD 0 model cost. SmolVM 1.31.1 used the existing 2 CPU / 2 GiB
  analysis profile; peak sampled guest-used memory was 219,553,792 bytes. The record retains
  the image/archive identities, code version, source identity and structured completion.

`smoke-summary.json`, `run.json`, `evaluator-mapping.json` and `evaluator-grade.json` retain
the checks; the bundle is `artifacts/report/`. The checks prove this selected source path,
not a new measurement of every existing sandbox timeout/cancellation branch.

## Deterministic report-to-reference grading

`scripts/grade_unfamiliar_report.py` consumes the trusted host `run.json`, a frozen reference
file and an evaluator-owned cell mapping. The mapping binds the exact run/reference/report
hashes and a case ID. Each reference leaf is mapped explicitly to table/row/column; numerical
facts also require units and independently interpreted metric/population/window/grain.
Mappings must be derived from the actual method and claims, never chosen by matching values.
Their authorship/interpretation remains an evaluator responsibility, not a fact inferred by
the checker. Normalized equivalent definitions can map to the same reference without a
preferred narrative.

```bash
uv run python scripts/grade_unfamiliar_report.py \
  --run results/raw/unfamiliar-transport-smoke-20261113 \
  --references data/unfamiliar-v1/evaluator/references-development-v3/python.json \
  --mapping results/raw/unfamiliar-transport-smoke-20261113/evaluator-mapping.json \
  --output results/raw/unfamiliar-transport-smoke-20261113/regrade-new.json
```

The grader verifies structured status, the exported bundle, every workbook table, the
host-retained reproduced specification hash, and each mapped cell's executed evidence.
Counts/labels use exact typed comparison and continuous values use the frozen tolerances.
Missing reference leaves fail fixed-reference coverage. Additional numeric table cells are
listed as unmapped; they cannot earn task-level correctness from nearby mapped facts.
Analyst evidence is never executed by this host grader; existing sandbox reproduction owns
that execution boundary.

An inappropriate `cannot_answer` on an answerable fixed challenge fails. A refusal on a
documented insufficient-data challenge receives status feedback only: its explanation still
needs semantic verification. Runtime failures return invalid/null quality feedback for
classification rather than becoming invented analytical failures. The synthetic tests also
reject wrong amounts, units, labels, cherry-picked populations, missing evidence, changed
host-spec bindings and incomplete mapping. An unassessed causal assertion explicitly does
not become certified by correct cells.

## Remaining campaign boundary

This completes the selected raw-file path and narrow fixed-fact integration. It does not
complete INT-443's general discovery claim extraction/independent calculation, causal-claim
or refusal-explanation grading. Discovery coverage, supported findings and limitations
remain separate pending dimensions; do not convert `task_pass: null` to a passing score.
Every additional material claim requires its own independent calculation and interpretation.

The reserved exact questions, source profile, reference implementations and expected answers
remain ignored evaluator-owned material. The runtime receives only one frozen question and
its own raw/domain documentation package. No reserved files were inspected or packaged in
this integration step. A candidate must be frozen before a separate evaluator executes them.

The full 21-task/35-response campaign still requires executable discovery/refusal criteria,
a frozen candidate/criteria manifest, provider readiness and a finite assigned allowance.
This offline check spends no part of a model allowance and makes no domain-transfer release
claim. The >=10 GiB corpus/runtime work under INT-446 is also separate.
