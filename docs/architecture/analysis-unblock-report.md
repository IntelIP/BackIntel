# BackIntel setup and benchmark unblocking

The owner authorized the setup/access changes and use of all five named datasets for benchmark and testing. The $10 cumulative new-provider budget remains in force. These changes are local; no public push, publication, deployment, or model promotion occurred.

The existing cloud configuration tool exposes status only. Current revision 9 enforces restricted egress with the package-manager preset and has no secret bindings. Probes reach the IBM publication on `raw.githubusercontent.com`; Kaggle, Hugging Face, and OpenRouter receive proxy CONNECT 403 denials. Approval in chat does not change that policy or inject the existing secret.

## Changes completed

- Replaced the machine-specific dataset mount in Compose with configurable paths and passed the environment-injected analyst credential to the runtime.
- Added configured credential-file paths and Linux provisioning that uses the environment binding. Mac Keychain provisioning remains available on macOS. Updated this cloud's activation helper to preserve an injected OpenRouter key.
- Added atomic ZIP/directory/file dataset imports, including existing Home Credit files. Inputs are validated before publication, fingerprinted, and accompanied by source/provenance receipts. Unsafe archive paths, duplicates, symlinks, extraction-budget violations, HTML responses, and Git LFS pointers are rejected. Existing differing datasets are preserved.
- Added pinned TabICLv2 acquisition and hash-checked local checkpoint imports, plus receipt-checked imports of an existing pinned Decide package. No command performs competition-account rule acceptance.
- Made benchmark service URLs and output/credential paths configurable, bounded event-stream waits, accepted the owner-authorized Home Credit import receipt, and redacted benchmark error details.
- Fixed whitespace-only numeric missing values found in the actual IBM Telco data. Unknown Telco outcome labels now fail validation rather than silently becoming negative outcomes.
- Added a separate actual baseline/CatBoost runner. It checks labels, contracts, entity partitions, Brier scores, and model-restored predictions against the raw original file. Its evidence is explicitly partial and is never added as an approved runtime candidate.

## What the owner must do

1. In this cloud environment's configuration, keep the package-manager preset and add the destinations in `config/analysis-cloud-access.json`. The initial hosts cover Kaggle, its Google Storage downloads, Hugging Face and common checkpoint artifact hosts, and OpenRouter. Additional approved artifact redirect hosts may be needed. This JSON is a request, not an effective policy. Apply the configuration through the environment workflow/UI; editing `/etc/codex/network-policy.json` cannot grant access.
2. In that environment's **Secrets**, inject the existing credential as **`OPENROUTER_API_KEY`**. The value belongs in Secrets, never in chat, a command argument, this repository, or a report. No new provider-account creation or higher budget is required.
3. For **Home Credit**, supply an existing ZIP or directory containing **`application_train.csv` and `bureau.csv`**, or make an account with existing competition access available for download. The importer avoids the Kaggle login requirement when files already exist. The three other missing datasets can be downloaded after egress is enabled or imported from existing files; Telco is already available.

