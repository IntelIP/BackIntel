"""Pinned local runtime and image admission. Preparation is separate from execution."""

import fcntl
import hashlib
import json
import os
import platform
import subprocess
import time
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path

VERSION = "1.31.1"
ARCHIVE_SHA256 = "69196e9880931344411eaf70b667c6633bb3015dc9f741cb85600f85a85d480c"
BINARY_SHA256 = "ae78eda57cb3a4d88960c74077055972fc058441ed49fded26a5b2f146faf086"
RELEASE_URL = f"https://github.com/smol-machines/smolvm/releases/download/v{VERSION}/smolvm-{VERSION}-darwin-arm64.tar.gz"
RUNTIME_HOME = Path.home() / ".local/share/backintel"


@lru_cache(maxsize=8)
def _digest(path: str, _stat_identity: tuple[int, int, int]) -> str:
    with open(path, "rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def digest(path: Path) -> str:
    info = path.stat()
    return _digest(str(path.resolve()), (info.st_size, info.st_mtime_ns, info.st_ctime_ns))


def runtime():
    if (platform.system(), platform.machine()) != ("Darwin", "arm64"):
        raise RuntimeError("This SmolVM release is qualified on macOS ARM64; no runtime fallback is allowed.")
    engine = Path(
        os.environ.get("BACKINTEL_SMOLVM") or RUNTIME_HOME / f"runtimes/smolvm-{VERSION}-darwin-arm64/smolvm"
    )
    binary = engine.parent / "smolvm-bin"
    if not engine.is_file() or not binary.is_file() or digest(binary) != BINARY_SHA256:
        raise RuntimeError("Prepare the pinned SmolVM runtime with uv run python -m scripts.prepare_smolvm.")
    return str(engine)


def image_archive(image: str | Path | None):
    path = Path(
        image or os.environ.get("BACKINTEL_SMOLVM_IMAGE") or RUNTIME_HOME / "images/analysis-py312.tar"
    ).resolve()
    receipt = path.with_suffix(".json")
    if not path.is_file() or not receipt.is_file():
        raise RuntimeError(
            "Prepare a local SmolVM image archive with scripts.prepare_smolvm; runtime pulls are disabled."
        )
    identity = json.loads(receipt.read_text())
    if digest(path) != identity["archive_sha256"]:
        raise ValueError("SmolVM image archive checksum does not match its preparation receipt.")
    return path, identity


@contextmanager
def image_staging_lock():
    """Serialize CLI image staging, whose hardlink/copy fallback is not atomic."""
    RUNTIME_HOME.mkdir(parents=True, exist_ok=True)
    with (RUNTIME_HOME / "image-staging.lock").open("a") as lock:
        deadline = time.monotonic() + 120
        while True:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise TimeoutError("Another sandbox is still staging its SmolVM image.") from None
                time.sleep(0.1)
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def host_environment():
    # Never inherit model credentials, proxy settings, or SMOLVM_* policy overrides.
    return {"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "HOME": str(Path.home()), "TMPDIR": "/tmp"}


def capacity():
    memory = subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True, timeout=5)
    return {"memory_bytes": int(memory), "cpus": os.cpu_count() or 1}
