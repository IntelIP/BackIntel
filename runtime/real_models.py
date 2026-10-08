"""Actual CatBoost and TabICLv2 implementations. Checkpoints never auto-download."""
from __future__ import annotations

from functools import lru_cache
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import statistics
import tempfile
import time

from runtime.simulation import digest, encoded

CONFIG = Path(__file__).resolve().parents[1] / "config" / "real_models.json"


def model_root() -> Path:
    value = os.environ.get("BACKINTEL_MODEL_DIR")
    if not value:
        raise RuntimeError("Real models require an explicit local model-artifact directory")
    return Path(value).resolve()


def file_sha(path: Path) -> str:
    checksum = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda:stream.read(1024*1024),b""):
            checksum.update(block)
    return checksum.hexdigest()


def versions() -> dict:
    return {name:version(name) for name in ("catboost","tabicl","torch","scikit-learn","numpy")}


def checkpoint(kind: str) -> tuple[Path,dict]:
    config = json.loads(CONFIG.read_text())
    spec = config["tabiclv2"]["checkpoints"][kind]
    path = model_root() / "Weights" / spec["file"]
    if not path.is_file():
        raise RuntimeError("Approved TabICLv2 checkpoint has not been downloaded")
    if path.resolve().parent != (model_root()/"Weights").resolve() or file_sha(path) != spec["sha256"]:
        raise ValueError("TabICLv2 checkpoint identity does not match the pinned model")
    return path,spec


def matrix(records: list[dict], columns: list[str]):
    import numpy as np
    return np.array([[float("nan") if r["body"]["values"][c] is None else r["body"]["values"][c] for c in columns] for r in records],dtype=float)


def _tabicl(kind: str, path: Path):
    import torch
    from tabicl import TabICLClassifier,TabICLRegressor
    torch.set_num_threads(2)
    cls = TabICLClassifier if kind == "classification" else TabICLRegressor
    parameters = json.loads(CONFIG.read_text())["tabiclv2"]["parameters"]
    return cls(model_path=str(path),allow_auto_download=False,**parameters)


def _allow_model_use(route: str) -> dict:
    config = json.loads(CONFIG.read_text())
    approval_path = model_root()/"model-use-approval.json"
    if not approval_path.is_file():
        raise PermissionError("Actual model execution requires explicit local model-use approval")
    approval = json.loads(approval_path.read_text())
    if approval.get("approved") is not True or approval.get("configuration_sha256") != digest(config) or route not in approval.get("routes",[]):
        raise PermissionError("Model-use approval does not match the pinned configuration")
    return config


