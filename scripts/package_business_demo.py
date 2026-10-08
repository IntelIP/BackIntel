"""Package and serve a recorded business run. Default playback uses only stdlib."""
from __future__ import annotations

import argparse
from contextlib import closing
import hashlib
import json
import mimetypes
from pathlib import Path
import shutil
import sqlite3
import subprocess
import tempfile
from urllib.parse import unquote, urlsplit
import zipfile

from runtime.decision_workspace import DecisionStore, WorkspaceHandler, WorkspaceServer

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def backup_reviews(source, target):
    with closing(sqlite3.connect(f"file:{source}?mode=ro", uri=True)) as original, closing(sqlite3.connect(target)) as copied:
        original.backup(copied)
        copied.execute("PRAGMA journal_mode=DELETE")


def verify(root):
    manifest = json.loads((root / "Manifest.json").read_text())
    expected = {item['path'] for item in manifest['files']}
    actual = {path.relative_to(root).as_posix() for path in root.rglob('*')
              if path.is_file() and path.relative_to(root).parts[0] != '.demo-state'
              and path.relative_to(root).as_posix() != 'Manifest.json'}
    if actual != expected:
        raise ValueError('Package file set differs from its manifest')
    for item in manifest["files"]:
        path = (root / item["path"]).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file() or sha(path) != item["sha256"]:
            raise ValueError(f"Package file is missing or changed: {item['path']}")
    packet = json.loads((root / "Records/Workspace.json").read_text())
    if packet["demo"]["status"] != "completed" or packet["demo"]["demo_id"] != manifest["demo_id"]:
        raise ValueError("Package does not contain the completed named run")
    return manifest


