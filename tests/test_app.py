"""Tests for pc_onboard.app module."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from pc_onboard.app import DEV_PACKAGES, run_init
from pc_onboard.detect import DetectionError
from pc_onboard.mise import MiseError
from pc_onboard.runner import Runner


def _make_runner() -> MagicMock:
    """Return a mock Runner whose .run() succeeds by default."""
    mock = MagicMock(spec=Runner)
    mock.run.return_value = subprocess.CompletedProcess(args=[], returncode=0)
    return mock


class TestRunInit:
    def test_uv_full_workflow(self, repo: Path) -> None:
        (repo / "uv.lock").touch()
        (repo / "pyproject.toml").write_text(
            '[project]\nname = "test"\nrequires-python = ">=3.11,<3.13"\n'
        )
        runner = _make_runner()

        exit_code = run_init(repo, runner, run_all=False)

        assert exit_code == 0
        calls = runner.run.call_args_list

        # mise --version check, mise install, mise use
        assert call(["mise", "--version"], capture=True) in calls
        assert call(["mise", "install", "python@3.12"]) in calls
        assert call(["mise", "use", "python@3.12"]) in calls

        # dev deps
        assert call(["uv", "add", "--dev", *DEV_PACKAGES], cwd=str(repo)) in calls
        assert call(["uv", "sync"], cwd=str(repo)) in calls

        # pre-commit install
        assert call(["uv", "run", "pre-commit", "install"], cwd=str(repo)) in calls

    def test_pipenv_full_workflow(self, repo: Path) -> None:
        (repo / "Pipfile").write_text("[requires]\npython_version = 3.11\n")
        runner = _make_runner()

        exit_code = run_init(repo, runner, run_all=False)

        assert exit_code == 0
        calls = runner.run.call_args_list

        # mise
        assert call(["mise", "install", "python@3.11"]) in calls
        assert call(["mise", "use", "python@3.11"]) in calls

        # dev deps
        assert call(
            ["pipenv", "install", "--dev", *DEV_PACKAGES], cwd=str(repo)
        ) in calls

        # pre-commit install
        assert call(
            ["pipenv", "run", "pre-commit", "install"], cwd=str(repo)
        ) in calls

    def test_writes_pre_commit_config(self, repo: Path) -> None:
        (repo / "uv.lock").touch()
        (repo / "pyproject.toml").write_text(
            '[project]\nname = "test"\nrequires-python = ">=3.11"\n'
        )
        runner = _make_runner()

        run_init(repo, runner, run_all=False)

        assert (repo / ".pre-commit-config.yaml").exists()
        content = (repo / ".pre-commit-config.yaml").read_text()
        assert "ruff" in content

    def test_run_all_true_executes_pre_commit(self, repo: Path) -> None:
        (repo / "uv.lock").touch()
        (repo / "pyproject.toml").write_text(
            '[project]\nname = "test"\nrequires-python = ">=3.11"\n'
        )
        runner = _make_runner()

        run_init(repo, runner, run_all=True)

        calls = runner.run.call_args_list
        assert call(
            ["uv", "run", "pre-commit", "run", "--all-files"],
            check=False,
            cwd=str(repo),
        ) in calls

    def test_run_all_returns_pre_commit_exit_code(self, repo: Path) -> None:
        (repo / "uv.lock").touch()
        (repo / "pyproject.toml").write_text(
            '[project]\nname = "test"\nrequires-python = ">=3.11"\n'
        )
        runner = _make_runner()
        # Make the run-all call return exit code 1
        def side_effect(cmd, **kwargs):
            if "pre-commit" in cmd and "--all-files" in cmd:
                return subprocess.CompletedProcess(args=cmd, returncode=1)
            return subprocess.CompletedProcess(args=cmd, returncode=0)

        runner.run.side_effect = side_effect

        exit_code = run_init(repo, runner, run_all=True)
        assert exit_code == 1

    def test_run_all_false_skips_pre_commit_run(self, repo: Path) -> None:
        (repo / "uv.lock").touch()
        (repo / "pyproject.toml").write_text(
            '[project]\nname = "test"\nrequires-python = ">=3.11"\n'
        )
        runner = _make_runner()

        run_init(repo, runner, run_all=False)

        calls = runner.run.call_args_list
        run_all_calls = [c for c in calls if "--all-files" in str(c)]
        assert len(run_all_calls) == 0

    def test_no_manager_raises(self, repo: Path) -> None:
        runner = _make_runner()
        with pytest.raises(DetectionError):
            run_init(repo, runner)

    def test_no_prompt_skips_run_all(self, repo: Path) -> None:
        (repo / "uv.lock").touch()
        (repo / "pyproject.toml").write_text(
            '[project]\nname = "test"\nrequires-python = ">=3.11"\n'
        )
        runner = _make_runner()

        exit_code = run_init(repo, runner, run_all=None, prompt_run_all=False)

        assert exit_code == 0
        calls = runner.run.call_args_list
        run_all_calls = [c for c in calls if "--all-files" in str(c)]
        assert len(run_all_calls) == 0


class TestDecideRunAll:
    def test_explicit_true(self) -> None:
        from pc_onboard.app import _decide_run_all

        assert _decide_run_all(True, prompt_run_all=True) is True

    def test_explicit_false(self) -> None:
        from pc_onboard.app import _decide_run_all

        assert _decide_run_all(False, prompt_run_all=True) is False

    def test_no_prompt_defaults_false(self) -> None:
        from pc_onboard.app import _decide_run_all

        assert _decide_run_all(None, prompt_run_all=False) is False

    def test_non_tty_defaults_false(self) -> None:
        from pc_onboard.app import _decide_run_all

        with patch("pc_onboard.app.sys.stdin") as mock_stdin:
            mock_stdin.isatty.return_value = False
            assert _decide_run_all(None, prompt_run_all=True) is False

    def test_tty_prompt_yes(self) -> None:
        from pc_onboard.app import _decide_run_all

        with (
            patch("pc_onboard.app.sys.stdin") as mock_stdin,
            patch("builtins.input", return_value="y"),
        ):
            mock_stdin.isatty.return_value = True
            assert _decide_run_all(None, prompt_run_all=True) is True

    def test_tty_prompt_no(self) -> None:
        from pc_onboard.app import _decide_run_all

        with (
            patch("pc_onboard.app.sys.stdin") as mock_stdin,
            patch("builtins.input", return_value="n"),
        ):
            mock_stdin.isatty.return_value = True
            assert _decide_run_all(None, prompt_run_all=True) is False


class TestDevPackages:
    def test_contains_expected_packages(self) -> None:
        assert "ruff" in DEV_PACKAGES
        assert "sqlfluff" in DEV_PACKAGES
        assert "pre-commit" in DEV_PACKAGES
