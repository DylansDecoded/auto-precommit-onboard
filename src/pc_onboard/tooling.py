"""Manager-specific command builders for uv and pipenv."""

from __future__ import annotations

from abc import ABC, abstractmethod


class ToolingError(Exception):
    """Raised for unknown or unsupported package managers."""


class Tooling(ABC):
    """Base class for package-manager-specific command generation."""

    @staticmethod
    def for_manager(manager: str) -> Tooling:
        """Factory: return the correct Tooling subclass for *manager*."""
        if manager == "uv":
            return UvTooling()
        if manager == "pipenv":
            return PipenvTooling()
        raise ToolingError(f"Unsupported package manager: {manager}")

    @abstractmethod
    def install_dev_deps(self, packages: list[str]) -> list[list[str]]:
        """Return the command list(s) needed to install dev dependencies."""

    @abstractmethod
    def run_pre_commit_install(self) -> list[str]:
        """Return the command to run `pre-commit install`."""

    @abstractmethod
    def wrap(self, cmd: list[str]) -> list[str]:
        """Wrap an arbitrary command to run inside the manager's environment."""


class UvTooling(Tooling):

    def install_dev_deps(self, packages: list[str]) -> list[list[str]]:
        return [
            ["uv", "add", "--dev", *packages],
            ["uv", "sync"],
        ]

    def run_pre_commit_install(self) -> list[str]:
        return ["uv", "run", "pre-commit", "install"]

    def wrap(self, cmd: list[str]) -> list[str]:
        return ["uv", "run", *cmd]


class PipenvTooling(Tooling):

    def install_dev_deps(self, packages: list[str]) -> list[list[str]]:
        return [
            ["pipenv", "install", "--dev", *packages],
        ]

    def run_pre_commit_install(self) -> list[str]:
        return ["pipenv", "run", "pre-commit", "install"]

    def wrap(self, cmd: list[str]) -> list[str]:
        return ["pipenv", "run", *cmd]
