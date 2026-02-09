"""Tests for pc_onboard.templates module."""

from __future__ import annotations

from pathlib import Path

import yaml

from pc_onboard.templates import get_pre_commit_config, write_pre_commit_config


class TestGetPreCommitConfig:
    def test_returns_string(self) -> None:
        config = get_pre_commit_config()
        assert isinstance(config, str)

    def test_valid_yaml(self) -> None:
        config = get_pre_commit_config()
        data = yaml.safe_load(config)
        assert "repos" in data

    def test_contains_ruff_repo(self) -> None:
        data = yaml.safe_load(get_pre_commit_config())
        repos = [r["repo"] for r in data["repos"]]
        assert any("ruff" in r for r in repos)

    def test_contains_sqlfluff_repo(self) -> None:
        data = yaml.safe_load(get_pre_commit_config())
        repos = [r["repo"] for r in data["repos"]]
        assert any("sqlfluff" in r for r in repos)

    def test_contains_prettier_repo(self) -> None:
        data = yaml.safe_load(get_pre_commit_config())
        repos = [r["repo"] for r in data["repos"]]
        assert any("prettier" in r for r in repos)

    def test_managed_by_header(self) -> None:
        config = get_pre_commit_config()
        assert "Managed by pc-onboard" in config


class TestWritePreCommitConfig:
    def test_creates_file(self, repo: Path) -> None:
        result = write_pre_commit_config(repo)
        assert result.exists()
        assert result.name == ".pre-commit-config.yaml"

    def test_content_matches_template(self, repo: Path) -> None:
        write_pre_commit_config(repo)
        written = (repo / ".pre-commit-config.yaml").read_text()
        assert written == get_pre_commit_config()

    def test_backs_up_existing_file(self, repo: Path) -> None:
        existing = repo / ".pre-commit-config.yaml"
        existing.write_text("old content\n")

        write_pre_commit_config(repo)

        # Check for timestamped backup file
        backup_files = list(repo.glob(".pre-commit-config.yaml.backup.*"))
        assert len(backup_files) == 1
        assert backup_files[0].read_text() == "old content\n"

    def test_overwrites_after_backup(self, repo: Path) -> None:
        existing = repo / ".pre-commit-config.yaml"
        existing.write_text("old content\n")

        write_pre_commit_config(repo)

        new_content = (repo / ".pre-commit-config.yaml").read_text()
        assert new_content == get_pre_commit_config()
        assert new_content != "old content\n"

    def test_returns_config_path(self, repo: Path) -> None:
        result = write_pre_commit_config(repo)
        assert result == repo / ".pre-commit-config.yaml"
