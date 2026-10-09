# Source this after activating Python and binding PostgreSQL/Redis.
# Preserve secrets supplied by environment configuration; no credential files are read.
export BACKINTEL_DATASET_DIR="${BACKINTEL_DATASET_DIR:-/workspace/backintel-cloud/live-campaign/Datasets}"
export BACKINTEL_MODEL_DIR="${BACKINTEL_MODEL_DIR:-/workspace/backintel-cloud/live-campaign/Models}"
export BACKINTEL_ACCESS_CREDENTIAL_FILE="${BACKINTEL_ACCESS_CREDENTIAL_FILE:-/workspace/backintel-cloud/live-campaign/credentials/access.json}"
export BACKINTEL_AEGRA_URL="${BACKINTEL_AEGRA_URL:-http://127.0.0.1:2028}"
export OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 HF_HUB_OFFLINE=1
