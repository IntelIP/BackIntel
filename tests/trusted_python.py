"""Host execution for fixed, repository-owned test fixtures only; never shipped in the package."""

import subprocess
import sys
import tempfile
from pathlib import Path

from backintel.sandbox import PythonSandbox, SandboxResult


class TrustedFixturePython(PythonSandbox):
    def run(self, code, *, env, mounts, network=None):
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / "fixture.py"
            script.write_text(code)
            result = subprocess.run(
                [sys.executable, "-I", str(script)],
                env=env,
                cwd=directory,
                capture_output=True,
                text=True,
                timeout=10,
            )
            return SandboxResult(result.stdout, result.stderr, result.returncode, 0, "trusted test fixture")
