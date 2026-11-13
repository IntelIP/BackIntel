# Independent unfamiliar-domain references

Prepared offline on 2026-11-13 for INT-443. **All 18 fixed challenge references have
been computed and reconciled**: 15 numeric cases and three documented insufficient-data
cases. No model was called, no source was written, and no code was committed or pushed.
This completes the fixed-reference handoff, not all discovery-scoring acceptance for INT-443.

The public [receipt](../../benchmarks/unfamiliar/unfamiliar-v1/reference-receipt.json)
contains source/task/implementation/output hashes and coverage only. It contains no reserved
answers or precise questions. Actual truth remains in ignored evaluator-owned files.

## Implementations and direct checks

- `scripts/unfamiliar_python_references.py`: Polars raw-file loading, independent filtering
  and aggregation; stable `math.fsum` for grouped monetary totals.
- `scripts/unfamiliar_sql_references.py`: independently authored DuckDB SQL reading the raw
  parquet and CSV/text files. It does not import Python references or consume derived tables.
- `scripts/build_unfamiliar_references.py`: verifies source hashes, retains both outputs,
  writes discrepancies, and fails when they disagree. Existing output directories cannot be
  overwritten. Counts/labels are exact; finite continuous values use `abs_tol=1e-6` in the
  requested unit and `rel_tol=1e-8`. Boolean values are not accepted as numbers.
- `scripts/unfamiliar_fact_checks.py`: checks one evaluator-mapped report cell against an
  independent value, unit, interpreted metric/population/window/grain, and an existing
  sandbox evidence-reproduction receipt. It calls the existing report binding validator.
  It never executes analyst code on the host or marks surrounding prose as verified.
- `tests/test_unfamiliar_references.py`: self-contained synthetic sources, with no download,
  model call or dependency on private files. Thirteen tests check date boundaries, signed
  money, unknown groups, join multiplication, type-7 quantiles, missing/zero observations,
  unit conversion, the 95% coverage boundary, wrong labels/units/populations/windows,
  missing evidence, broken bindings and discrepancy preservation.

The private reserved implementation uses separately written standard-library CSV/statistics
and DuckDB paths. One evaluator-private counterexample test checks source-specific boundary,
sentinel, unit, flag and ordering behavior. Its code and results are not runtime material.
The development SQL path was authored by a separate worker. The reserved paths were authored
by the same evaluator worker and provide computational cross-checking, not blind review.

Both paths share acquired bytes, task definitions, source documentation and agreed output
field names. They do not independently establish the source vendor's original measurement
accuracy. Refusal references are documented source-availability judgments. Matching absent
column guards does not establish that an arbitrary model refusal explained the missing inputs.

## Interpretation decisions frozen before results

Development definitions follow the [task contract](../../benchmarks/unfamiliar/unfamiliar-v1/task-contract.md).
January transport means pickup timestamps in `[2023-01-01,2023-02-01)`; duration exclusions
are counted within that population. Recorded money remains signed USD. Lookup Borough values
NULL, blank, `Unknown` and `N/A` map to `unknown`; absent lookup keys map to `unmatched`.
The unknown payment group remains explicit even when empty. Raw labels remain in the source.

Energy uses recorded minute labels and no timezone conversion or imputation. `missing_minutes`
means expected January slots minus numeric active-power observations, including absent rows;
`rows_present` is reported separately. kWh is the sum of observed minute-average kW divided
by 60. Submeters are already Wh per minute, and reconciliation uses only minutes with all
required numeric inputs. Daily coverage uses 1,440 slots and a 95% threshold. The energy
comparison wording was clarified before calculations to signed second-window mean minus
first-window mean in kW; it does not mean the mathematical absolute value. No thresholds
were selected from model results.

## Evidence and fixes retained

Final development evidence: `data/unfamiliar-v1/evaluator/references-development-v3/`.
Final reserved evidence: `data/unfamiliar-v1/evaluator/references-reserved-v2/`.
Each directory contains `python.json`, `sql.json`, `discrepancies.json` and `receipt.json`.
Both final comparisons have zero discrepancies. A fresh development Python calculation
reproduced its serialized output hash exactly after the stable-summation fix.

Earlier `references-development-v1/`, `references-development-v2/` and
`references-reserved-v1/` are retained. The initial development outputs differed between
repetitions in two grouped monetary totals by at most `4.656612873077393e-10`, within the
frozen tolerance. Stable summation removes that avoidable byte-level nondeterminism. No
expected answer or tolerance was relaxed. A synthetic test's exact `0.95` floating-point
assertion was changed to an approximate comparison; both calculation paths had already
agreed. An initial SQL alias-binding error was repaired before the successful reference run.

The source profiler formerly globbed matching weather CSV filenames beyond the verified
manifest. It now reads only explicitly listed, verified CSV assets. The focused regression
rejects an unverified manifest entry. A full profile run with an invalid, matching decoy CSV
present also exactly matched the prior profile; the decoy was removed. The result is retained
as `data/unfamiliar-v1/evaluator/profile-v3.json`. The earlier `profile-v2.json` corrected a
station-name suffix check; original profile evidence remains retained.

## Reproduce and hand off

```bash
python scripts/build_unfamiliar_references.py --output data/unfamiliar-v1/evaluator/references-new-run
pytest tests/test_unfamiliar_references.py -q
```

The first command requires the pinned raw files; the test command does not. Download missing
sources only through the bounded acquisition command documented in the qualification report.
Do not mount the shared raw/evaluator directory into an analyst. The subsequent
[execution integration](unfamiliar-package-integration.md) implements per-file allowlists,
packages the two development domains and demonstrates one real-source scripted SmolVM run.

The evaluator custodian must retain the ignored reserved specification, implementation,
test and result files when transferring or removing this local worktree. A public hash is a
commitment, not a recoverable backup of private truth. No access-control infrastructure has
been added; evaluator workspace separation depends on assigned ownership. The implemented
runtime mount allowlist excludes evaluator material and sibling domains.

The subsequent integration adds exact mapped report-to-reference checks and rejection of
inappropriate refusal on an answerable fixed challenge. INT-443 remains open for arbitrary
claim verification and refusal-explanation semantics. The existing `validate_report`, sandbox `reproduce_report`
and bundle checks support structural consistency and reproducibility. They do not prove
interpretation, causality, missingness disclosure, coverage or business usefulness. A mapped
fact can use the new narrow helper; every additional material claim still needs an independent
calculation and interpretation check. Unsupported or unmapped prose must remain ungraded or
fail the applicable explicit criterion, never inherit a passing score from a nearby correct
number. Keep discovery coverage, supported findings and limitations separate from fixed
correctness and runtime outcomes. No preferred narrative or human calibration is claimed.
