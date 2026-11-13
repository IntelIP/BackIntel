"""Real SmolVM acceptance is opt-in; the default suite never needs Docker or a model."""

import json
import os
import subprocess
import time
import uuid
from pathlib import Path

import pytest

from backintel.analysis_sandbox import AnalysisSandbox, ResourceProfile
from backintel.sandbox import DOCKER_IMAGE, PythonSandbox
from backintel.smol_runtime import runtime

smolvm = pytest.mark.skipif(
    os.environ.get("BACKINTEL_SMOLVM_TESTS") != "1", reason="SmolVM acceptance opt-in"
)


def test_reject_invalid_resource_and_write_contracts():
    with pytest.raises(ValueError, match="positive"):
        ResourceProfile(cpus=0)
    with pytest.raises(ValueError, match="Reserve RAM"):
        ResourceProfile(memory_mib=512)
    sandbox = AnalysisSandbox()
    with pytest.raises(ValueError, match="/workspace"):
        sandbox.write_file("/workspace/../etc/host", "no")
    with pytest.raises(ValueError, match="256 KiB"):
        sandbox.write_file("/workspace/program.py", "x" * (256 * 1024 + 1))


@smolvm
def test_real_persistent_workspace_boundary_and_export(tmp_path):
    source = tmp_path / "source.csv"
    source.write_text("category,revenue\nA,12\nB,18\n")
    with AnalysisSandbox(mounts={str(source): "/assigned/source.csv"}) as sandbox:
        assert sandbox.write_file("/workspace/program.py", "print('first revision')").exit_code == 0
        assert "first revision" in sandbox.run_shell("python /workspace/program.py").stdout
        assert sandbox.run_shell("python -c 'raise ValueError(\"repair me\")'").exit_code != 0
        assert sandbox.write_file("/workspace/program.py", "print('recovered')").exit_code == 0
        assert "recovered" in sandbox.run_shell("python /workspace/program.py").stdout
        assert sandbox.read_file("/workspace/program.py") == "print('recovered')"
        assert sandbox.run_shell("printf forbidden >> /assigned/source.csv").exit_code != 0
        assert sandbox.run_shell("touch /etc/forbidden").exit_code != 0
        assert sandbox.run_shell("touch /home/analyst/forbidden").exit_code != 0
        result = sandbox.run_python("import os; print(os.getuid()); print(open('/proc/self/status').read())")
        assert "10001" in result.stdout and "CapEff:\t0000000000000000" in result.stdout
        assert "NoNewPrivs:\t1" in result.stdout
        assert sandbox.run_shell("test ! -e /var/run/docker.sock && test ! -d /Users/hudson").exit_code == 0
        denied = sandbox.run_python("import socket; socket.create_connection(('1.1.1.1',443),timeout=1)")
        assert denied.exit_code != 0
        assert sandbox.run_shell("command -v bash rg grep find file head tail sort wc").exit_code == 0
        assert (
            sandbox.run_python(
                "import matplotlib, plotly, openpyxl, polars, pandas, numpy, scipy, duckdb"
            ).exit_code
            == 0
        )
        result = sandbox.run_python(
            "import matplotlib.pyplot as plt; import plotly.graph_objects as go; from openpyxl import Workbook; "
            "fig, ax = plt.subplots(); ax.bar(['A','B'],[12,18]); fig.savefig('/artifacts/chart.png'); "
            "fig.savefig('/artifacts/chart.svg'); plt.close(fig); "
            "go.Figure(go.Bar(x=['A','B'],y=[12,18])).write_html('/artifacts/interactive.html',include_plotlyjs=True); "
            "wb=Workbook(); wb.active.append(['A',12]); wb.save('/artifacts/data.xlsx')"
        )
        assert result.exit_code == 0, result.stderr
        assert sandbox.read_bytes("/artifacts/chart.png").startswith(b"\x89PNG\r\n\x1a\n")
        with pytest.raises(ValueError, match="bounded"):
            sandbox.read_bytes("/artifacts/chart.png", max_bytes=10)
        assert sandbox.run_shell("ln -s /assigned/source.csv /artifacts/leak.csv").exit_code == 0
        with pytest.raises(ValueError, match="regular files"):
            sandbox.export_artifacts(tmp_path / "rejected")
        assert not (tmp_path / "rejected").exists()
        assert sandbox.run_shell("rm /artifacts/leak.csv").exit_code == 0
        exported = sandbox.export_artifacts(tmp_path / "delivered")
        assert set(exported) == {"chart.png", "chart.svg", "interactive.html", "data.xlsx"}
        usage = sandbox.resource_usage()
        assert usage["peak_memory_bytes"] > 0
        assert usage["image_id"].startswith("sha256:")
    assert source.read_text() == "category,revenue\nA,12\nB,18\n"
    assert (tmp_path / "delivered/chart.png").is_file()
    assert sandbox.name not in subprocess.check_output([runtime(), "machine", "ls", "--quiet"], text=True)


