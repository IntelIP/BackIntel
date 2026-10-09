"""Download only the explicitly approved, hash-pinned TabICLv2 checkpoints."""
import json
import os
from pathlib import Path

from huggingface_hub import hf_hub_download

from runtime.real_models import CONFIG,_allow_model_use,file_sha,model_root
from runtime.simulation import encoded


def main() -> int:
    config = _allow_model_use("tabiclv2")
    _allow_model_use("catboost")
    directory = model_root()/"Weights"
    directory.mkdir(parents=True,exist_ok=True)
    receipts = []
    for spec in config["tabiclv2"]["checkpoints"].values():
        path = directory/spec["file"]
        if not path.exists():
            downloaded = hf_hub_download(repo_id=config["tabiclv2"]["repository"],filename=spec["file"],
                revision=config["tabiclv2"]["revision"],local_dir=directory,token=False)
            path = Path(downloaded)
        if path.stat().st_size != spec["bytes"] or file_sha(path) != spec["sha256"]:
            raise ValueError("Downloaded checkpoint does not match the approved size/hash")
        path.chmod(0o444)
        receipts.append({**spec,"path":str(path),"license":config["tabiclv2"]["license"],"verified":True})
    result = {"status":"passed","model_execution":"not_yet_run","checkpoints":receipts,"paid_provider_calls":0}
    (model_root()/"download-receipt.json").write_bytes(encoded(result))
    print(json.dumps(result,indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
