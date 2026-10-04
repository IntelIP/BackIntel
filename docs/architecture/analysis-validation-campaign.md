# BackIntel validation campaign, October 4, 2026

The development source is recovered, and the offline validation framework is runnable. Overall acceptance remains **blocked** until the named source datasets, approved local model artifacts, and real analyst calls can be exercised in this environment. The owner authorized all five datasets for benchmarking and testing. No new provider calls have been made; new provider spending is **$0** of the authorized **$10** cap.

## Source and candidate

The cloud checkout initially contained the legacy PoC. The latest analysis files were uncommitted in the Mac checkout. Supported chat records from development chat `01a0fd11-fd5e-7f13-badf-4bf5e8d1ef63` supplied complete, untruncated additions and patches. Recovery applies those records chronologically to published base `499ae9e88117cb56646e3e1ab63a7e26ba4f1a29` in the isolated branch `codex/backintel-analysis-validation`.

Local commit `ae73a3855a18e7bf07329f3b493c5062ff0dfc7e` freezes the recovered source and a regenerated npm lockfile. Subsequent campaign fixes and checks are recorded in the branch and final receipts. This is a reconstructed candidate, not a claim of byte-identical recovery of the missing Mac tree. A historical Python command failed before any write; a later shell command masked its failure. That failed transform was skipped, and later successful patches established the final source. Machine-wide settings, credentials, datasets, model downloads/runs, generated runtime evidence, and Mac-only provisioning were not replayed.

Historical benchmark results remain in the earlier acceptance document as history. They do not establish this candidate's correctness or spending. Fresh evidence is kept outside tracked source under `/workspace/backintel-cloud/goal-campaign`. Final receipts name the tested clean commit; earlier attempts retain their dirty candidate identity and failures.

## Fresh validation

| Layer | Verified behavior | Remaining boundary |
| --- | --- | --- |
| Legacy baseline and current regressions | Six validators and 20 tests passed on the initial legacy PoC. The current candidate also runs all Python modules, including existing Jev, capability, Olist, replay, and provider-boundary regressions. | The initial baseline is historical; current all-module receipts separately identify their candidate. Optional Torch/TabICL constructor dependencies are explicit mocks in the no-download boundary test, not real-model evidence. |
| Enhancement backend | 40 unit/database cases cover adapters, timezone offsets, temporal/label/entity separation, numeric/evidence validation, permissions, goal revision, correction invalidation, promotion, partial resume, refresh failure, cancellation, duplicate admission, concurrency, spend caps, uncertain billing, cached-response replay without credentials/transport, malformed analyst output, hostile tool rejection, twelve-tool/six-call bounds, and elapsed-time stops. | Explicit fixtures; no production benefit or real model quality is established. |
| Static and contract | TypeScript build, pinned frontend/Python dead-code checks, Python compilation, validation-manifest schema, and embedded validator Python syntax. | Prepared local CI is not hosted CI execution. |
| Five-domain simulated workflow | Real browser → API → PostgreSQL/Redis → Aegra worker → deterministic provider tools → results; import, confirmed goal, evidence/snapshot inspection, follow-up preservation. | Small synthetic inputs and model responses; receipt is labeled `fixture`. |
| Recovery and attention | Unsupported numeric answer is partial, last answer survives failure, a correction refreshes the saved result, and an internal threshold event is retrieved. Fixture training, manager approval, and the prediction tool are exercised. A real process kill during import resumes the same accepted job in its second attempt without provider calls. A full fixture-database dump restores evidence bodies, response identities, and accepted results unchanged into a fresh database. An owned Redis container is stopped/restarted while a durable import is admitted. Credential expiry blocks API access and accepted queued work. Synthetic secrets are removed from failed results, API responses, events, and append-only application evidence. | General host logs, live provider echo behavior, and real model resource enforcement remain required. |
| Browser roles | Manager/analyst/viewer at 1440 and 390 pixels; all six views, role controls, core-route denial, no overflow/page errors, and keyboard evidence access. | The three-role viewport checks use the populated commerce fixture; complete live five-domain browser campaigns remain required. |
| Native clock | A disabled native cron is enabled without editing its due time, fires after its actual due time, completes a refresh, and is deleted. | Real scheduler and infrastructure with fixture sources/provider; not a live-data refresh result. |

