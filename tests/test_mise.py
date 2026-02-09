"""Tests for pc_onboard.mise module."""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, call

import pytest

from pc_onboard.mise import MiseError, ensure_python
from pc_onboard.runner import Runner, RunnerError


def _make_runner() -> MagicMock:
    """Return a mock Runner whose .run() succeeds by default."""
    return MagicMock(spec=Runner)


class TestEnsurePython:
    def test_installs_and_uses_version(self) -> None:
        runner = _make_runner()
        ensure_python("3.12", runner)

        assert runner.run.call_args_list == [
            call(["mise", "--version"], capture=True),
            call(["mise", "install", "python@3.12"]),
            call(["mise", "use", "python@3.12"]),
        ]

    def test_full_version_string(self) -> None:
        runner = _make_runner()
        ensure_python("3.11.8", runner)

        assert runner.run.call_args_list == [
            call(["mise", "--version"], capture=True),
            call(["mise", "install", "python@3.11.8"]),
            call(["mise", "use", "python@3.11.8"]),
        ]

    def test_none_version_skips(self, caplog: pytest.LogCaptureFixture) -> None:
        runner = _make_runner()
        with caplog.at_level(logging.WARNING):
            ensure_python(None, runner)

        runner.run.assert_not_called()
        assert "skipping" in caplog.text.lower()

    def test_mise_not_installed_raises(self) -> None:
        runner = _make_runner()
        runner.run.side_effect = FileNotFoundError("mise not found")

        with pytest.raises(MiseError, match="not installed"):
            ensure_python("3.12", runner)

    def test_mise_version_check_fails_raises(self) -> None:
        runner = _make_runner()
        runner.run.side_effect = RunnerError(["mise", "--version"], 1)

        with pytest.raises(MiseError, match="not installed"):
            ensure_python("3.12", runner)

    def test_mise_install_fails_raises(self) -> None:
        runner = _make_runner()
        # First call (--version) succeeds, second (install) fails
        runner.run.side_effect = [
            None,
            RunnerError(["mise", "install", "python@3.12"], 1, "install error"),
        ]

        with pytest.raises(MiseError, match="Failed to install"):
            ensure_python("3.12", runner)

    def test_mise_use_fails_raises(self) -> None:
        runner = _make_runner()
        # First two calls succeed, third (use) fails
        runner.run.side_effect = [
            None,
            None,
            RunnerError(["mise", "use", "python@3.12"], 1, "use error"),
        ]

        with pytest.raises(MiseError, match="Failed to activate"):
            ensure_python("3.12", runner)