The applicable cloud runtime skill explicitly says: “Configuration changes require the environment configuration workflow and its user review.” See [the skill](skill://plugin_connector_1p_c5b7d5df5d7081918f2c4be5a633ed5d/cloud-environment-runtime/SKILL.md). The request above is already authorized; applying the configuration and binding the actual secret require the user-accessible workflow because no configuration-write tool is exposed here.

## Commands already prepared

From the analysis checkout, activate the configured cloud environment and select the dataset/model directories:

```bash
cd /workspace/BackIntel-analysis
source /workspace/backintel-cloud/activate.sh
source scripts/analysis_env.sh
python -m scripts.analysis_setup preflight --probe --output /workspace/backintel-cloud/live-campaign/preflight.json
```

This preflight makes no inference calls and reports only secret-binding presence, never credential contents. A reachable host or present environment binding does not prove authenticated model access.

The pinned IBM Telco publication can be reproduced without Kaggle:

```bash
python -m scripts.analysis_setup published --domain churn
python -m pip install -r requirements.analysis-local.txt
python -m scripts.analysis_local_benchmark --output /workspace/backintel-cloud/live-campaign/telco-next-run
```

Use a new output directory for each benchmark so earlier failures and receipts are preserved. The default `BACKINTEL_MODEL_DIR/LocalBenchmarks/telco` also requires a new directory.

Import already downloaded data, including Home Credit, without a network request:

```bash
python -m scripts.analysis_setup import-data --domain credit --input /absolute/path/to/home-credit-default-risk.zip
python -m scripts.analysis_setup import-data --domain support --input /absolute/path/to/synthetic_it_support_tickets.csv
python -m scripts.analysis_setup import-data --domain commerce --input '/absolute/path/to/Womens Clothing E-Commerce Reviews.csv'
python -m scripts.analysis_setup import-data --domain maintenance --input /absolute/path/to/CMAPSSData
```

The maintenance directory must contain `train_FD001.txt`, `test_FD001.txt`, and `RUL_FD001.txt`. Alternatively pass a ZIP containing the expected files. Imports record the owner's benchmark authorization and file hashes; they do not certify an independently unverified original-download identity. Do not replace the existing dataset directory with a different copy during a run. Select another `BACKINTEL_DATASET_DIR` to compare a changed source.

Once network access is applied, the remaining noncompetition datasets and approved weights can be acquired with the prepared commands:

```bash
python -m scripts.analysis_demo acquire --domain commerce --acknowledge-terms
python -m scripts.analysis_demo acquire --domain support --acknowledge-terms
python -m scripts.analysis_demo acquire --domain maintenance --acknowledge-terms
python -m pip install -r requirements.analysis-models.txt
python -m scripts.analysis_setup download-weights --kind classification
python -m scripts.analysis_setup download-weights --kind regression
python -m scripts.analysis_setup download-weights --kind decide
```

Existing checkpoint/model files avoid Hugging Face downloads:

```bash
python -m scripts.analysis_setup import-weights --kind classification --input /absolute/path/to/tabicl-classifier-v2-20260212.ckpt
python -m scripts.analysis_setup import-weights --kind regression --input /absolute/path/to/tabicl-regressor-v2-20260212.ckpt
python -m scripts.analysis_setup import-weights --kind decide --input /absolute/path/to/Decide
```

TabICLv2 imports require the approved size and SHA-256. Decide imports require its original `backintel-weights.json`, approved revision, complete config/tensor package, and matching file hashes. Receipt verification is weaker than independent publisher verification; full actual model execution remains necessary.

For the isolated Compose runtime, set the dataset/model paths but leave the host `BACKINTEL_ACCESS_CREDENTIAL_FILE` unset before the Mac launcher uses Docker's tmpfs credentials. For a host Python runtime, retain the configured access file and set `BACKINTEL_AEGRA_URL` to its local API. Follow the existing runbook to create the isolated database, bootstrap, seed access, and start Aegra. The supplied cloud activation helper binds the earlier legacy databases; do not launch the analysis API against those without setting its isolated database URL. Build the frontend before starting any browser checks and keep the built assets stable while the API is running.

## Actual Telco evidence and limits

The file comes from IBM's repository at commit `d5371f5d83a446ad5673cbcca3b814b926491f8a`, with Git blob `3de7a612d1609f25f21a455bda77948729369002` and SHA-256 `16320c9c1ec72448db59aa0a26a0b95401046bef5d02fd3aeb906448e3055e91`. It has 7,043 records, 21 columns, and 1,869 positive labels. Its pinned IBM publication identity is verified; byte identity with a Kaggle archive is unverified.

The fixed held-out comparison uses 512 training, 128 calibration, and 256 test records, with no entity overlap. Test Brier score is about **0.1249** for CatBoost versus **0.1757** for the constant training-prevalence baseline; CatBoost ROC AUC is about **0.8469**. These are descriptive results for this frozen, bounded cohort, with no claimed causal effect or uncertainty estimate. Original-label and restored-model checks pass.

Actual local work incurred **$0 provider spend**. Local compute cost is unpriced, not asserted to be zero. TabICLv2, Decide, hosted analyst correctness, and the full five-domain live campaign remain incomplete. The prior fixture campaign's five-domain browser, recovery, budget, and permission evidence stays available as separate historical evidence.

Receipts and regression results from this follow-up are under `/workspace/backintel-cloud/unblock-campaign/`. The final exact-commit receipt records a clean candidate; working-run receipts retain their dirty-tree status. Alternate clothing/support copies and LFS-only maintenance paths were inspected and excluded rather than admitted as the named originals.