@smolvm
def test_real_command_deadline_output_and_storage_limits(tmp_path):
    profile = ResourceProfile(workspace_mib=1, artifacts_mib=1, command_timeout_s=2, run_timeout_s=30)
    with AnalysisSandbox(profile=profile) as sandbox:
        overflow = sandbox.run_shell("dd if=/dev/zero of=/workspace/too-large bs=1M count=2")
        assert overflow.exit_code != 0
        assert "space" in overflow.stderr.lower()
        output = sandbox.run_python("print('x'*1000000)")
        assert len(output.stdout) < 13000 and "clipped" in output.stdout
        timeout = sandbox.run_shell("sleep 20")
        assert timeout.timed_out and sandbox.closed
        assert sandbox.run_shell("echo cannot-run").exit_code != 0


@smolvm
def test_real_whole_run_deadline_and_command_budget():
    with AnalysisSandbox(timeout_s=2) as sandbox:
        time.sleep(3)
        assert sandbox.closed and sandbox.cancelled
    with AnalysisSandbox(max_commands=1) as sandbox:
        assert sandbox.run_shell("true").exit_code == 0
        assert sandbox.run_shell("true").exit_code != 0
        assert sandbox.closed


@smolvm
def test_real_offline_vm_reaches_only_assigned_store_socket():
    suffix = uuid.uuid4().hex[:12]
    network, source = (f"backintel-test-{kind}-{suffix}" for kind in ("net", "source"))
    subprocess.run(["docker", "network", "create", "--internal", network], check=True, capture_output=True)
    try:
        subprocess.run(
            [
                "docker",
                "run",
                "-d",
                "--name",
                source,
                "--read-only",
                "--memory",
                "128m",
                "-p",
                "127.0.0.1::8080",
                DOCKER_IMAGE,
                "python",
                "-m",
                "http.server",
                "8080",
                "--directory",
                "/opt/backintel/docs",
            ],
            check=True,
            capture_output=True,
        )
        subprocess.run(["docker", "network", "connect", network, source], check=True, capture_output=True)
        env = {"BACKINTEL_CH_URL": f"http://{source}:8080"}
        with AnalysisSandbox(env=env, network=network) as sandbox:
            peers = json.loads(
                subprocess.check_output(
                    ["docker", "network", "inspect", network, "--format", "{{json .Containers}}"], text=True
                )
            )
            assert {peer["Name"] for peer in peers.values()} == {source}
            result = sandbox.run_python(
                f"import urllib.request; print(urllib.request.urlopen('http://{source}:8080/README.md').read(40))"
            )
            assert result.exit_code == 0, result.stderr
            assert "Offline analytical workspace" in result.stdout
            for host, port in [("1.1.1.1", 443), ("127.0.0.1", 55432), ("host.docker.internal", 80)]:
                assert (
                    sandbox.run_python(
                        f"import socket; socket.create_connection(({host!r},{port}),timeout=1)"
                    ).exit_code
                    != 0
                )
            subprocess.run(
                ["docker", "network", "disconnect", network, source], check=True, capture_output=True
            )
            with pytest.raises(ValueError, match="endpoint changed"):
                sandbox.run_shell("echo must-not-execute")
            assert sandbox.closed
        assert subprocess.run(["docker", "inspect", source], capture_output=True).returncode == 0
    finally:
        subprocess.run(["docker", "rm", "--force", source], capture_output=True)
        subprocess.run(["docker", "network", "rm", network], capture_output=True)


