"""Thin wrapper around subprocess.run for testability."""

from __future__ import annotations

import logging
import subprocess

logger = logging.getLogger(__name__)


class RunnerError(Exception):
    """Raised when a subprocess command fails."""

    def __init__(self, cmd: list[str], returncode: int, stderr: str = "") -> None:
        self.cmd = cmd
        self.returncode = returncode
        self.stderr = stderr
        detail = f": {stderr.strip()}" if stderr.strip() else ""
        super().__init__(
            f"Command {cmd} failed with exit code {returncode}{detail}"
        )


class Runner:
    """Single point of subprocess execution."""

    def __init__(self, *, verbose: bool = False) -> None:
        self.verbose = verbose

    def run(
        self,
        cmd: list[str],
        *,
        check: bool = True,
        capture: bool = False,
        cwd: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        if self.verbose:
            logger.info("$ %s", " ".join(cmd))

        result = subprocess.run(
            cmd,
            check=False,
            capture_output=capture,
            text=True,
            cwd=cwd,
        )

        if check and result.returncode != 0:
            stderr = result.stderr if capture else ""
            raise RunnerError(cmd, result.returncode, stderr)

        return result
