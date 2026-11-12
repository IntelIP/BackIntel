"""A Docker-only, per-run coding workspace with bounded persistent outputs.

The workspace persists between commands, not across container failures. Only explicitly
exported regular artifact files survive close/cancellation. No writable host mount is used.
"""

from __future__ import annotations

import json
import os
import selectors
import shutil
import subprocess
import tarfile
import threading
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

from backintel.sandbox import DOCKER_IMAGE, MAX_OUTPUT_CHARS, SandboxResult


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


def _checked(command: list[str], *, timeout: float = 20) -> str:
    result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        # Do not echo command arguments: store credentials may be among them.
        raise RuntimeError(f"Docker operation failed: {result.stderr[:1000]}")
    return result.stdout


def docker_capacity() -> dict:
    """Only capacity fields, never Docker configuration or credentials."""
    raw = _checked(["docker", "info", "--format", "{{json .MemTotal}} {{json .NCPU}}"])
    memory, cpus = raw.split()
    return {"memory_bytes": int(memory), "cpus": int(cpus)}


class AnalysisSandbox:
    """One isolated analytical run. Use as a context manager and export before close.

    `env` and `mounts` come from a trusted Store, never directly from a model. Optional
    `network` identifies internal store infrastructure. Only assigned endpoints are attached
    to a fresh internal run network; their backend peers remain on the infrastructure network.
    """

    def __init__(
        self,
        *,
        env: dict[str, str] | None = None,
        mounts: dict[str, str] | None = None,
        network: str | None = None,
        allowed_hosts: set[str] | None = None,
        profile: str | ResourceProfile = "analysis",
        image: str = DOCKER_IMAGE,
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
        self._owned_network: str | None = None
        self._source_peers: list[str] = []
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
        return "docker"

    def __enter__(self):
        return self.start()

    def __exit__(self, *_):
        self.close()

    def start(self):
        if self.closed:
            raise RuntimeError("A closed sandbox cannot be restarted; create a new run.")
        if self.started_at is not None:
            return self
        if shutil.which("docker") is None:
            raise RuntimeError("Analysis requires Docker; there is no host subprocess fallback.")
        capacity = docker_capacity()
        if self.profile.memory_mib * 1024**2 > capacity["memory_bytes"] * 0.85:
            raise RuntimeError("Requested profile leaves insufficient Docker VM memory headroom.")
        if self.profile.cpus > capacity["cpus"]:
            raise RuntimeError("Requested profile exceeds available Docker CPUs.")
        self.image_id = _checked(
            ["docker", "inspect", "--type=image", self.image, "--format", "{{.Id}}"]
        ).strip()
        p = self.profile
        command = [
            "docker",
            "run",
            "--detach",
            "--rm",
            "--name",
            self.name,
            "--label",
            "backintel.analysis=true",
            "--network",
            self.network or "none",
            "--dns",
            "127.0.0.1",  # Keep Docker's peer-name resolution; disable external DNS forwarding.
            "--read-only",
            "--user",
            "10001:10001",
            "--memory",
            f"{p.memory_mib}m",
            "--memory-swap",
            f"{p.memory_mib}m",
            "--cpus",
            str(p.cpus),
            "--pids-limit",
            str(p.pids),
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--init",
            "--ulimit",
            "nofile=1024:1024",
            "--workdir",
            "/workspace",
        ]
        for path, mib in [
            ("/workspace", p.workspace_mib),
            ("/artifacts", p.artifacts_mib),
            ("/tmp", p.temporary_mib),
        ]:
            command += ["--tmpfs", f"{path}:rw,nosuid,nodev,size={mib}m,uid=10001,gid=10001,mode=0700"]
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
        )
        for host, inside in self.mounts.items():
            source = Path(host).resolve(strict=True)
            target = PurePosixPath(inside)
            if not target.is_absolute() or ".." in target.parts or str(target) == "/":
                raise ValueError("Source mounts require an absolute, non-root container path.")
            if any(str(target) == part or str(target).startswith(part + "/") for part in protected):
                raise ValueError("Source mounts cannot replace runtime or output directories.")
            if source in {Path("/"), Path.home(), Path.home().parent} or "," in str(source):
                raise ValueError("Refusing an overly broad or malformed source mount.")
            if "," in str(target):
                raise ValueError("Malformed source mount target.")
            command += ["--mount", f"type=bind,src={source},dst={target},readonly"]
        for key, value in self.env.items():
            if not key.startswith("BACKINTEL_") or not key.replace("_", "").isalnum():
                raise ValueError("Only explicit BACKINTEL_ store context can enter the analysis sandbox.")
            command += ["--env", f"{key}={value}"]
        # The container expires even if the host process is killed before its watchdog runs.
        command += [self.image_id, "sleep", str(p.run_timeout_s)]
        try:
            if self.network:
                self._isolate_network()
                command[command.index("--network") + 1] = self.network
            _checked(command, timeout=45)
            self.started_at = time.monotonic()
            self._watchdog = threading.Timer(p.run_timeout_s, self.cancel)
            self._watchdog.daemon = True
            self._watchdog.start()
        except BaseException:
            self.close()
            raise
        return self

    def _isolate_network(self):
        """Attach only selected source endpoints; never modify their existing connections."""
        details = json.loads(
            _checked(["docker", "network", "inspect", self.network, "--format", "{{json .}}"])
        )
        if not details.get("Internal") or not self.allowed_hosts:
            raise ValueError("Networked analysis requires an internal network and assigned source hosts.")
        selected, found = {}, set()
        for container_id, peer in details.get("Containers", {}).items():
            networks = json.loads(
                _checked(
                    ["docker", "inspect", container_id, "--format", "{{json .NetworkSettings.Networks}}"]
                )
            )
            names = {peer.get("Name"), *(networks.get(self.network, {}).get("Aliases") or [])}
            authorized = names & self.allowed_hosts
            if found & authorized:
                raise ValueError("Assigned source hostname resolves to more than one container.")
            if authorized:
                selected[container_id] = authorized
                found.update(authorized)
        if found != self.allowed_hosts:
            raise ValueError("Not all assigned source hosts exist on the selected internal network.")
        private = f"{self.name}-net"
        _checked(["docker", "network", "create", "--internal", "--label", "backintel.analysis=true", private])
        self._owned_network = self.network = private
        for container_id, names in selected.items():
            # Track before connecting so even an interrupted Docker response gets cleaned up.
            self._source_peers.append(container_id)
            aliases = [arg for name in sorted(names) for arg in ("--alias", name)]
            _checked(["docker", "network", "connect", *aliases, private, container_id])
        self._validate_network()

    def _validate_network(self):
        details = json.loads(
            _checked(["docker", "network", "inspect", self.network, "--format", "{{json .}}"])
        )
        if not details.get("Internal"):
            raise ValueError("Analysis may join only an explicitly internal Docker network.")
        if not self.allowed_hosts:
            raise ValueError("Networked analysis requires explicit assigned source hostnames.")
        found = set()
        for container_id, peer in details.get("Containers", {}).items():
            if peer.get("Name") == self.name:
                continue
            networks = json.loads(
                _checked(
                    ["docker", "inspect", container_id, "--format", "{{json .NetworkSettings.Networks}}"]
                )
            )
            endpoint = networks.get(self.network, {})
            names = {peer.get("Name"), *(endpoint.get("Aliases") or [])}
            authorized = names & self.allowed_hosts
            if not authorized:
                raise ValueError(
                    "Shared network includes an unassigned peer; use a source-only internal network."
                )
            found.update(authorized)
        if found != self.allowed_hosts:
            raise ValueError("Not all assigned source hosts exist on the selected internal network.")

    def _execute(self, arguments: list[str], *, input_data: bytes | None = None) -> SandboxResult:
        with self._command_lock:
            if self.started_at is None:
                self.start()
            if self.closed:
                return SandboxResult("", "Sandbox is closed or cancelled.", -1, 0, "docker")
            if self.network:
                try:
                    self._validate_network()
                except (ValueError, RuntimeError):
                    self.cancel()
                    raise
            remaining = self.profile.run_timeout_s - (time.monotonic() - self.started_at)
            if self.commands >= self.profile.max_commands or remaining <= 0:
                self.cancel()
                return SandboxResult("", "Whole-run command/time budget exhausted.", -1, 0, "docker", True)
            self.commands += 1
            timeout = min(self.profile.command_timeout_s, remaining)
            started = time.monotonic()
            proc = subprocess.Popen(
                ["docker", "exec", *(["-i"] if input_data is not None else []), self.name, *arguments],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE if input_data is not None else None,
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
                "docker",
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
                [
                    "docker",
                    "exec",
                    self.name,
                    "tar",
                    "-C",
                    str(source_path.parent),
                    "-cf",
                    "-",
                    "--",
                    source_path.name,
                ],
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
                result = subprocess.run(
                    ["docker", "exec", self.name, "cat", "/sys/fs/cgroup/memory.peak"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode == 0 and result.stdout.strip().isdigit():
                    self._peak_memory_bytes = max(self._peak_memory_bytes, int(result.stdout.strip()))
            except subprocess.TimeoutExpired:
                pass  # Observability must not turn a completed command into a failed analysis.
        return {
            "peak_memory_bytes": self._peak_memory_bytes,
            "commands": self.commands,
            "elapsed_ms": int(((self.finished_at or time.monotonic()) - self.started_at) * 1000)
            if self.started_at
            else 0,
            "image_id": self.image_id,
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
                ["docker", "exec", self.name, "tar", "-C", "/artifacts", "-cf", "-", "."],
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
        if shutil.which("docker"):
            try:
                subprocess.run(["docker", "rm", "--force", self.name], capture_output=True, timeout=15)
            finally:
                if self._owned_network:
                    # Even an unassigned peer that triggered cancellation must be detached
                    # from our disposable network. Its other networks/container stay intact.
                    peers = set(self._source_peers)
                    inspected = subprocess.run(
                        [
                            "docker",
                            "network",
                            "inspect",
                            self._owned_network,
                            "--format",
                            "{{json .Containers}}",
                        ],
                        capture_output=True,
                        text=True,
                        timeout=15,
                    )
                    if inspected.returncode == 0:
                        peers.update(json.loads(inspected.stdout) or {})
                    for peer in peers:
                        subprocess.run(
                            ["docker", "network", "disconnect", "--force", self._owned_network, peer],
                            capture_output=True,
                            timeout=15,
                        )
                    subprocess.run(
                        ["docker", "network", "rm", self._owned_network], capture_output=True, timeout=15
                    )

    def cancel(self):
        self.cancelled = True
        self.close()
