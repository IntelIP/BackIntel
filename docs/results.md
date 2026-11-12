# BackIntel v2: measured capability report

Measured 2026-11-09 in America/New_York. One Deep Agents lead; OpenAI GPT-6 Luna through OpenRouter; Anthropic Claude Haiku 5.5 as the method judge. No sub-agents.

The required six-store Olist matrix passed **143/144 responses (99.3%)**. This measures the requested result, reproducible evidence and appropriate refusal, across levels 1–3. The one failure was an agent execution loop on an unanswerable net-profit question. The revised standing/replay suite passed **15/17** responses; its failures remain visible.

These are single-pass results from versioned development iterations, not an estimate of future production reliability. Each experiment retains its model, prompt/skill version, source/reference hash where available, outputs and LangSmith feedback. Historical git SHAs identify the v1 base. The model experiments ran before v2 was committed; working-tree source hashes identify the new runs.

## Storage matrix

All six required storage types ran the same 24 Olist questions (8 per level). The two source datasets were also loaded and directly checked on every adapter: [16 parity checks](../results/store-parity.json) compared row counts and monetary aggregates against polars. The UCI data contains 1,067,371 source rows; Olist has 99,441 order rows.

| Storage | Supported | Median seconds | Reported analyst USD | Experiment |
|---|---:|---:|---:|---|
| sqlite | 24/24 | 32.6 | 0.0348 | [LangSmith](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/8005c331-91e2-4cb7-b0be-5098a78e0575) |
| postgres | 24/24 | 14.9 | 0.0274 | [LangSmith](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/7a57655e-0720-45d6-b4fa-d27564cfe636) |
| ferretdb | 23/24 | 19.8 | 0.0389 | [LangSmith](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/f5308e82-7897-4588-a915-ce2f115b4e8f) |
| lake-iceberg | 24/24 | 21.3 | 0.0275 | [LangSmith](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/b9a0705d-2e0e-4722-b469-90e6909b2e66) |
| clickhouse | 24/24 | 20.5 | 0.0330 | [LangSmith](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/f899ee4c-c205-4343-bf38-2687bcede90a) |
| files | 24/24 | 14.4 | 0.0293 | [LangSmith](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/3180652a-f8bf-4d60-8dfb-9fafd868b45d) |

The UCI 20-question suite passed 20/20 on each of SQLite, PostgreSQL, CSV files and the local Parquet baseline (80/80 total). Its corrected Parquet run is [here](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/e274ced4-8a0e-46d1-97a9-e40ef36bb657). UCI was loaded and checked for parity on the other native stores; this report does not claim a full 20-question model run on those three adapters.

The additional Olist local-Parquet baseline passed 24/24. A mixed CSV/JSON folder passed a three-question probe, one question per level; it is not a second 24-question raw-file suite. [Mixed-file experiment](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/bfd11479-7a0e-4d82-ab02-2f9c23072edd).

## Higher difficulty levels

| Capability | Supported | What ran |
|---|---:|---|
| Cross-store | 6/6 | PostgreSQL order tables combined with SQLite catalog tables |
| Standing problems | 3/3 | Repeat purchasing, delivery/satisfaction, category/seller performance |
| Ambient replay | 12/14 | Monthly delivery, quarterly repeat purchasing, weekly category/seller reviews |
| Scale | 6/6 | TPC-H SF1, 8,661,245 generated rows across 8 tables, through DuckDB over Parquet |

The [standing/replay experiment](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/33cb05b4-9ae7-409e-956a-d7e050d166b3) uses snapshots that hide future delivery/review observations. The declared SP delivery shift in May was detected. These are replayed invocations, not a live scheduler. TPC-H is a generated analytical workload, not REES46 clickstream data or an official TPC-H performance result. Larger scale factors were not run; the Windows desktop was unavailable.

## Response failures and grader limits

