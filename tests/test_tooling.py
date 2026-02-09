"""Tests for pc_onboard.tooling module."""

from __future__ import annotations

import pytest

from pc_onboard.tooling import PipenvTooling, Tooling, ToolingError, UvTooling


class TestToolingFactory:
    def test_uv_returns_uv_tooling(self) -> None:
        assert isinstance(Tooling.for_manager("uv"), UvTooling)

    def test_pipenv_returns_pipenv_tooling(self) -> None:
        assert isinstance(Tooling.for_manager("pipenv"), PipenvTooling)

    def test_unknown_raises(self) -> None:
        with pytest.raises(ToolingError, match="Unsupported"):
            Tooling.for_manager("poetry")


class TestUvTooling:
    def setup_method(self) -> None:
        self.tooling = UvTooling()

    def test_install_dev_deps(self) -> None:
        cmds = self.tooling.install_dev_deps(["ruff", "sqlfluff", "pre-commit"])
        assert cmds == [
            ["uv", "add", "--dev", "ruff", "sqlfluff", "pre-commit"],
            ["uv", "sync"],
        ]

    def test_run_pre_commit_install(self) -> None:
        assert self.tooling.run_pre_commit_install() == [
            "uv", "run", "pre-commit", "install"
        ]

    def test_wrap(self) -> None:
        assert self.tooling.wrap(["pre-commit", "run", "--all-files"]) == [
            "uv", "run", "pre-commit", "run", "--all-files"
        ]


class TestPipenvTooling:
    def setup_method(self) -> None:
        self.tooling = PipenvTooling()

    def test_install_dev_deps(self) -> None:
        cmds = self.tooling.install_dev_deps(["ruff", "sqlfluff", "pre-commit"])
        assert cmds == [
            ["pipenv", "install", "--dev", "ruff", "sqlfluff", "pre-commit"],
        ]

    def test_run_pre_commit_install(self) -> None:
        assert self.tooling.run_pre_commit_install() == [
            "pipenv", "run", "pre-commit", "install"
        ]

    def test_wrap(self) -> None:
        assert self.tooling.wrap(["pre-commit", "run", "--all-files"]) == [
            "pipenv", "run", "pre-commit", "run", "--all-files"
        ]
