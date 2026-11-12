"""Real container acceptance is opt-in; the default suite never needs Docker or a model."""

import json
import os
import subprocess
import time
import uuid
from pathlib import Path

import pytest

from backintel.analysis_sandbox import AnalysisSandbox, ResourceProfile
from backintel.sandbox import DOCKER_IMAGE

docker = pytest.mark.skipif(
    os.environ.get("BACKINTEL_DOCKER_TESTS") != "1", reason="Docker acceptance opt-in"
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


@docker
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
    assert subprocess.run(["docker", "inspect", sandbox.name], capture_output=True).returncode != 0


@docker
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


@docker
def test_real_whole_run_deadline_and_command_budget():
    with AnalysisSandbox(timeout_s=2) as sandbox:
        time.sleep(3)
        assert sandbox.closed and sandbox.cancelled
    with AnalysisSandbox(max_commands=1) as sandbox:
        assert sandbox.run_shell("true").exit_code == 0
        assert sandbox.run_shell("true").exit_code != 0
        assert sandbox.closed


@docker
def test_real_internal_network_allows_only_assigned_peers():
    suffix = uuid.uuid4().hex[:12]
    network, source, extra = (f"backintel-test-{kind}-{suffix}" for kind in ("net", "source", "extra"))
    subprocess.run(["docker", "network", "create", "--internal", network], check=True, capture_output=True)
    try:
        subprocess.run(
            [
                "docker",
                "run",
                "-d",
                "--name",
                source,
                "--network",
                network,
                "--read-only",
                "--memory",
                "128m",
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
        env = {"BACKINTEL_CH_URL": f"http://{source}:8080"}
        with AnalysisSandbox(env=env, network=network) as sandbox:
            result = sandbox.run_python(
                f"import urllib.request; print(urllib.request.urlopen('http://{source}:8080/README.md').read(40))"
            )
            assert result.exit_code == 0, result.stderr
            assert "Offline analytical workspace" in result.stdout
            assert (
                sandbox.run_python(
                    "import socket; socket.create_connection(('1.1.1.1',443),timeout=1)"
                ).exit_code
                != 0
            )
            subprocess.run(
                [
                    "docker",
                    "run",
                    "-d",
                    "--name",
                    extra,
                    "--network",
                    network,
                    "--read-only",
                    "--memory",
                    "32m",
                    DOCKER_IMAGE,
                    "sleep",
                    "infinity",
                ],
                check=True,
                capture_output=True,
            )
            with pytest.raises(ValueError, match="unassigned peer"):
                sandbox.run_shell("echo must-not-execute")
    finally:
        for name in (source, extra):
            subprocess.run(["docker", "rm", "--force", name], capture_output=True)
        subprocess.run(["docker", "network", "rm", network], capture_output=True)


@docker
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