- **FerretDB profit question:** `olist-l3-07` asks for 2017 net profit. The tables have revenue/payment fields and no cost ledger. The agent repeatedly inspected the same schema and fetched revenue data instead of declining, exhausted 80 graph steps, and returned no structured answer. The trace contains 26 model calls. This is a measured refusal/execution-limit failure, not fabricated profit and not an unavailable database.

- **Quarterly repeat report:** `olist-l6-repeat-2017-09` gives all four correct metric values, but its second cited Python program uses the explanatory store note as a database path. That program cannot re-execute. Correct numbers with a broken claimed check fail the evidence criterion.

- **March delivery report:** `olist-l6-2018-03` contains every correct expected fact, but repeats `relative_change_RJ` with inconsistent units. The required report contract forbids duplicate metrics, so the response fails format/correctness despite full fact recall.

One replay initially failed because the code printed per-state Boolean tests rather than the literal NO_CHANGE label. That was a verifier false rejection: the declared 25% rule follows deterministically from the reproduced changes. The scorer now accepts that alternative, the run was rescored without regenerating an answer, and the corresponding LangSmith feedback was updated.

The deterministic headline concerns requested result fields. Re-execution does not prove complete data lineage or validate every sentence in a narrative. The independent method judge supplies written reasons and anchored ratings for conventions, method fit, overreach and caveats. The revised standing/replay mean method score is 0.735. Numerical correctness is scored by code, never by that judge.

A seeded judge contrast scored a valid join-based method 0.875 and a hardcoded answer with invented causal/profit claims 0.0. [Calibration artifact](../results/grader-calibration.json). This is an agent-authored sanity check, not human calibration, inter-rater agreement or external leaderboard validation. Old probabilistic judge results are retained as historical baselines and are not directly comparable to the revised anchored rubric.

The old eight-run delivery replay allowed post-cutoff outcomes; it is retired as evidence of prospective ambient capability. Original experiments remain available. The revised replay is the reported result. The first mixed-file attempt hit provider/credit-reservation errors; its completed sequential retry is the reported probe. Infrastructure errors remain classified separately in the detailed scorecard.

## Reproducibility and validation

[Benchmark specification](benchmark.md) describes licenses, isolation, oracle independence, exact scoring, native paths and commands. [Detailed scorecard](../results/scorecard.md) and [machine-readable results](../results/scorecard.json) retain every experiment, including failures and earlier harness defects. [Experiment links](../results/experiment-links.json) open the selected runs. Raw data, per-run JSONL and complete trace captures remain local and outside Git; full generated outputs and feedback are in LangSmith.

Local validation: 28 tests pass, Ruff and pinned Vulture checks pass, both datasets pass all 16 direct store checks, and Gitleaks 8.30.1 finds no leak in the candidate files. The Docker Python sandbox has no internet, read-only data mounts and resource limits. Native client reads work; ClickHouse and the frozen FerretDB backend reject writes. Garage gives the evaluated agent only a read key. FerretDB 2.7 role declarations alone did not prevent writes; the loader now freezes its PostgreSQL backend and does not leave it writable after loading.

Cost columns include available provider-reported analyst charges, including recovered partial usage from failed historical traces. They exclude judge charges and are not a complete invoice. Missing charges remain unknown. No credits were purchased. All testbed services started for this goal are stopped after verification.

Hosted CI must run on the published head. The workflow runs lint, format, dead-code, tests and the candidate secret scan, without model calls or production deployment. At measurement closeout the local checks had passed; commit/push approval had not yet been requested. [GitHub Actions](https://github.com/IntelIP/BackIntel/actions) holds the hosted result, and Linear owns delivery status.

## Recommended next step

Improve early refusal when required information is absent, then compare the same failed case and a held-out missing-data set. Add a deterministic final report check for duplicate metric IDs and verify every cited program before returning a report. These failures do not justify adding a sub-agent. Production hosting, live scheduling, customer integrations and Infrastructure Engine enrollment remain deferred. Public DABstep/KramaBench comparison is a separate backlog item, not a result claimed here.
