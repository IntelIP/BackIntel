# BackIntel — Demo Proof of Concept

BackIntel helps a reviewer inspect an operational finding, check its evidence, and record a decision. This repository contains a runnable recorded demo and the developing analysis system behind it.

**Status: demonstration proof of concept.** The recorded demo uses synthetic business data and saved results. The current analysis workspace uses known dataset formats. Autonomous collection and preparation of unfamiliar data remain future work.

[Try the recorded demo](#try-the-recorded-demo) · [Current capabilities](docs/demo/PoCStatus.txt) · [Architecture](docs/architecture/current-system.md) · [Future product concept](docs/research/autonomous-workflow-concept.txt)

## Try the recorded demo

Requirements: Python 3.10 or later and an unzip utility. From this repository checkout:

```sh
unzip docs/demo/Packages/BackIntelDemoBusinessV4.zip -d /path/to/a/new/demo-folder
cd /path/to/a/new/demo-folder/BackIntelDemo
python3 RunDemo.py --check
python3 RunDemo.py
```

Open <http://127.0.0.1:2053/>. Stop with Ctrl-C. Use `python3 RunDemo.py --port 2054` if that port is occupied. Extract into a new folder to preserve any previous demo reviews.

The package includes the built interface and saved results. It needs no Node installation, database server, model download, provider key, or paid inference. New review notes are saved only inside the extracted copy.

Follow the [five-minute narration](docs/demo/SupportNarration.txt): inspect the original support message, interpretation, prediction comparison, corrected result, and recorded human decision. See [package instructions](docs/demo/DemoPackage.txt) for details.

The archive is a historical recording, with its original source identity and limitations retained in its manifest. Running it does not execute the current analysis engine or prove current live-model performance.

## Choose the right entry point

| Purpose | Entry point | Execution boundary |
| --- | --- | --- |
| Show findings, evidence, and a human decision | Recorded ZIP above | Saved results; no new model calls. |
| Exercise the workflow without external services | `python3 -m scripts.simulate` | Synthetic data and simulated model responses. |
| Develop the current analysis workspace | [`apps/web` runbook](docs/architecture/analysis-workspace-runbook.md) | Local database and workers; hosted analysis requires separate setup and spending authority. |
| Develop the earlier decision-review interface | [`frontend` guide](frontend/README.md) | Local review API; includes an optional Reflex interface. |

The simulation writes reports under `~/Library/Application Support/BackIntel/Evidence/Simulation` by default. Use `--output /absolute/path` to choose another location.

## What is demonstrated

The current source includes saved questions, source permissions, versioned data snapshots, evidence-linked findings, local predictor comparisons, corrections, durable jobs, and recovery checks. Each analysis goal belongs to one domain.

The October 6 consolidation campaign at `8f3cb28` recorded 162 passing Python tests and 50 passing scenarios, with six blocked cases. Four available domains ran real local predictors. Offline workflow checks used simulated analyst responses. These are historical results for that source revision; see [scope and limitations](docs/demo/PoCStatus.txt).

Credit prediction and the five live analyst cases remained blocked. Production readiness, customer accuracy, commercial savings, and complete operating cost are not established.

## Development and validation

Use the [analysis runbook](docs/architecture/analysis-workspace-runbook.md) for local setup and the [benchmark campaign](docs/roadmap/BenchmarkCampaign.txt) for repeatable checks. Dataset files, model weights, credentials, and private run evidence are kept outside tracked source.

GitHub workflows check source, both web interfaces, database behavior, and simulated browser/recovery journeys. A fixture pass does not establish live analyst acceptance.

Demo merges use `tabellio.demo.validation.json`: recorded-package installation, current UI workflows, visual and keyboard checks, recovery, role permissions, budget controls, and actual sandbox isolation. GitHub Codex review must also pass. The unchanged `tabellio.validation.json` preserves full-product acceptance, including actual Jev, CatBoost and TabICLv2 execution; a passing demo is not full-product acceptance.

- [Current repository map](docs/architecture/repository-map.md)
- [Git reconciliation and preserved work](docs/architecture/GitReconciliation.txt)
- [Benchmark methods](docs/research/AnalysisBenchmarkMethods.txt)
- [Historical developer guide](docs/demo/LegacyDeveloperGuide.txt)

## Product direction

The intended product accepts an objective and permitted information, acquires and prepares unfamiliar data in its own workspace, completes the task, and saves a reusable workflow. That broader capability is not implemented by the current demo.

The agreed sequence is to clean up and clarify this proof of concept before expanding. The [saved concept and research](docs/research/autonomous-workflow-concept.txt) records that direction and the remaining gaps.

## License

BackIntel source is licensed under [MIT](LICENSE), copyright 2026 IntelIP. Preserve the recorded package's [dependency and dataset notices](docs/demo/DemoLicensing.txt) when sharing it. Third-party software, models, and services retain their own terms.

[Website and SEO source](https://github.com/IntelIP/BackIntelWebsite)
