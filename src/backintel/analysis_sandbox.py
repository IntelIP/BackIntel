"""A SmolVM-only, per-run coding workspace with bounded persistent outputs.

The workspace persists between commands, not across VM failures. Only explicitly
exported regular artifact files survive close/cancellation. No writable host mount is used.
"""

from __future__ import annotations

import json
import os
import selectors
import shutil
import subprocess
import tarfile
import tempfile
import threading
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

from backintel.sandbox import MAX_OUTPUT_CHARS, SandboxResult
from backintel.smol_runtime import capacity, host_environment, image_archive, image_staging_lock, runtime
from backintel.smol_services import ServiceBridges


@dataclass(frozen=True)
class ResourceProfile:
    memory_mib: int = 2048
    cpus: float = 2.0
    workspace_mib: int = 512
    artifacts_mib: int = 128
    temporary_mib: int = 256
    pids: int = 128
    command_timeout_s: int = 120
    run_timeout_s: int = 900
    max_commands: int = 40

    def __post_init__(self):
        if any(value <= 0 for value in asdict(self).values()):
            raise ValueError("All sandbox resource limits must be positive.")
        if self.command_timeout_s > self.run_timeout_s:
            raise ValueError("Command timeout cannot exceed the whole-run deadline.")
        if self.workspace_mib + self.artifacts_mib + self.temporary_mib >= self.memory_mib:
            raise ValueError("Reserve RAM for analysis in addition to the bounded tmpfs filesystems.")


RESOURCE_PROFILES = {
    "analysis": ResourceProfile(),
    "large": ResourceProfile(
        memory_mib=4096,
        cpus=3.0,
        workspace_mib=1024,
        temporary_mib=512,
        command_timeout_s=300,
        run_timeout_s=1800,
    ),
}