@smolvm
def test_real_large_scan_with_small_memory_budget(tmp_path):
    """A real on-disk input larger than the process memory, created without model calls."""
    # Opt-in large acceptance generates a 320 MiB text corpus, not a >10 GiB roadmap claim.
    if os.environ.get("BACKINTEL_LARGE_TEST") != "1":
        pytest.skip("320 MiB full-file scan acceptance requires BACKINTEL_LARGE_TEST=1")
    source = tmp_path / "large.csv"
    line = "A,1," + "x" * 1018 + "\n"
    count = 327680
    with source.open("w") as stream:
        stream.write("category,value,padding\n")
        for _ in range(count // 1024):
            stream.write(line * 1024)
    profile = ResourceProfile(
        memory_mib=256, workspace_mib=16, artifacts_mib=8, temporary_mib=16, command_timeout_s=120
    )
    with AnalysisSandbox(mounts={str(source): "/assigned/large.csv"}, profile=profile) as sandbox:
        result = sandbox.run_python(
            "import csv,json; count=total=0; "
            "rows=csv.DictReader(open('/assigned/large.csv')); "
            "\nfor row in rows:\n count+=1; total+=int(row['value'])\n"
            "print(json.dumps({'rows':count,'total':total}))"
        )
        assert result.exit_code == 0, result.stderr
        assert json.loads(result.stdout) == {"rows": count, "total": count}
        usage = sandbox.resource_usage()
        assert source.stat().st_size > profile.memory_mib * 1024**2
        Path(tmp_path / "scan-evidence.json").write_text(
            json.dumps({"input_bytes": source.stat().st_size, **usage})
        )


def test_store_mounts_are_relocated_outside_protected_workspace():
    """All local adapters publish their source through a BACKINTEL path variable."""
    from backintel.stores.duckdb_lake import DuckDBLakeStore
    from backintel.stores.files import FilesStore
    from backintel.stores.sqlite import SQLiteStore

    sources = [
        (SQLiteStore, "path", "BACKINTEL_SQLITE_PATH", "sales.sqlite"),
        (FilesStore, "dir", "BACKINTEL_FILES_DIR", "files"),
        (DuckDBLakeStore, "dir", "BACKINTEL_PARQUET_DIR", "parquet"),
    ]
    for cls, attr, key, name in sources:
        store = object.__new__(cls)
        setattr(store, attr, Path("/workspace/BackIntel/data") / name)
        store.files = store.tables = {}
        env, mounts = store.python_environment(), store.python_mounts()
        sandbox = AnalysisSandbox(env=env, mounts=mounts)
        assert sandbox.env[key].startswith("/sources/")
        assert sandbox.mounts[str(getattr(store, attr))] == sandbox.env[key]
        assert env[key].startswith("/workspace/")  # Does not mutate the host-side Store context.


@smolvm
def test_real_store_path_remap_reads_sqlite_and_rejects_writes(tmp_path):
    import sqlite3

    from backintel.stores.sqlite import SQLiteStore

    source = tmp_path / "sales.sqlite"
    with sqlite3.connect(source) as conn:
        conn.execute("CREATE TABLE sales (amount INT)")
        conn.execute("INSERT INTO sales VALUES (42)")
    store = SQLiteStore(source, dataset="fixture")
    try:
        with AnalysisSandbox(env=store.python_environment(), mounts=store.python_mounts()) as sandbox:
            assert sandbox.env["BACKINTEL_SQLITE_PATH"].startswith("/sources/")
            result = sandbox.run_python(
                "import sqlite3,os; c=sqlite3.connect('file:'+os.environ['BACKINTEL_SQLITE_PATH']+'?mode=ro',uri=True); "
                "print(c.execute('SELECT SUM(amount) FROM sales').fetchone()[0])"
            )
            assert result.exit_code == 0 and result.stdout.strip() == "42", result.stderr
            assert (
                sandbox.run_python("import os; open(os.environ['BACKINTEL_SQLITE_PATH'],'wb')").exit_code != 0
            )
    finally:
        store.close()


def test_service_socket_cleanup_when_endpoint_admission_fails(monkeypatch, tmp_path):
    import backintel.smol_services as module

    created = []
    real_temp = module.tempfile.TemporaryDirectory

    def temporary(**kwargs):
        result = real_temp(dir=tmp_path)
        created.append(Path(result.name))
        return result

    monkeypatch.setattr(module.tempfile, "TemporaryDirectory", temporary)
    monkeypatch.setattr(module, "docker_json", lambda *args: [{"Internal": True, "Containers": {}}])
    with pytest.raises(ValueError, match="exactly one"):
        module.ServiceBridges("test", {"BACKINTEL_CH_URL": "http://selected:8123"}, {"selected"})
    assert created and all(not path.exists() for path in created)


@smolvm
def test_real_benchmark_python_uses_smolvm():
    result = PythonSandbox().run("import os; print(os.getuid())", env={}, mounts={})
    assert result.backend == "smolvm"
    assert result.exit_code == 0 and result.stdout.strip() == "10001", result.stderr


@smolvm
def test_real_concurrent_cold_startup_preserves_archive(tmp_path):
    import shutil
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from backintel.smol_runtime import digest, image_archive

    original, receipt = image_archive(None)
    archive = tmp_path / "concurrent.tar"
    shutil.copyfile(original, archive)
    # Trailing padding gives this valid tar a never-staged identity, exposing the
    # upstream cold-cache hardlink race rather than testing an existing seed.
    with archive.open("ab") as stream:
        stream.write(uuid.uuid4().bytes + bytes(10240))
    expected = digest(archive)
    archive.with_suffix(".json").write_text(json.dumps({**receipt, "archive_sha256": expected}))
    barrier = Barrier(2)
    profile = ResourceProfile(memory_mib=768, cpus=1, workspace_mib=128, temporary_mib=128)

    def execute():
        barrier.wait(timeout=10)
        with AnalysisSandbox(image=archive, profile=profile) as sandbox:
            result = sandbox.run_python("print(6 * 7)")
            assert result.exit_code == 0 and result.stdout.strip() == "42", result.stderr

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda _: execute(), range(2)))
    assert digest(archive) == expected


