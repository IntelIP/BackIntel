import pytest

from backintel.cli import main


def test_paid_acceptance_requires_allowance_before_building_stores(monkeypatch):
    def unexpected_build(*args, **kwargs):
        pytest.fail("Missing allowance must stop before any dataset mutation or model call")

    monkeypatch.setattr("backintel.bench.acceptance.build_acceptance", unexpected_build)
    with pytest.raises(ValueError, match="explicitly authorized"):
        main(["acceptance", "run"])


def test_coding_proposal_requires_explicit_allowance(tmp_path):
    with pytest.raises(SystemExit) as error:
        main(
            [
                "improve",
                "propose",
                "--files",
                "src/backintel/agent_files/lead.md",
                "--brief",
                str(tmp_path / "brief.txt"),
                "--output",
                str(tmp_path / "proposal.json"),
            ]
        )
    assert error.value.code == 2
    assert not (tmp_path / "proposal.json").exists()
