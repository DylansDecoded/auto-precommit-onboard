"""mise install/use operations for Python version management."""

from __future__ import annotations

import logging

from pc_onboard.runner import Runner, RunnerError

logger = logging.getLogger(__name__)


class MiseError(Exception):
    """Raised when a mise operation fails."""


def ensure_python(version: str | None, runner: Runner) -> None:
    """Install and activate a Python version via mise.

    If *version* is None, logs a warning and returns without action.
    Raises MiseError if mise is not installed or a mise command fails.
    """
    if version is None:
        logger.warning("No Python version specified — skipping mise setup.")
        return

    # Verify mise is available
    try:
        runner.run(["mise", "--version"], capture=True)
    except (RunnerError, FileNotFoundError) as exc:
        raise MiseError(
            "mise is not installed or not on PATH. "
            "Install it from https://mise.jdx.dev"
        ) from exc

    # Install the requested Python version
    try:
        runner.run(["mise", "install", f"python@{version}"])
    except RunnerError as exc:
        raise MiseError(
            f"Failed to install Python {version} via mise: {exc}"
        ) from exc

    # Pin the version for this repo
    try:
        runner.run(["mise", "use", f"python@{version}"])
    except RunnerError as exc:
        raise MiseError(
            f"Failed to activate Python {version} via mise: {exc}"
        ) from exc
