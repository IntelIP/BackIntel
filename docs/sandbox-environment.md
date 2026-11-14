# Analytical sandbox environment

Both `AnalysisSandbox` and the benchmark `PythonSandbox` execute in **SmolVM 1.31.1**.
The qualified local target is macOS ARM64. Each run owns a Linux microVM; the final trusted
artifact renderer uses a separate clean VM. There is no Docker or host-Python fallback.
Docker remains an image preparation tool and the host of optional database services.
File/SQLite/Parquet analysis does not invoke Docker after preparation.

## Prepare once

```bash
uv sync --frozen
docker build -f Dockerfile.sandbox -t backintel-sandbox:py312 .
uv run python -m scripts.prepare_smolvm
uv run backintel sandbox check
```

Preparation downloads a checksum-pinned official SmolVM distribution and exports the
already-built local OCI image. `--runtime-archive /path/to/release.tar.gz` reuses a downloaded
release. Nothing is installed or downloaded by a running analysis. Set
`BACKINTEL_SANDBOX=smolvm` if the environment previously selected Docker.

The default installation is `~/.local/share/backintel/runtimes/smolvm-1.31.1-darwin-arm64/`.
The image is `~/.local/share/backintel/images/analysis-py312.tar`, with an adjacent JSON
preparation receipt. `BACKINTEL_SMOLVM` and `BACKINTEL_SMOLVM_IMAGE` can select their locations;
they do not bypass runtime or image checksums. Missing/corrupt archives fail closed.
BackIntel serializes local image staging with a host file lock (120-second wait limit).
This avoids a SmolVM 1.31.1 cold-cache hardlink/copy race that can truncate an archive
when two machines are created concurrently. VM execution remains concurrent after staging.

The release archive SHA-256 is
`69196e9880931344411eaf70b667c6633bb3015dc9f741cb85600f85a85d480c`.
The binary extracted from that archive hashes to
`ae78eda57cb3a4d88960c74077055972fc058441ed49fded26a5b2f146faf086`.
The same archive was already present for Condere. A historical IntelIPGTM binary lock has
a different hash; this integration records the bytes actually extracted, rather than
copying that old binary identity.

## Packages and source provenance

The existing Python 3.12.16 Debian Bookworm image and hash-locked binary wheels are reused.
Packages include Polars, pandas, NumPy, SciPy, DuckDB and database clients; Matplotlib
3.11.2, Plotly 7.1.0 and openpyxl 3.1.5 provide PNG/SVG, offline interactive HTML and Excel.
Bash, ripgrep, grep, findutils, coreutils, file and DejaVu fonts are preinstalled.
The tested workflow needs no runtime compiler or package downloads. Package records are
in `/opt/backintel/package-versions.txt` and `/opt/backintel/system-packages.txt`; offline
guidance is under `/docs`. The trusted guest setup is mounted read-only from the application.

SmolVM is the upstream [smol-machines project](https://github.com/smol-machines/smolvm/tree/v1.31.1),
not the unrelated SmolLM model family. [Y Combinator's company record](https://www.ycombinator.com/companies/smol-machines)
identifies a San Francisco company led by its founder/CEO; the runtime uses
[libkrun](https://github.com/libkrun/libkrun) and Apple's Hypervisor.framework on this host.
The public records establish the project and its operating organization; no private cap-table
verification is claimed. No new model, hosted provider, cloud account or inference dependency
is introduced. The existing Debian, GNU, Python and analytical package provenance remains
applicable to the unchanged image.

## Limits and workspace

| Profile | RAM / CPUs | Workspace / artifacts / temp | Command / run deadline | Commands |
| --- | --- | --- | --- | --- |
| analysis | 2 GiB / 2 | 512 / 128 / 256 MiB | 120 / 900 seconds | 40 |
| large | 4 GiB / 3 | 1024 / 128 / 512 MiB | 300 / 1800 seconds | 40 |
| benchmark Python | 768 MiB / 1 | 128 / 64 / 128 MiB | caller timeout, normally 120 seconds | 1 |

CPU counts must be whole numbers. Admission requires a profile within the host's CPU count
and at most 85% of its physical RAM; it does not reserve capacity across concurrent runs. SmolVM caps guest
RAM and CPUs. Each run has a 3 GiB image/storage disk and a 1 GiB overlay; analyst writes
are restricted to separately bounded tmpfs mounts. `/dev/shm` is bounded by the temp limit.

Trusted bootstrap sets up the filesystems. Every analyst command gets a private read-only
root mount, UID/GID 10001, no supplemental groups, an empty capability bounding set,
`no_new_privs`, 128 processes per UID and 1024 open files. Applying the read-only root per
command avoids blocking SmolVM's own resolver-metadata refresh. Work files persist between
commands within that run. Source mounts are read-only; individual files are staged as
private copies so their parent directories do not expose other host files.

The host watchdog and command deadline cancel the entire VM. The native workload exits at
the run deadline with `--stop-on-exit`, so it also stops if the host orchestrator disappears.
Explicit close stops and deletes only the task-owned machine. Cancellation is not durable
job resumption. No host home, Docker socket, model credential or writable host directory is
mounted. Host subprocesses run the trusted SmolVM CLI only, never analyst-generated code.

Memory telemetry is sampled **VM used memory**, including guest runtime overhead. Its
sampled maximum is retained in `peak_memory_bytes`; it is not the former Docker cgroup
high-water mark and must not be directly compared without that qualification. Records
include `backend=smolvm`, runtime version, OCI image ID, archive hash and limits.

## Assigned database services

The VM has no outbound network. For each trusted store endpoint, the host validates its
unique identity on the existing internal Docker network and its localhost-only published
TCP port. A task-owned Unix socket forwards only to that specific endpoint. SmolVM mounts
that socket into the guest; a trusted loopback listener preserves the existing database
hostname and port. PostgreSQL, FerretDB, ClickHouse and Garage use the same connection
fields and native database clients. No general localhost/LAN/public-network access is given.

The endpoint is checked before commands and connections. An endpoint that stops or changes
cancels access. The host bridge admits at most 32 concurrent connections. Cleanup removes
all sockets and closes forwards, preserving the source containers and their networks.
Database roles must independently remain read-only; FerretDB's frozen backend remains
necessary. The Docker host is trusted not to replace a binding during a connection.

Same-path local sources are relocated under `/sources`, updating `BACKINTEL_SQLITE_PATH`,
`BACKINTEL_FILES_DIR` and `BACKINTEL_PARQUET_DIR`. The original source remains unchanged.
Artifact reads and exports reuse the bounded tar-stream validation: regular files only,
no links/traversal/special files, supported suffixes, at most 256 files and the byte budget.
Binary downloads use native pipes rather than SmolVM's 11 MiB capped command-output
stream; see the [export fix and real-VM checks](smolvm-artifact-export.md).

## Verification

```bash
uv run pytest -q
BACKINTEL_SMOLVM_TESTS=1 uv run pytest tests/test_analysis_sandbox.py -q
BACKINTEL_SMOLVM_TESTS=1 BACKINTEL_LARGE_TEST=1 uv run pytest tests/test_analysis_sandbox.py -q
```

The real VM checks cover coding and error recovery, source/root write denial, UID and
capabilities, networking, endpoint isolation, storage/output limits, cancellation, binary
artifact transfer and cleanup. The separately pending four-case comparison harness defaults
to a scripted model and makes no provider calls. Historical live Sol/Luna scores were measured on Docker and remain
labelled with that runtime. See [measured results](results-analysis-sandbox.md) for current
verification receipts. Linux and Windows distributions are not qualified by this migration.