class RecordedHandler(WorkspaceHandler):
    def do_GET(self):
        path = unquote(urlsplit(self.path).path)
        if path.startswith("/api/"):
            return super().do_GET()
        if not self.allowed():
            return
        target = (self.server.static_root / (path.lstrip("/") or "index.html")).resolve()
        if not target.is_relative_to(self.server.static_root) or not target.is_file():
            return self.send_json(404, {"error": "Not found"})
        body = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mimetypes.guess_type(target.name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


def server(root, port):
    verify(root)
    state = root / ".demo-state"
    state.mkdir(exist_ok=True)
    database = state / "Reviews.sqlite3"
    if not database.exists():
        shutil.copyfile(root / "Records/ReviewsSeed.sqlite3", database)
    packet_path = root / "Records/Workspace.json"
    packet = json.loads(packet_path.read_text())
    store = DecisionStore(database, packet["cases"], packet_path)
    api = WorkspaceServer(store, packet["source_mode"], port,
                          additional_origins={f"http://localhost:{port}", "http://127.0.0.1:3003", "http://localhost:3003"})
    api.static_root = (root / "Frontend").resolve()
    api.RequestHandlerClass = RecordedHandler
    return api


def build(root, demo_id, destination):
    run = root / "artifacts/validation/BusinessDemo" / demo_id
    packet = json.loads((run / "Workspace.json").read_text())
    validation = json.loads((run / "Validation.json").read_text())
    if packet["demo"]["status"] != "completed" or validation["business_demo_status"] != "passed":
        raise ValueError("Only a verified completed business run can be packaged")
    receipt_path = Path(validation["workflow_receipt"])
    receipt = json.loads(receipt_path.read_text())
    if receipt["status"] != "passed" or receipt["paid_provider_calls"] != 54:
        raise ValueError("The retained actual-provider receipt is incomplete")
    if not (root / "frontend/dist/index.html").is_file():
        raise ValueError("Build the existing frontend before packaging")
    destination.mkdir(parents=True, exist_ok=True)
    archive = destination / "BackIntelDemoBusinessV4.zip"
    with tempfile.TemporaryDirectory(prefix="BackIntelDemo") as temporary:
        package = Path(temporary) / "BackIntelDemo"
        records = package / "Records"
        records.mkdir(parents=True)
        packet["demo"]["boundaries"].append("Recorded playback: this package opens saved results and makes no new model calls.")
        (records / "Workspace.json").write_text(json.dumps(packet, indent=2) + "\n")
        backup_reviews(run / "Reviews.sqlite3", records / "ReviewsSeed.sqlite3")
        shutil.copyfile(run / "AuthorizationScopes.json", records / "Inputs.json")
        for name in ("Validation.json", "Replay.json", "Budget.json", "NumericRoundingChecks.json", "ResumeApproval.json", "AuthorizationClosure.Resumed.json", "ReactInterpretationRunning.png", "ReactReviewed.png", "ReflexReviewed.png"):
            shutil.copyfile(run / name, records / name)
        shutil.copyfile(receipt_path, records / "Integration.json")
        shutil.copytree(receipt_path.parent / "Package", records / "ExecutionPackage")
        shutil.copytree(root / "frontend/dist", package / "Frontend")
        for relative in ("runtime/decision_workspace.py", "scripts/package_business_demo.py"):
            target = package / relative
            target.parent.mkdir(exist_ok=True)
            shutil.copyfile(root / relative, target)
        for name in ("runtime", "scripts"):
            (package / name / "__init__.py").write_text("")
        (package / "RunDemo.py").write_text("import sys\nsys.dont_write_bytecode = True\nfrom scripts.package_business_demo import main\nmain()\n")
        shutil.copytree(run / "ReflexApp/reflex_demo", package / "PythonDemo/reflex_demo", ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(run / "ReflexApp/assets", package / "PythonDemo/assets")
        shutil.copyfile(root / "reflex_demo/requirements.txt", package / "PythonDemo/requirements.txt")
        (package / "PythonDemo/rxconfig.py").write_text('import reflex as rx\nconfig = rx.Config(app_name="reflex_demo", frontend_port=3003, backend_port=3003, api_url="http://127.0.0.1:3003", backend_host="127.0.0.1", show_built_with_reflex=False)\n')
        narration = (root / "docs/demo/SupportNarration.txt").read_text()
        for original, packaged in ((5174, 2053), (3002, 3003), (2043, 2053)):
            narration = narration.replace(f"http://127.0.0.1:{original}/", f"http://127.0.0.1:{packaged}/")
        narration = narration.replace("artifacts/validation/RealDemo/business-v4/Attemptc605b91b38e3/Package/", "Records/ExecutionPackage/")
        narration = narration.replace("artifacts/validation/RealDemo/business-v4/Attemptc605b91b38e3/", "Records/")
        narration = narration.replace("artifacts/validation/BusinessDemo/business-v4/", "Records/")
        (package / "SupportNarration.txt").write_text(narration)
        shutil.copyfile(root / "docs/demo/DemoPackage.txt", package / "StartHere.txt")
        shutil.copyfile(root / "docs/demo/DemoLicensing.txt", package / "Licensing.txt")
        shutil.copyfile(root / "LICENSE", package / "LICENSE")
        paths = subprocess.run(["git", "ls-files", "--cached"], cwd=root, check=True, capture_output=True, text=True).stdout.splitlines()
        for relative in paths:
            path = root / relative
            if (path.is_file() and not path.is_symlink() and
                    (relative.split("/")[0] in {"runtime", "scripts", "tests", "schemas", "frontend", "reflex_demo"} or
                     ("/" not in relative and (path.name == "LICENSE" or path.suffix in {".txt", ".json", ".yml", ".yaml", ".toml", ".md"})))):
                target = package / "SourceSnapshot" / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, target)
        lock = json.loads((root / "frontend/package-lock.json").read_text())
        notices = []
        for relative, info in lock["packages"].items():
            if not relative:
                continue
            notices.append({"package": relative.removeprefix("node_modules/"), "version": info.get("version"), "license": info.get("license", "Not declared in lockfile")})
            directory = root / "frontend" / relative
            for pattern in ("LICENSE*", "LICENCE*", "COPYING*", "NOTICE*", "OFL*"):
                for path in directory.glob(pattern):
                    if path.is_file() and not path.is_symlink():
                        target = package / "DependencyLicenses" / relative.removeprefix("node_modules/") / path.name
                        target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copyfile(path, target)
        (package / "DependencyLicenses.json").write_text(json.dumps(notices, indent=2) + "\n")
        files = [{"path": str(p.relative_to(package)), "sha256": sha(p), "bytes": p.stat().st_size}
                 for p in sorted(package.rglob("*")) if p.is_file()]
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True).stdout.strip()
        manifest = {"schema": "backintel-recorded-demo-package/v1", "demo_id": demo_id, "mode": "recorded_synthetic_run", "new_provider_calls": 0,
                    "base_head": head, "candidate": "uncommitted-working-tree", "exact_commit_product_readiness": "blocked", "files": files}
        (package / "Manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        verify(package)
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zipped:
            for path in sorted(package.rglob("*")):
                if path.is_file():
                    zipped.write(path, str(path.relative_to(package.parent)))
    (destination / "PackageReceipt.json").write_text(json.dumps({"status": "passed", "archive": archive.name, "archive_sha256": sha(archive), "mode": "recorded_synthetic_run", "files": len(files), "new_provider_calls": 0, "exact_commit_product_readiness": "blocked"}, indent=2) + "\n")
    return archive


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--demo-id", default="business-v4")
    parser.add_argument("--output", type=Path, default=ROOT / "docs/demo/Packages")
    parser.add_argument("--port", type=int, default=2053)
    args = parser.parse_args()
    if args.demo_id != "business-v4" or not 1 <= args.port <= 65535:
        parser.error("This package owns business-v4; use a valid local port")
    if args.build:
        print(build(ROOT, args.demo_id, args.output))
    elif args.check:
        manifest = verify(ROOT)
        print(json.dumps({"status": "passed", "files": len(manifest["files"]), "new_provider_calls": 0}))
    else:
        api = server(ROOT, args.port)
        print(f"Recorded demo: http://127.0.0.1:{api.server_port}/ · no new model calls", flush=True)
        try:
            api.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            api.server_close()


if __name__ == "__main__":
    main()