class AnalysisSandbox:
    """One isolated analytical run. Use as a context manager and export before close.

    `env` and `mounts` come from a trusted Store, never directly from a model. Optional
    `network` identifies internal store infrastructure. Assigned endpoints are bridged through
    individual Unix sockets. The VM has no outbound network or general host access.
    """

    def __init__(
        self,
        *,
        env: dict[str, str] | None = None,
        mounts: dict[str, str] | None = None,
        network: str | None = None,
        allowed_hosts: set[str] | None = None,
        profile: str | ResourceProfile = "analysis",
        image: str | Path | None = None,
        timeout_s: int | None = None,
        max_commands: int | None = None,
    ):
        self.profile = RESOURCE_PROFILES[profile] if isinstance(profile, str) else profile
        if timeout_s is not None or max_commands is not None:
            values = asdict(self.profile)
            if timeout_s is not None:
                values["run_timeout_s"] = timeout_s
                values["command_timeout_s"] = min(values["command_timeout_s"], timeout_s)
            if max_commands is not None:
                values["max_commands"] = max_commands
            self.profile = ResourceProfile(**values)
        self.env = dict(env or {})
        self.mounts = dict(mounts or {})
        # Store adapters use the same host/container path. Relocate those mounts so a
        # checkout under /workspace (or /tmp) never overlaps our protected tmpfs roots.
        for index, (host, inside) in enumerate(self.mounts.items()):
            if host == inside:
                target = f"/sources/{index}/{PurePosixPath(inside).name}"
                self.mounts[host] = target
                for key in ("BACKINTEL_SQLITE_PATH", "BACKINTEL_FILES_DIR", "BACKINTEL_PARQUET_DIR"):
                    if self.env.get(key) == inside:
                        self.env[key] = target
        self.network = network
        self._services: ServiceBridges | None = None
        self._staging: tempfile.TemporaryDirectory | None = None
        self.engine: str | None = None
        self._created = False
        self.allowed_hosts = set(allowed_hosts or ())
        for key in ("BACKINTEL_POSTGRES_DSN", "BACKINTEL_MONGO_URI", "BACKINTEL_CH_URL"):
            if key in self.env and (host := urlsplit(self.env[key]).hostname):
                self.allowed_hosts.add(host)
        if "BACKINTEL_ICEBERG_TABLES" in self.env:
            self.allowed_hosts.add("backintel-garage")  # The existing Iceberg adapter's fixed endpoint.
        self.image = image
        self.name = f"backintel-analysis-{uuid.uuid4().hex}"
        self.image_id: str | None = None
        self.started_at: float | None = None
        self.finished_at: float | None = None
        self.commands = 0
        self.closed = False
        self.cancelled = False
        self._watchdog: threading.Timer | None = None
        self._command_lock = threading.Lock()
        self._peak_memory_bytes = 0

    @property
    def label(self) -> str:
        return "smolvm"

    def __enter__(self):
        return self.start()

    def __exit__(self, *_):
        self.close()

    def _checked(self, arguments, *, timeout=30):
        result = subprocess.run(
            [self.engine, *arguments], capture_output=True, text=True, timeout=timeout, env=host_environment()
        )
        if result.returncode:
            # Never echo arguments: explicitly assigned store credentials may be present.
            raise RuntimeError(f"SmolVM operation failed: {result.stderr[:1000]}")
        return result.stdout

    def _exec_command(self, arguments, *, input_data=False, timeout=30):
        return [
            self.engine,
            "machine",
            "exec",
            "--name",
            self.name,
            "--user",
            "0",
            "--workdir",
            "/workspace",
            "--timeout",
            f"{max(1, int(timeout))}s",
            *(["-i"] if input_data else ["--stream"]),
            "--",
            "python",
            "-I",
            "/opt/backintel/runtime/execute.py",
            json.dumps(asdict(self.profile)),
            *arguments,
        ]

    def start(self):
        if self.closed:
            raise RuntimeError("A closed sandbox cannot be restarted; create a new run.")
        if self.started_at is not None:
            return self
        self.engine = runtime()
        available = capacity()
        if self.profile.memory_mib * 1024**2 > available["memory_bytes"] * 0.85:
            raise RuntimeError("Requested profile leaves insufficient host memory headroom.")
        if self.profile.cpus > available["cpus"] or int(self.profile.cpus) != self.profile.cpus:
            raise ValueError("SmolVM requires whole CPUs within available host capacity.")
        archive, self._image_receipt = image_archive(self.image)
        self.image_id = self._image_receipt["image_id"]
        p = self.profile
        command = [
            "machine",
            "create",
            "--name",
            self.name,
            "--label",
            "owner=backintel",
            "--image",
            str(archive),
            "--cpus",
            str(int(p.cpus)),
            "--mem",
            str(p.memory_mib),
            "--storage",
            "3",
            "--overlay",
            "1",
            "--shm-size",
            f"{p.temporary_mib}m",
            "--user",
            "0",
            "--stop-on-exit",
            "--stop-timeout",
            "1",
            "--volume",
            f"{Path(__file__).parent / 'smol_guest'}:/opt/backintel/runtime:ro",
        ]
        self._staging = tempfile.TemporaryDirectory(prefix="backintel-sources-")
        file_directories = {}
        try:
            for host, inside in self.mounts.items():
                source, target = Path(host).resolve(strict=True), PurePosixPath(inside)
                protected = (
                    "/workspace",
                    "/artifacts",
                    "/tmp",
                    "/opt",
                    "/usr",
                    "/bin",
                    "/etc",
                    "/proc",
                    "/sys",
                    "/dev",
                    "/run",
                    "/backintel-sockets",
                )
                if (
                    not target.is_absolute()
                    or ".." in target.parts
                    or str(target) == "/"
                    or any(target == PurePosixPath(part) or target.is_relative_to(part) for part in protected)
                ):
                    raise ValueError("Source mounts cannot replace runtime or output directories.")
                if source in {Path("/"), Path.home(), Path.home().parent} or ":" in str(source) + str(target):
                    raise ValueError("Refusing an overly broad or malformed source mount.")
                if source.is_dir():
                    command += ["--volume", f"{source}:{target}:ro"]
                elif source.is_file() and str(target.parent) != "/":
                    directory = file_directories.setdefault(
                        str(target.parent), Path(self._staging.name) / str(len(file_directories))
                    )
                    directory.mkdir(exist_ok=True)
                    shutil.copyfile(source, directory / target.name)
                else:
                    raise ValueError("Sources must be regular files or directories.")
            for target, source in file_directories.items():
                command += ["--volume", f"{source}:{target}:ro"]
            for key, value in self.env.items():
                if not key.startswith("BACKINTEL_") or not key.replace("_", "").isalnum():
                    raise ValueError("Only explicit BACKINTEL_ store context can enter the analysis sandbox.")
                command += ["--env", f"{key}={value}"]
            services = []
            if self.network:
                self._services = ServiceBridges(self.network, self.env, self.allowed_hosts)
                services = self._services.services
                for service in services:
                    command += ["--mount-socket", f"{service['host_socket']}:{service['socket']}"]
            command += [
                "--",
                "python",
                "-I",
                "/opt/backintel/runtime/boot.py",
                json.dumps(asdict(p)),
                json.dumps(
                    [{k: v for k, v in item.items() if k in {"host", "port", "socket"}} for item in services]
                ),
            ]
            self._created = True
            # SmolVM 1.31.1's concurrent cold-cache staging can copy onto a hardlink
            # of its input, truncating both. Serialize staging, not VM execution.
            with image_staging_lock():
                self._checked(command, timeout=120)
            self._checked(["machine", "start", "--name", self.name], timeout=120)
            deadline = time.monotonic() + 15
            while True:
                ready = subprocess.run(
                    [
                        self.engine,
                        "machine",
                        "exec",
                        "--name",
                        self.name,
                        "--timeout",
                        "2s",
                        "--",
                        "test",
                        "-f",
                        "/run/backintel-ready",
                    ],
                    capture_output=True,
                    timeout=5,
                    env=host_environment(),
                )
                if ready.returncode == 0:
                    break
                if time.monotonic() >= deadline:
                    logs = self._checked(["machine", "logs", "--name", self.name])
                    raise RuntimeError(f"SmolVM workspace setup failed: {logs[-1500:]}")
                time.sleep(0.1)
            self.started_at = time.monotonic()
            self._watchdog = threading.Timer(p.run_timeout_s, self.cancel)
            self._watchdog.daemon = True
            self._watchdog.start()
        except BaseException:
            self.close()
            raise
        return self

    def _execute(self, arguments: list[str], *, input_data: bytes | None = None) -> SandboxResult:
        with self._command_lock:
            if self.started_at is None:
                self.start()
            if self.closed:
                return SandboxResult("", "Sandbox is closed or cancelled.", -1, 0, "smolvm")
            if self.network:
                try:
                    self._services.validate()
                except (ValueError, RuntimeError):
                    self.cancel()
                    raise
            remaining = self.profile.run_timeout_s - (time.monotonic() - self.started_at)
            if self.commands >= self.profile.max_commands or remaining <= 0:
                self.cancel()
                return SandboxResult("", "Whole-run command/time budget exhausted.", -1, 0, "smolvm", True)
            self.commands += 1
            timeout = min(self.profile.command_timeout_s, remaining)
            started = time.monotonic()
            proc = subprocess.Popen(
                self._exec_command(arguments, input_data=input_data is not None, timeout=timeout),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE if input_data is not None else None,
                env=host_environment(),
            )
            writer = None
            if input_data is not None:

                def feed_input():
                    try:
                        proc.stdin.write(input_data)
                    except BrokenPipeError:
                        pass
                    finally:
                        proc.stdin.close()

                writer = threading.Thread(target=feed_input, daemon=True)
                writer.start()
            buffers = {"stdout": bytearray(), "stderr": bytearray()}
            truncated = {"stdout": False, "stderr": False}
            timed_out = False
            selector = selectors.DefaultSelector()
            try:
                for name, stream in [("stdout", proc.stdout), ("stderr", proc.stderr)]:
                    os.set_blocking(stream.fileno(), False)
                    selector.register(stream, selectors.EVENT_READ, name)
                while selector.get_map():
                    if time.monotonic() - started >= timeout or self.closed:
                        timed_out = True
                        self.cancel()
                        proc.kill()
                        break
                    for key, _ in selector.select(timeout=0.1):
                        chunk = os.read(key.fileobj.fileno(), 65536)
                        if not chunk:
                            selector.unregister(key.fileobj)
                            continue
                        room = max(0, MAX_OUTPUT_CHARS - len(buffers[key.data]))
                        buffers[key.data].extend(chunk[:room])
                        truncated[key.data] |= len(chunk) > room
                proc.wait(timeout=10)
            except BaseException:
                self.cancel()
                proc.kill()
                proc.wait(timeout=10)
                raise
            finally:
                selector.close()
                proc.stdout.close()
                proc.stderr.close()
                if writer:
                    writer.join(timeout=1)
            outputs = {
                key: data.decode("utf-8", "replace") + ("\n…[output clipped]…" if truncated[key] else "")
                for key, data in buffers.items()
            }
            if timed_out:
                outputs["stderr"] += "\nExecution deadline reached; this sandbox was cancelled."
            self.resource_usage()
            return SandboxResult(
                outputs["stdout"],
                outputs["stderr"],
                -1 if timed_out else proc.returncode,
                int((time.monotonic() - started) * 1000),
                "smolvm",
                timed_out,
            )

    def run_shell(self, command: str) -> SandboxResult:
        if len(command.encode()) > 64 * 1024:
            raise ValueError("Shell command exceeds 64 KiB; split the program into files.")
        return self._execute(["bash", "--noprofile", "--norc", "-c", command])

    def run_python(self, code: str) -> SandboxResult:
        if len(code.encode()) > 64 * 1024:
            raise ValueError("Python command exceeds 64 KiB.")
        return self._execute(["python", "-I", "-c", code])

    @staticmethod
    def _writable_path(path: str) -> str:
        parsed = PurePosixPath(path)
        if ".." in parsed.parts or not any(
            parsed.is_relative_to(root) for root in ("/workspace", "/artifacts")
        ):
            raise ValueError("Write only within /workspace or /artifacts.")
        return str(parsed)

    def write_file(self, path: str, content: str) -> SandboxResult:
        path = self._writable_path(path)
        encoded = content.encode()
        if len(encoded) > 256 * 1024:
            raise ValueError("write_file is limited to 256 KiB; use shell tools for larger generated data.")
        script = (
            f"from pathlib import Path; import sys; p=Path({path!r}); "
            "p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(sys.stdin.buffer.read())"
        )
        return self._execute(["python", "-I", "-c", script], input_data=encoded)

    def read_file(self, path: str, max_bytes: int = 256 * 1024) -> str:
        return self.read_bytes(path, max_bytes=max_bytes).decode("utf-8")

    def read_bytes(self, path: str, max_bytes: int = 2 * 1024 * 1024) -> bytes:
        """Read a bounded workspace/artifact file without model-output truncation."""
        path = self._writable_path(path)
        if not 0 < max_bytes <= self.profile.artifacts_mib * 1024**2:
            raise ValueError("Read limit exceeds the artifact budget.")
        with self._command_lock:
            if self.started_at is None or self.closed:
                raise RuntimeError("Read from an active sandbox before closing it.")
            source_path = PurePosixPath(path)
            proc = subprocess.Popen(
                self._exec_command(
                    ["tar", "-C", str(source_path.parent), "-cf", "-", "--", source_path.name]
                ),
                env=host_environment(),
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
            timer = threading.Timer(30, proc.kill)
            timer.daemon = True
            timer.start()
            try:
                with tarfile.open(fileobj=proc.stdout, mode="r|") as archive:
                    member = archive.next()
                    if member is None or not member.isfile() or member.islnk() or member.size > max_bytes:
                        raise ValueError("Requested file is not a bounded regular file.")
                    with archive.extractfile(member) as source:
                        data = source.read(max_bytes + 1)
                    if len(data) > max_bytes or archive.next() is not None:
                        raise ValueError("Expected a single bounded file.")
                if proc.wait(timeout=5) != 0:
                    raise RuntimeError("Sandbox file read failed.")
                return data
            finally:
                timer.cancel()
                proc.kill() if proc.poll() is None else None
                proc.wait(timeout=5)
                proc.stdout.close()

    def resource_usage(self) -> dict:
        if self.started_at is not None and not self.closed:
            try:
                stats = json.loads(
                    self._checked(["machine", "stats", "--name", self.name, "--json"], timeout=10)
                )
                self._peak_memory_bytes = max(self._peak_memory_bytes, stats["memory"]["used_bytes"])
            except (subprocess.TimeoutExpired, RuntimeError, KeyError, ValueError):
                pass
        return {
            "backend": "smolvm",
            "runtime_version": "1.31.1",
            "peak_memory_bytes": self._peak_memory_bytes,
            "memory_measurement": "sampled VM used memory; includes guest runtime",
            "commands": self.commands,
            "elapsed_ms": int(((self.finished_at or time.monotonic()) - self.started_at) * 1000)
            if self.started_at
            else 0,
            "image_id": self.image_id,
            "image_archive_sha256": getattr(self, "_image_receipt", {}).get("archive_sha256"),
            "profile": asdict(self.profile),
            "cancelled": self.cancelled,
        }

    def export_artifacts(self, destination: str | Path) -> list[str]:
        """Export bounded regular files only, never symlinks, devices or path traversal.

        The caller validates their semantic manifest before serving them. No tarfile.extract
        is used. Export is exclusive; command execution cannot run concurrently with it.
        """
        with self._command_lock:
            if self.started_at is None or self.closed:
                raise RuntimeError("Export artifacts before closing the active sandbox.")
            output = Path(destination)
            if output.exists() and (output.is_symlink() or any(output.iterdir())):
                raise ValueError("Artifact destination must be a new or empty real directory.")
            output.mkdir(parents=True, exist_ok=True)
            output = output.resolve()
            proc = subprocess.Popen(
                self._exec_command(["tar", "-C", "/artifacts", "-cf", "-", "."], timeout=60),
                env=host_environment(),
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
            files, total = [], 0
            timer = threading.Timer(min(60, self.profile.command_timeout_s), proc.kill)
            timer.daemon = True
            timer.start()
            try:
                with tarfile.open(fileobj=proc.stdout, mode="r|") as archive:
                    for member in archive:
                        path = PurePosixPath(member.name)
                        if path.is_absolute() or ".." in path.parts:
                            raise ValueError("Invalid artifact archive path.")
                        if member.isdir():
                            continue
                        if not member.isfile() or member.issym() or member.islnk():
                            raise ValueError("Artifacts must be regular files, not links or special files.")
                        total += member.size
                        if total > self.profile.artifacts_mib * 1024**2 or len(files) >= 256:
                            raise ValueError("Artifact export exceeds run limits.")
                        if path.suffix.lower() not in {
                            ".json",
                            ".csv",
                            ".xlsx",
                            ".png",
                            ".svg",
                            ".html",
                            ".md",
                            ".txt",
                        }:
                            raise ValueError(f"Unsupported artifact format: {path.suffix}")
                        target = output.joinpath(*path.parts)
                        target.parent.mkdir(parents=True, exist_ok=True)
                        with archive.extractfile(member) as source, target.open("xb") as dest:
                            shutil.copyfileobj(source, dest, length=65536)
                        files.append(str(target.relative_to(output)))
                if proc.wait(timeout=5) != 0:
                    raise RuntimeError("Artifact export failed or exceeded its deadline.")
            except BaseException:
                proc.kill()
                proc.wait(timeout=5)
                # Only our new export directory is removed, never an existing populated path.
                shutil.rmtree(output)
                raise
            finally:
                timer.cancel()
                proc.stdout.close()
            return files

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.finished_at = time.monotonic()
        if self._watchdog:
            self._watchdog.cancel()
        try:
            if self.engine and self._created:
                try:
                    subprocess.run(
                        [self.engine, "machine", "stop", "--name", self.name],
                        capture_output=True,
                        timeout=20,
                        env=host_environment(),
                    )
                finally:
                    deleted = subprocess.run(
                        [
                            self.engine,
                            "machine",
                            "delete",
                            "--name",
                            self.name,
                            "--force",
                            "--error-format",
                            "json",
                        ],
                        capture_output=True,
                        text=True,
                        timeout=30,
                        env=host_environment(),
                    )
                    if deleted.returncode:
                        try:
                            missing = json.loads(deleted.stderr)["error"]["code"] == "NOT_FOUND"
                        except (ValueError, KeyError):
                            missing = False
                        if not missing:
                            raise RuntimeError(f"SmolVM cleanup failed for {self.name}; retain its identity.")
        finally:
            if self._services:
                self._services.close()
            if self._staging:
                self._staging.cleanup()

    def cancel(self):
        self.cancelled = True
        self.close()
