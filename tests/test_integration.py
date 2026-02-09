"""Integration tests for pc-onboard init workflow.

These tests simulate real repository scenarios and verify the complete
workflow from detection through pre-commit installation.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, call

import pytest

from pc_onboard.app import DEV_PACKAGES, run_init
from pc_onboard.runner import Runner


def _make_git_repo(path: Path) -> None:
    """Initialize a git repository at the given path."""
    subprocess.run(["git", "init"], cwd=str(path), check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=str(path),
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=str(path),
        check=True,
        capture_output=True,
    )


def _make_runner() -> MagicMock:
    """Return a mock Runner whose .run() succeeds by default."""
    mock = MagicMock(spec=Runner)
    mock.run.return_value = subprocess.CompletedProcess(args=[], returncode=0)
    return mock


class TestUvIntegration:
    """Integration tests for uv-based repositories."""

    def test_full_init_workflow_with_uv(self, tmp_path: Path) -> None:
        """Test complete init workflow for a uv repository."""
        # Setup: minimal uv repo
        repo = tmp_path / "test-repo"
        repo.mkdir()
        _make_git_repo(repo)

        (repo / "uv.lock").touch()
        (repo / "pyproject.toml").write_text(
            '[project]\n'
            'name = "test-project"\n'
            'version = "0.1.0"\n'
            'requires-python = ">=3.11,<3.13"\n'
        )

        runner = _make_runner()

        # Execute
        exit_code = run_init(repo, runner, run_all=False, prompt_run_all=False)

        # Verify exit code
        assert exit_code == 0

        # Verify command sequence
        calls = runner.run.call_args_list

        # 1. mise version check
        assert call(["mise", "--version"], capture=True) in calls

        # 2. mise install
        assert call(["mise", "install", "python@3.12"]) in calls

        # 3. mise use
        assert call(["mise", "use", "python@3.12"]) in calls

        # 4. uv add dev dependencies
        assert call(["uv", "add", "--dev", *DEV_PACKAGES], cwd=str(repo)) in calls

        # 5. uv sync
        assert call(["uv", "sync"], cwd=str(repo)) in calls

        # 6. pre-commit install via uv run
        assert call(["uv", "run", "pre-commit", "install"], cwd=str(repo)) in calls

        # Verify .pre-commit-config.yaml was written
        config_path = repo / ".pre-commit-config.yaml"
        assert config_path.exists()

        content = config_path.read_text()
        assert "ruff" in content
        assert "sqlfluff" in content
        assert "prettier" in content
        assert "Managed by pc-onboard" in content

    def test_uv_with_run_all_flag(self, tmp_path: Path) -> None:
        """Test that --run-all executes pre-commit on all files."""
        repo = tmp_path / "test-repo"
        repo.mkdir()
        _make_git_repo(repo)

        (repo / "uv.lock").touch()
        (repo / "pyproject.toml").write_text(
            '[project]\n'
            'name = "test"\n'
            'requires-python = ">=3.11"\n'
        )

        runner = _make_runner()

        exit_code = run_init(repo, runner, run_all=True)

        assert exit_code == 0

        calls = runner.run.call_args_list

        # Verify pre-commit run --all-files was called
        assert call(
            ["uv", "run", "pre-commit", "run", "--all-files"],
            check=False,
            cwd=str(repo),
        ) in calls


class TestPipenvIntegration:
    """Integration tests for pipenv-based repositories."""

    def test_full_init_workflow_with_pipenv(self, tmp_path: Path) -> None:
        """Test complete init workflow for a pipenv repository."""
        # Setup: minimal pipenv repo
        repo = tmp_path / "test-repo"
        repo.mkdir()
        _make_git_repo(repo)

        (repo / "Pipfile").write_text(
            '[[source]]\n'
            'url = "https://pypi.org/simple"\n'
            'verify_ssl = true\n'
            'name = "pypi"\n'
            '\n'
            '[packages]\n'
            '\n'
            '[dev-packages]\n'
            '\n'
            '[requires]\n'
            'python_version = "3.11"\n'
        )

        runner = _make_runner()

        # Execute
        exit_code = run_init(repo, runner, run_all=False, prompt_run_all=False)

        # Verify exit code
        assert exit_code == 0

        # Verify command sequence
        calls = runner.run.call_args_list

        # 1. mise checks
        assert call(["mise", "--version"], capture=True) in calls
        assert call(["mise", "install", "python@3.11"]) in calls
        assert call(["mise", "use", "python@3.11"]) in calls

        # 2. pipenv install dev dependencies
        assert call(
            ["pipenv", "install", "--dev", *DEV_PACKAGES],
            cwd=str(repo),
        ) in calls

        # 3. pre-commit install via pipenv run
        assert call(
            ["pipenv", "run", "pre-commit", "install"],
            cwd=str(repo),
        ) in calls

        # Verify .pre-commit-config.yaml was written
        config_path = repo / ".pre-commit-config.yaml"
        assert config_path.exists()

        content = config_path.read_text()
        assert "ruff" in content
        assert "sqlfluff" in content

    def test_pipenv_with_python_full_version(self, tmp_path: Path) -> None:
        """Test pipenv with python_full_version instead of python_version."""
        repo = tmp_path / "test-repo"
        repo.mkdir()
        _make_git_repo(repo)

        (repo / "Pipfile").write_text(
            '[[source]]\n'
            'url = "https://pypi.org/simple"\n'
            'verify_ssl = true\n'
            'name = "pypi"\n'
            '\n'
            '[packages]\n'
            '\n'
            '[dev-packages]\n'
            '\n'
            '[requires]\n'
            'python_full_version = "3.11.8"\n'
        )

        runner = _make_runner()

        exit_code = run_init(repo, runner, run_all=False, prompt_run_all=False)

        assert exit_code == 0

        calls = runner.run.call_args_list

        # Verify correct Python version was used
        assert call(["mise", "install", "python@3.11.8"]) in calls
        assert call(["mise", "use", "python@3.11.8"]) in calls


class TestCommandPrefixes:
    """Test that commands use correct package manager prefixes."""

    def test_uv_commands_use_uv_prefix(self, tmp_path: Path) -> None:
        """Verify all commands in uv repo use uv prefix."""
        repo = tmp_path / "test-repo"
        repo.mkdir()
        _make_git_repo(repo)

        (repo / "uv.lock").touch()
        (repo / "pyproject.toml").write_text(
            '[project]\nname = "test"\nrequires-python = ">=3.11"\n'
        )

        runner = _make_runner()
        run_init(repo, runner, run_all=False)

        calls = runner.run.call_args_list

        # Find all non-mise commands that should have uv prefix
        dev_install_calls = [c for c in calls if "add" in str(c) and "--dev" in str(c)]
        assert len(dev_install_calls) > 0
        for c in dev_install_calls:
            assert c.args[0][0] == "uv"

        sync_calls = [c for c in calls if "sync" in str(c)]
        assert len(sync_calls) > 0
        for c in sync_calls:
            assert c.args[0][0] == "uv"

        precommit_calls = [c for c in calls if "pre-commit" in str(c) and "install" in str(c)]
        assert len(precommit_calls) > 0
        for c in precommit_calls:
            assert c.args[0][:2] == ["uv", "run"]

    def test_pipenv_commands_use_pipenv_prefix(self, tmp_path: Path) -> None:
        """Verify all commands in pipenv repo use pipenv prefix."""
        repo = tmp_path / "test-repo"
        repo.mkdir()
        _make_git_repo(repo)

        (repo / "Pipfile").write_text(
            '[requires]\npython_version = "3.11"\n'
        )

        runner = _make_runner()
        run_init(repo, runner, run_all=False)

        calls = runner.run.call_args_list

        # Find pipenv-specific calls
        install_calls = [c for c in calls if "install" in str(c) and "--dev" in str(c)]
        assert len(install_calls) > 0
        for c in install_calls:
            assert c.args[0][0] == "pipenv"

        # Find pre-commit install calls (look for "pre-commit" AND "install" in the command)
        precommit_calls = [c for c in calls if "pre-commit" in str(c) and "install" in str(c) and "run" in str(c)]
        assert len(precommit_calls) > 0
        for c in precommit_calls:
            assert c.args[0][:2] == ["pipenv", "run"]


class TestConfigBackup:
    """Test that existing .pre-commit-config.yaml files are backed up."""

    def test_existing_config_is_backed_up(self, tmp_path: Path) -> None:
        """Verify that existing config is backed up before overwriting."""
        repo = tmp_path / "test-repo"
        repo.mkdir()
        _make_git_repo(repo)

        (repo / "uv.lock").touch()
        (repo / "pyproject.toml").write_text(
            '[project]\nname = "test"\nrequires-python = ">=3.11"\n'
        )

        # Create existing config
        existing_config = "# old config\nrepos: []"
        (repo / ".pre-commit-config.yaml").write_text(existing_config)

        runner = _make_runner()
        run_init(repo, runner, run_all=False)

        # Check backup was created
        backup_files = list(repo.glob(".pre-commit-config.yaml.backup.*"))
        assert len(backup_files) == 1

        # Verify backup has old content
        assert backup_files[0].read_text() == existing_config

        # Verify new config was written
        new_config = (repo / ".pre-commit-config.yaml").read_text()
        assert "Managed by pc-onboard" in new_config


@pytest.mark.live
class TestLiveIntegration:
    """Live integration tests that actually invoke tools.

    These tests require mise, uv, and git to be installed.
    They are skipped by default and run with: pytest -m live
    """

    def test_live_uv_init(self, tmp_path: Path) -> None:
        """Test real init workflow with actual tool invocations."""
        # Skip if mise not available
        if not subprocess.run(
            ["which", "mise"],
            capture_output=True,
        ).returncode == 0:
            pytest.skip("mise not installed")

        repo = tmp_path / "live-test-repo"
        repo.mkdir()
        _make_git_repo(repo)

        (repo / "uv.lock").touch()
        (repo / "pyproject.toml").write_text(
            '[project]\n'
            'name = "live-test"\n'
            'requires-python = ">=3.11,<3.13"\n'
        )

        # Use real runner (no mocking)
        runner = Runner(verbose=True)

        # Execute (this will actually run mise, uv, etc.)
        exit_code = run_init(repo, runner, run_all=False, prompt_run_all=False)

        # Verify success
        assert exit_code == 0

        # Verify artifacts
        assert (repo / ".pre-commit-config.yaml").exists()
        assert (repo / ".git" / "hooks" / "pre-commit").exists()

        # Verify Python version was pinned
        tool_versions = repo / ".tool-versions"
        if tool_versions.exists():
            content = tool_versions.read_text()
            assert "python" in content
