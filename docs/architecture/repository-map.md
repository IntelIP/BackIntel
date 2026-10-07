# Current repository map

Start with the [demo PoC README](../../README.md), [capability status](../demo/PoCStatus.txt), and [current architecture](current-system.md). The broader autonomous workflow is a [saved future concept](../research/autonomous-workflow-concept.txt).

## Current entry points

| Surface | Source | Purpose |
| --- | --- | --- |
| Recorded business demo | `docs/demo/Packages/BackIntelDemoBusinessV4.zip` | Shareable saved-result walkthrough; no new inference. |
| Current analysis workspace | `apps/web`, `runtime/analysis_api.py`, `runtime/analysis_agent.py` | Saved goals, bounded tools, findings, and evidence. |
| Data preparation and predictors | `runtime/analysis_data.py`, `runtime/analysis_models.py` | Known-domain adapters and local model comparisons. |
| Persistence and execution | `runtime/analysis_store.py`, `runtime/analysis_service.py`, `runtime/jobs.py`, `runtime/evidence.py` | Permissions, snapshots, durable work, recovery, and usage records. |
| Analysis runtime | `compose.analysis.yml`, `aegra.analysis.json` | Local PostgreSQL, Redis, and Aegra/LangGraph workers. |
| Benchmark campaign | `scripts/validation/benchmark_campaign.py`, `config/analysis_scenarios.json` | Separate offline, real-prediction, and real-analyst evidence. |

## Preserved proof-of-concept components

| Surface | Source | Boundary |
| --- | --- | --- |
| Earlier review interfaces | `frontend`, `reflex_demo`, `runtime/decision_workspace.py` | Review findings and preserve human decisions. |
| Capability simulation | `runtime/simulation.py`, `scripts/simulate.py`, `config/simulation` | Explicitly synthetic scenarios and simulated interpretation. |
| Capability jobs and model stages | `runtime/capability_pipeline.py`, `runtime/capability_graph.py`, `runtime/real_pipeline.py` | Earlier staged workflows; real and fixture evidence stay distinct. |
| Local predictors and Jev integration | `runtime/real_models.py`, `runtime/real_semantics.py`, `runtime/jev.py` | Local predictor execution and separately authorized hosted interpretation. |
| Report packaging | `runtime/artifacts.py`, `runtime/audience_server.py`, `scripts/package_capabilities.py` | Scoped reports, evidence, and review actions. |
| Generated report layouts | `runtime/generated_artifacts.py`, `runtime/sandbox.py` | Isolated execution of bounded candidates; demo code generation is simulated. |
| Original Olist example | `runtime/olist*.py`, `scripts/data`, earlier architecture notes | Historical code/contracts retained; OlistV2 data remains removed. |

Historical commands and earlier runtime claims are preserved in the [legacy developer guide](../demo/LegacyDeveloperGuide.txt). They do not describe current installed services. The [Git reconciliation](GitReconciliation.txt) records recovery boundaries and retained checkouts.

The existing presentation uses readable tables, explicit caveats, and source links. Keep those features when changing the interface. No older benchmark, screenshot, or model receipt establishes acceptance of a new source revision.
