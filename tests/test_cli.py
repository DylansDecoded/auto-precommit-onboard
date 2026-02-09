"""Tests for pc_onboard.cli module."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from pc_onboard.cli import app

runner = CliRunner()


class TestDoctorCommand:
    def test_doctor_with_uv_repo(self, repo: Path) -> None:
        (repo / "uv.lock").touch()
        (repo / "pyproject.toml").write_text(
            '[project]\nname = "test"\nrequires-python = ">=3.11,<3.13"\n'
        )
        result = runner.invoke(app, ["doctor", "--repo-root", str(repo)])
        assert result.exit_code == 0
        assert "uv" in result.stdout
        assert "3.12" in result.stdout

    def test_doctor_with_pipenv_repo(self, repo: Path) -> None:
        (repo / "Pipfile").write_text("[requires]\npython_version = 3.11\n")
        result = runner.invoke(app, ["doctor", "--repo-root", str(repo)])
        assert result.exit_code == 0
        assert "pipenv" in result.stdout
        assert "3.11" in result.stdout

    def test_doctor_no_manager_exits_1(self, repo: Path) -> None:
        result = runner.invoke(app, ["doctor", "--repo-root", str(repo)])
        assert result.exit_code == 1
        assert "NOT DETECTED" in result.stdout
