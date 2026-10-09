"""Host-side runner for generated Python; never mount Docker access into workers."""

from __future__ import annotations

import json
import os
from pathlib import Path
import selectors
import subprocess
import tempfile
import time
import uuid

from runtime.simulation import digest, encoded

LIMITS = {"seconds": 5, "memory_bytes": 268435456, "cpus": 1,
          "processes": 32, "output_bytes": 32768, "input_bytes": 131072,
          "source_bytes": 32768, "temporary_bytes": 16777216}


def resolve_image(image: str) -> str:
    resolved = subprocess.run(["docker", "image", "inspect", image, "--format", "{{.Id}}"],
                              check=True, capture_output=True, text=True, timeout=10).stdout.strip()
    if not resolved.startswith("sha256:") or len(resolved) != 71:
        raise ValueError("Sandbox requires an existing immutable local image")
    return resolved


def run_candidate(source: str, snapshot: dict, image: str) -> dict:
    """Return an untrusted JSON candidate and a review receipt. Never publish it."""
    if not isinstance(snapshot, dict) or len(encoded(snapshot)) > LIMITS["input_bytes"]:
        raise ValueError("Approved input snapshot exceeds sandbox contract")
    if not isinstance(source, str) or len(source.encode()) > LIMITS["source_bytes"]:
        raise ValueError("Generated source exceeds sandbox contract")
    resolved = resolve_image(image)
    name = "backintel-sandbox-" + uuid.uuid4().hex
    started = time.monotonic()
    receipt = {"schema": "backintel-sandbox-run/v1", "image": resolved, "limits": LIMITS,
               "source": source, "source_sha256": digest(source), "input_sha256": digest(snapshot),
               "status": "rejected", "review": "not_reviewed", "network": "none",
               "host_mounts": "generated source and approved snapshot only", "result": None}
    with tempfile.TemporaryDirectory(prefix="BackIntelSandbox") as temporary:
        root = Path(temporary)
        root.chmod(0o755)
        (root / "source").mkdir(mode=0o755)
        (root / "input").mkdir(mode=0o755)
        script = root / "source/code.py"
        inputs = root / "input/snapshot.json"
        script.write_text(source)
        inputs.write_bytes(encoded(snapshot))
        script.chmod(0o444)
        inputs.chmod(0o444)
        command = ["docker", "run", "--pull=never", "--name", name, "--rm",
                   "--network=none", "--read-only", "--user=65534:65534",
                   "--cap-drop=ALL", "--security-opt=no-new-privileges",
                   "--memory=256m", "--memory-swap=256m", "--cpus=1", "--pids-limit=32",
                   "--ulimit=nofile=64:64", "--ulimit=fsize=1048576:1048576",
                   "--tmpfs=/tmp:rw,nosuid,nodev,noexec,size=16m,mode=1777",
                   "--tmpfs=/app:ro,nosuid,nodev,noexec,size=1m",
                   "--workdir=/tmp", "--env=PYTHONDONTWRITEBYTECODE=1",
                   "--mount", f"type=bind,source={root / 'source'},target=/candidate,readonly",
                   "--mount", f"type=bind,source={root / 'input'},target=/input,readonly",
                   "--entrypoint=python", resolved, "-I", "-B", "-u", "/candidate/code.py"]
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        streams = {"stdout": bytearray(), "stderr": bytearray()}
        reason = None
        try:
            with selectors.DefaultSelector() as selector:
                for label, stream in (("stdout", process.stdout), ("stderr", process.stderr)):
                    os.set_blocking(stream.fileno(), False)
                    selector.register(stream, selectors.EVENT_READ, label)
                deadline = time.monotonic() + LIMITS["seconds"]
                while selector.get_map():
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        reason = "time_limit"
                        break
                    for key, _ in selector.select(min(remaining, .1)):
                        chunk = os.read(key.fileobj.fileno(), 4096)
                        if not chunk:
                            selector.unregister(key.fileobj)
                            continue
                        capacity = LIMITS["output_bytes"] - sum(len(v) for v in streams.values())
                        streams[key.data].extend(chunk[:capacity])
                        if len(chunk) > capacity:
                            reason = "output_limit"
                            break
                    if reason:
                        break
                if reason is None:
                    process.wait(timeout=max(.01, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            reason = "time_limit"
        finally:
            # Stop the attached client first: unread output can block Docker teardown.
            # The named container still needs explicit removal below.
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)
            try:
                cleanup = subprocess.run(["docker", "rm", "--force", name], capture_output=True, timeout=10)
                receipt["cleanup_confirmed"] = cleanup.returncode == 0 or b"No such container" in cleanup.stderr
                if not receipt["cleanup_confirmed"]:
                    receipt["cleanup_error"] = cleanup.stderr.decode('utf-8', errors='replace')[:1000]
            except (OSError, subprocess.TimeoutExpired) as error:
                receipt["cleanup_confirmed"] = False
                receipt["cleanup_error"] = str(error)[:1000]
            finally:
                if process.poll() is None:
                    process.kill()
                process.wait(timeout=5)
                process.stdout.close()
                process.stderr.close()
        receipt.update(stdout=streams["stdout"].decode("utf-8", errors="replace"),
                       stderr=streams["stderr"].decode("utf-8", errors="replace"),
                       returncode=process.returncode, wall_seconds=time.monotonic() - started)
        if not receipt["cleanup_confirmed"]:
            reason = "cleanup_unconfirmed"
        if reason is None and process.returncode != 0:
            reason = "process_failed"
        if reason is None:
            try:
                result = json.loads(receipt["stdout"], parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
                if not isinstance(result, dict):
                    raise ValueError("Candidate must return a JSON object")
                receipt.update(status="candidate", result=result)
            except (ValueError, RecursionError):
                reason = "invalid_output"
        receipt["stop_reason"] = reason
    return receipt