def prepare_real(store, task_record: dict, training: list[dict], route: str, feature_set: str, at: int) -> dict:
    if route not in ("catboost","tabiclv2"):
        raise ValueError("Unsupported actual predictor implementation")
    config = _allow_model_use(route)
    if len(training) > config["limits"]["max_training_rows"]:
        raise ValueError("Real model training/context row budget exceeded")
    if feature_set == "semantic":
        expected = {q["id"] for q in task_record["body"]["questions"]}
        if task_record["body"]["observation_provider"]["implementation_mode"] != "real":
            raise ValueError("Final semantic-feature model preparation requires actual Jev findings")
        for case in training:
            observations = [r for r in store.lineage(case["feature"]["sha256"]) if r["kind"] == "observation"]
            if {r["body"]["question_id"] for r in observations} != expected or any(r["body"]["provider"]["implementation_mode"] != "real" or not r["body"].get("request_id") for r in observations):
                raise ValueError("Final semantic-feature model preparation requires actual Jev findings")
    columns = sorted(c for c in training[0]["feature"]["body"]["values"] if feature_set == "semantic" or c.startswith("structured:"))
    libraries = versions()
    implementation = file_sha(Path(__file__))
    key = digest({"task":task_record["sha256"],"training":[[r["feature"]["sha256"],r["outcome"]["sha256"]] for r in training],
                  "route":route,"feature_set":feature_set,"at":at,"implementation_mode":"real","libraries":libraries,"config":config,
                  "implementation_sha256":implementation})
    with store.connection.transaction():
        store.lock()
        existing = store.find("model",key)
        if existing:
            return existing
        root = model_root()
        root.mkdir(parents=True,exist_ok=True)
        package = root/key
        if package.exists():
            body = json.loads((package/"manifest.json").read_text())
            if file_sha(package/body["artifact"]["file"]) != body["artifact"]["sha256"]:
                raise ValueError("Prepared model package was modified")
        else:
            started = time.perf_counter()
            x = matrix([r["feature"] for r in training],columns)
            y = [r["outcome"]["body"]["value"] for r in training]
            kind = task_record["body"]["target"]["kind"]
            with tempfile.TemporaryDirectory(prefix="Preparing",dir=root) as directory:
                staging = Path(directory)
                weights = None
                if route == "catboost":
                    from catboost import CatBoostClassifier,CatBoostRegressor
                    cls = CatBoostClassifier if kind == "classification" else CatBoostRegressor
                    estimator = cls(**config["catboost"]["parameters"])
                    estimator.fit(x,y)
                    artifact = staging/"model.cbm"
                    estimator.save_model(str(artifact))
                else:
                    path,weights = checkpoint(kind)
                    estimator = _tabicl(kind,path)
                    estimator.fit(x,y)
                    artifact = staging/"context.json"
                    artifact.write_bytes(encoded({"columns":columns,"features":[[r["feature"]["body"]["values"][c] for c in columns] for r in training],"outcomes":y}))
                scales = {}
                for column in columns:
                    values = [r["feature"]["body"]["values"][column] for r in training if r["feature"]["body"]["values"][column] is not None]
                    scales[column] = {"mean":statistics.mean(values) if values else 0.,"std":statistics.pstdev(values) if values else 0.,
                                      "min":min(values) if values else 0.,"max":max(values) if values else 0.}
                body = {"task":task_record["sha256"],"route":route,"feature_set":feature_set,"adapter_version":"real-v1",
                        "implementation_mode":"real","preparation":"trained_catboost" if route == "catboost" else "tabiclv2_context",
                        "columns":columns,"scales":scales,"target":task_record["body"]["target"],"prepared_at":at,"training_count":len(training),
                        "training_matrix_sha256":digest([[r["feature"]["sha256"],r["outcome"]["sha256"]] for r in training]),
                        "libraries":libraries,"configuration_sha256":digest(config),"checkpoint":weights,"implementation_sha256":implementation,
                        "artifact":{"package":key,"file":artifact.name,"sha256":file_sha(artifact)},
                        "wall_ms":(time.perf_counter()-started)*1000,"prepared_bytes":artifact.stat().st_size,
                        "provider_calls":0,"measured_provider_usd":0,"local_compute_usd":None,
                        "parameters":config[route]["parameters"]}
                (staging/"manifest.json").write_bytes(encoded(body))
                staging.rename(package)
        return store.put("model",key,body,at,[task_record["sha256"],*[r[k]["sha256"] for r in training for k in ("feature","outcome")]])


@lru_cache(maxsize=2)
def _load(root_value: str, model_json: str):
    model = json.loads(model_json)
    if model.get('implementation_sha256') != file_sha(Path(__file__)):
        raise ValueError('Predictor implementation differs from prepared package; prepare it again')
    if model["libraries"] != versions():
        raise ValueError("Installed predictor libraries differ from the prepared package")
    root = Path(root_value)
    artifact = root/model["artifact"]["package"]/model["artifact"]["file"]
    if not artifact.resolve().is_relative_to(root) or file_sha(artifact) != model["artifact"]["sha256"]:
        raise ValueError("Model artifact identity mismatch")
    kind = model["target"]["kind"]
    if model["route"] == "catboost":
        from catboost import CatBoostClassifier,CatBoostRegressor
        estimator = (CatBoostClassifier if kind == "classification" else CatBoostRegressor)()
        estimator.load_model(str(artifact))
    else:
        import numpy as np
        path,spec = checkpoint(kind)
        if spec != model["checkpoint"]:
            raise ValueError("Prepared TabICLv2 checkpoint changed")
        context = json.loads(artifact.read_text())
        estimator = _tabicl(kind,path)
        estimator.fit(np.array([[float("nan") if v is None else v for v in row] for row in context["features"]]),context["outcomes"])
    return estimator


def predict_real(model: dict, feature: dict) -> float:
    body = model["body"]
    _allow_model_use(body["route"])
    estimator = _load(str(model_root()),json.dumps(body,sort_keys=True))
    values = matrix([feature],body["columns"])
    if body["target"]["kind"] == "classification":
        classes = list(estimator.classes_)
        if 1 not in classes:
            return 0.
        kwargs = {"thread_count":2} if body["route"] == "catboost" else {}
        return float(estimator.predict_proba(values,**kwargs)[0][classes.index(1)])
    kwargs = {"thread_count":2} if body["route"] == "catboost" else {}
    return float(estimator.predict(values,**kwargs)[0])
