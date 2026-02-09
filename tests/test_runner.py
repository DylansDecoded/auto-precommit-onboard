"""Tests for pc_onboard.runner module."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from pc_onboard.runner import Runner, RunnerError


class TestRunner:
    def test_successful_command(self) -> None:
        runner = Runner()
        result = runner.run(["echo", "hello"], capture=True)
        assert result.returncode == 0
        assert "hello" in result.stdout

    def test_failed_command_raises(self) -> None:
        runner = Runner()
        with pytest.raises(RunnerError, match="exit code"):
            runner.run(["false"])

    def test_check_false_no_raise(self) -> None:
        runner = Runner()
        result = runner.run(["false"], check=False)
        assert result.returncode != 0

    def test_capture_stderr_in_error(self) -> None:
        runner = Runner()
        with pytest.raises(RunnerError, match="No such file"):
            runner.run(["ls", "/nonexistent_path_xyz"], capture=True)

    def test_verbose_logs(self, caplog: pytest.LogCaptureFixture) -> None:
        import logging

        with caplog.at_level(logging.INFO):
            runner = Runner(verbose=True)
            runner.run(["echo", "test"], capture=True)
        assert "echo test" in caplog.text