def test_missing_image_archive_fails_without_remote_pull(tmp_path):
    from backintel.smol_runtime import image_archive

    with pytest.raises(RuntimeError, match="runtime pulls are disabled"):
        image_archive(tmp_path / "absent.tar")


def test_partial_machine_creation_failure_is_cleaned(monkeypatch, tmp_path):
    import backintel.analysis_sandbox as module

    actions = []
    monkeypatch.setattr(module, "runtime", lambda: "/smolvm")
    monkeypatch.setattr(module, "capacity", lambda: {"memory_bytes": 8 * 1024**3, "cpus": 4})
    monkeypatch.setattr(
        module, "image_archive", lambda _: (tmp_path / "image.tar", {"image_id": "sha256:test"})
    )

    def run(arguments, **kwargs):
        actions.append(arguments)
        if "create" in arguments:
            raise subprocess.TimeoutExpired(arguments, 120)
        return subprocess.CompletedProcess(arguments, 0, stdout="", stderr="")

    monkeypatch.setattr(module.subprocess, "run", run)
    sandbox = AnalysisSandbox()
    with pytest.raises(subprocess.TimeoutExpired):
        sandbox.start()
    assert sandbox.closed
    assert any(args[1:3] == ["machine", "delete"] and sandbox.name in args for args in actions)
    assert not Path(sandbox._staging.name).exists()
