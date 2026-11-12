"""Sandboxed Python for the analyst.

Docker is the required isolation boundary for model-generated code:
no network, read-only root filesystem, memory and CPU caps, the data mounted read-only, and a
hard timeout. There is no host-interpreter fallback.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path

MAX_OUTPUT_CHARS = 12_000
DOCKER_IMAGE = "backintel-sandbox:py312"
DOCKER_MEMORY = "768m"
DOCKER_CPUS = "1.0"


@dataclass
class SandboxResult:
    stdout: str
    stderr: str
    exit_code: int
    elapsed_ms: int
    backend: str
    timed_out: bool = False

    def to_dict(self) -> dict:
        return self.__dict__.copy()


def _clip(text: str) -> str:
    if len(text) <= MAX_OUTPUT_CHARS:
        return text
    return text[: MAX_OUTPUT_CHARS // 2] + "\n…[output clipped]…\n" + text[-MAX_OUTPUT_CHARS // 2 :]


class PythonSandbox:
    def __init__(self, backend: str = "docker", *, timeout_s: int = 120):
        if backend != "docker":
            raise ValueError("Docker is required for model-generated Python; host execution is disabled.")
        self.backend = backend
        self.timeout_s = timeout_s

    @property
    def label(self) -> str:
        return "docker"

    def run(
        self, code: str, *, env: dict[str, str], mounts: dict[str, str], network: str | None = None
    ) -> SandboxResult:
        """Run `code` with `env` set; `mounts` maps host paths to the same path inside (read-only).

        `network` names an internal Docker network that reaches a store container; it never
        reaches the internet (the network is created with `--internal`).
        """
        return self._run_docker(code, env=env, mounts=mounts, network=network)

    def _run_docker(
        self, code: str, *, env: dict[str, str], mounts: dict[str, str], network: str | None
    ) -> SandboxResult:
        if shutil.which("docker") is None:
            raise RuntimeError("Docker is required for model-generated Python; no host fallback is allowed.")
        with tempfile.TemporaryDirectory(prefix="backintel-sbx-") as tmp:
            container_name = f"backintel-sbx-{uuid.uuid4().hex}"
            script = Path(tmp) / "main.py"
            script.write_text(code)
            cmd = [
                "docker",
                "run",
                "--rm",
                "--name",
                container_name,
                "--network",
                network or "none",
                "--read-only",
                "--memory",
                DOCKER_MEMORY,
                "--cpus",
                DOCKER_CPUS,
                "--pids-limit",
                "128",
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges",
                "--tmpfs",
                "/tmp:rw,size=256m",
                "-v",
                f"{tmp}:/work:ro",
                "-w",
                "/work",
            ]
            for host, inside in mounts.items():
                cmd += ["-v", f"{host}:{inside}:ro"]
            for key, value in env.items():
                cmd += ["-e", f"{key}={value}"]
            cmd += [DOCKER_IMAGE, "python", "-I", "/work/main.py"]
            try:
                return self._execute(cmd, label="docker")
            finally:
                # Killing a timed-out Docker CLI does not kill its container. Remove only
                # this invocation's UUID-named container, including on a Python exception.
                subprocess.run(["docker", "rm", "--force", container_name], capture_output=True, timeout=15)

    def _execute(self, cmd: list[str], *, label: str, env=None, cwd=None) -> SandboxResult:
        import time

        started = time.monotonic()
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=self.timeout_s, env=env, cwd=cwd
            )
            return SandboxResult(
                stdout=_clip(proc.stdout),
                stderr=_clip(proc.stderr),
                exit_code=proc.returncode,
                elapsed_ms=int((time.monotonic() - started) * 1000),
                backend=label,
            )
        except subprocess.TimeoutExpired as error:
            return SandboxResult(
                stdout=_clip(error.stdout or "" if isinstance(error.stdout, str) else ""),
                stderr=f"Timed out after {self.timeout_s}s.",
                exit_code=-1,
                elapsed_ms=int((time.monotonic() - started) * 1000),
                backend=label,
                timed_out=True,
            )


def docker_image_available() -> bool:
    if shutil.which("docker") is None:
        return False
    proc = subprocess.run(["docker", "image", "inspect", DOCKER_IMAGE], capture_output=True)
    return proc.returncode == 0


def describe_backend(sandbox: PythonSandbox) -> dict:
    return {
        "backend": sandbox.label,
        "timeout_s": sandbox.timeout_s,
        **(
            {"image": DOCKER_IMAGE, "memory": DOCKER_MEMORY, "cpus": DOCKER_CPUS}
            if sandbox.backend == "docker"
            else {}
        ),
    }


if __name__ == "__main__":  # Manual check: python -m backintel.sandbox
    sb = PythonSandbox(os.environ.get("BACKINTEL_SANDBOX", "docker"))
    print(
        json.dumps(
            sb.run(
                "import sys, polars; print(sys.version); print(polars.__version__)",
                env={},
                mounts={},
            ).to_dict(),
            indent=2,
        )
    )
