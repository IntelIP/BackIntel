# Analysis sandbox implementation results

## SmolVM migration — 2026-11-12 UTC

Owner-authorized local migration is implemented on macOS ARM64. Both the benchmark's
`run_python` and the opt-in specialist now execute in SmolVM 1.31.1; final artifact rendering
uses a separate clean VM. `backintel/dev` in Doppler now selects `BACKINTEL_SANDBOX=smolvm`.
GPT-6.1 Sol and its ChatGPT subscription route are unchanged. These checks were run before
committing the migration; PR #4 and its CI results describe the earlier Docker candidate.

The prepared image retains ID
`sha256:9820b507a21f383ad0af1fac20426a6123ef718df79e35740461ab3ff3087dac`.
Its current local archive SHA-256 is
`d12436507cf87f1eb99cc360232e9dc9b2ac0ec8c9addf4167395cdc78ba24a5`.
The pinned runtime distribution, extracted binary and operating constraints are recorded
in [sandbox-environment.md](sandbox-environment.md). Docker remains necessary for preparing
the OCI image and hosting optional database services; prepared file-based execution no
longer performs Docker image lookups or depends on its Linux VM waking from Resource Saver.

The first concurrent cold-start check exposed a separate SmolVM 1.31.1 image-cache race:
the hardlink/copy staging fallback can truncate the shared input when machine creations
overlap. BackIntel now holds a bounded host file lock during image staging only. A real
regression starts two VMs concurrently from a fresh archive, verifies both return `42`,
and verifies the archive hash is unchanged. VM execution remains concurrent. The failed
first four-case attempt remains at `data/output/analysis-smolvm-20261112T155300Z`; its runs
failed during infrastructure setup and made no model calls. They are not model failures.

Final direct verification:

- `doppler run -p backintel -c dev -- uv run backintel sandbox check`: passed; backend
  `smolvm`, Python 3.12.16, public-network probe blocked.
- `BACKINTEL_SMOLVM_TESTS=1 uv run pytest -q --tb=short`: **189 passed, 7 skipped** in
  71.26 seconds. Real VM tests cover root/source write denial, non-root UID, empty effective
  capabilities, no-new-privileges, coding recovery, file/output limits, deadlines, assigned
  service socket isolation, SQLite reads, artifact export, concurrent startup and cleanup.
  Optional live-source and large-input tests remain outside this run.
- Ruff lint and format, Vulture and whitespace checks passed.
- Four-case scripted graph integration: **4/4 passed**, no unresolved cases, **zero provider
  calls**, 61.169 seconds summed recorded latency. Retail refunds, irregular energy and
  service availability each produced independently checked report/chart/workbook bundles;
  missing-cost correctly returned `cannot_answer`. Workbook cells and report values agreed.
- No task-owned `backintel-*` machines remained after completion.

The final comparison is `data/output/analysis-smolvm-20261112T155700Z/comparison.json`,
with per-case `run.json` and retained artifacts. Source version is `4db4fdfda73698e3`.
These four-case results use the separately pending comparison scripts and full local
working tree; the scoped migration commit does not publish that expanded harness.
This is scripted runtime/integration evidence, not a new LangSmith live-model comparison.
Historical Sol 4/4 and Luna 2/4 scores still belong to their original Docker experiments.
Memory records now report sampled VM used memory, including guest overhead; they are not
directly comparable to Docker cgroup high-water marks. Linux/Windows SmolVM distributions,
unseen-domain model quality and large-data acceptance are not claimed. INT-454 remains
In Progress for its broader release/reliability scope.

### Scoped commit verification

The migration was staged separately from the earlier benchmark expansion and versioning
changes. An isolated checkout of that staged snapshot passed **155 tests, 6 optional skips**
with real SmolVM acceptance enabled, in 77.70 seconds. Ruff lint/format, Vulture and Gitleaks
passed. Its runtime source version is `7e3758f52558caca`; the earlier 189-test count and
four-case comparison above include the separately pending evaluation files. No runtime
code changed between the migration checks and commit preparation. The differing source
fingerprint includes the pending `uv.lock` version metadata excluded from this commit.