Each offline run creates and removes a disposable database. E2E additionally removes the server, credential file, native cron, and only its own Redis prefix. Synthetic fixture files and safe logs/screenshots remain as evidence. Existing environment services and machine-wide Docker settings are preserved.

The independent fixture oracles assert group identity, count, and mean directly from the synthetic input definitions. The dump/restore proof uses the existing local PostgreSQL container's tools and removes the restored database. Receipts distinguish retained simulated requests from zero real provider calls and record dependency versions, source/configuration hashes, and maximum individual child-process memory. Aggregate service memory and the real-model ceiling remain unverified.

Component checks use pinned Vitest and React Testing Library against the real React workspace. Nine cases cover expired login, source confirmation, changed run limits, follow-up isolation, blocked refresh retention, pending controls, evidence inspection, read-only actions, empty results, and inert hostile markup. V8 coverage is retained as diagnostic evidence. Python branch coverage accompanies the 40 backend cases; neither broad percentage is used as a pass gate.

## Fixes exposed by validation

- Fresh-checkout regressions now create missing ignored presentation assets, retain database authentication while removing provider credentials, and mock optional model constructors explicitly. The all-module runner admits the analysis DB cases, clears provider bindings, rejects external HTTP transport, and records skips.
- Credential expiry is enforced in API authentication and queued-work admission. Scoped managers cannot grant sources outside their own domains. Credential redaction runs before error persistence and API rendering.
- Budget admission now treats a reserved request as in flight. The suite lock enforces the $10 campaign cap, one concurrent request, $0.25 request ceiling, 200 admitted attempts, and six calls per investigation. Settlement replaces the reservation; uncertain charges block new work. Admission rechecks current goal and actor permission.
- Accepted response replay returns the stored approved-model response before credential discovery or pricing/network access. Replayed calls keep the original response identity and do not increment the ledger.
- The notification query uses the event sequence column, so material-change notices can be retrieved.
- Timestamp parsing preserves explicit timezone offsets, keeping label-availability comparisons aligned to the actual instant.
- The frontend displays the configured campaign cap. Rollup call-interaction analysis stalled the build; disabling tree shaking preserves behavior and reduces the local build to under a second, with approximately 205 kB JavaScript output.
- Native schedule payloads are nonempty for the installed Aegra contract. Local worker credentials can be injected through an explicit path for portable validation. Failed filesystem refreshes retain source error information.
- Real-operation validators require explicit `mode: real`. Deterministic provider fixtures are marked throughout result and finding evidence and cannot qualify as a real run.

## Live-stage dependencies and next run

Kaggle and Hugging Face connection attempts are rejected by the environment proxy with HTTP 403. The environment has no ready analyst secret binding or prepared Decide/TabICLv2 checkpoints. Therefore no named source was downloaded and no real-model/frontier benchmark was attempted. The user's benchmark authorization is recorded; an environment download denial is not treated as a dataset-use refusal. Home Credit access may also require the Kaggle account's competition access once networking is available.

Enable the required source/model/provider hosts in the cloud network settings and inject the existing analyst key through environment secrets. Then acquire the actual named files, retain attribution and fingerprints, prepare approved pinned weights, and freeze the baseline/split/oracle before spending. Run the remaining real model comparisons, independent answer checks, live instruction-resistance and recovery cases, resource ceilings, complete five-domain browser-to-model journeys, and paid exact-candidate validation inside the same $10 campaign. Expanding the budget requires a new limit; the missing live evidence is not replaced by simulations.

The repository's required `graphify update .` could not run: no compatible executable was installed, and the available `graphify-cli==0.1.0` lacks `update`. Current Python callers, dependencies, 24 application routes, and the three Aegra graph registrations were inspected directly and recorded in `dependency-inspection.json`. The missing graphify check remains an explicit tooling limitation.

See [the phase-by-phase goal](../roadmap/analysis-workspace-testing-goal.md) and [the portable operator runbook](analysis-workspace-runbook.md). No public push, PR, publication, or deployment was performed.
