"""Sandboxed Python for the analyst.

SmolVM is the required isolation boundary for model-generated code. The shared runtime
enforces offline networking, read-only source mounts, resource caps and a hard timeout.
"""

from __future__ import annotations

from dataclasses import dataclass

MAX_OUTPUT_CHARS = 12_000
DOCKER_IMAGE = "backintel-sandbox:py312"


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
    def __init__(self, backend: str = "smolvm", *, timeout_s: int = 120):
        if backend != "smolvm":
            raise ValueError("SmolVM is required for model-generated Python; host execution is disabled.")
        self.backend = backend
        self.timeout_s = timeout_s

    @property
    def label(self) -> str:
        return "smolvm"

    def run(
        self, code: str, *, env: dict[str, str], mounts: dict[str, str], network: str | None = None
    ) -> SandboxResult:
        # Import lazily: both sandbox entry points share the result contract in this module.
        from backintel.analysis_sandbox import AnalysisSandbox, ResourceProfile

        profile = ResourceProfile(
            memory_mib=768,
            cpus=1,
            workspace_mib=128,
            artifacts_mib=64,
            temporary_mib=128,
            command_timeout_s=self.timeout_s,
            run_timeout_s=self.timeout_s,
            max_commands=1,
        )
        with AnalysisSandbox(env=env, mounts=mounts, network=network, profile=profile) as sandbox:
            return sandbox.run_python(code)


def describe_backend(sandbox: PythonSandbox) -> dict:
    return {
        "backend": sandbox.label,
        "timeout_s": sandbox.timeout_s,
        "memory": "768m",
        "cpus": "1",
        "runtime_version": "1.31.1",
    }
