"""Tests for pc_onboard.cli module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

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


class TestInitCommand:
    def test_init_no_manager_exits_1(self, repo: Path) -> None:
        result = runner.invoke(app, ["init", "--repo-root", str(repo)])
        assert result.exit_code == 1

    def test_init_success_with_mocked_run_init(self, repo: Path) -> None:
        with patch("pc_onboard.cli.run_init", return_value=0):
            result = runner.invoke(
                app, ["init", "--repo-root", str(repo), "--no-prompt"]
            )
        assert result.exit_code == 0

    def test_init_has_run_all_flag(self) -> None:
        result = runner.invoke(app, ["init", "--help"])
        assert "--run-all" in result.stdout
        assert "--no-run-all" in result.stdout

    def test_init_has_no_prompt_flag(self) -> None:
        result = runner.invoke(app, ["init", "--help"])
        assert "--no-prompt" in result.stdout

    def test_init_has_verbose_flag(self) -> None:
        result = runner.invoke(app, ["init", "--help"])
        assert "--verbose" in result.stdout
