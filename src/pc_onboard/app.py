"""Init orchestration — ties detection, mise, tooling, and templates together."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from pc_onboard.detect import detect_manager, detect_python_version
from pc_onboard.mise import ensure_python
from pc_onboard.runner import Runner
from pc_onboard.templates import write_pre_commit_config
from pc_onboard.tooling import Tooling

logger = logging.getLogger(__name__)

DEV_PACKAGES: list[str] = ["ruff", "sqlfluff", "pre-commit"]


def run_init(
    repo_root: Path,
    runner: Runner,
    *,
    run_all: bool | None = None,
    prompt_run_all: bool = True,
) -> int:
    """Execute the full onboarding workflow. Returns an exit code (0 = success).

    Steps:
      1. Detect package manager
      2. Resolve Python version
      3. Install/pin Python via mise
      4. Install dev dependencies
      5. Write .pre-commit-config.yaml
      6. Run pre-commit install
      7. Optionally run pre-commit on all files
    """
    manager = detect_manager(repo_root)
    logger.info("Detected package manager: %s", manager)

    python_version = detect_python_version(repo_root, manager)
    ensure_python(python_version, runner)

    tooling = Tooling.for_manager(manager)

    # Install dev deps
    for cmd in tooling.install_dev_deps(DEV_PACKAGES):
        runner.run(cmd, cwd=str(repo_root))

    # Write enterprise pre-commit config
    write_pre_commit_config(repo_root)

    # Install pre-commit hooks
    runner.run(tooling.run_pre_commit_install(), cwd=str(repo_root))

    # Handle run-all logic
    should_run_all = _decide_run_all(run_all, prompt_run_all)
    if should_run_all:
        cmd = tooling.wrap(["pre-commit", "run", "--all-files"])
        result = runner.run(cmd, check=False, cwd=str(repo_root))
        return result.returncode

    return 0


def _decide_run_all(run_all: bool | None, prompt_run_all: bool) -> bool:
    """Determine whether to run pre-commit on all files."""
    # Explicit flag takes precedence
    if run_all is not None:
        return run_all

    # If prompting is disabled, default to no
    if not prompt_run_all:
        return False

    # Only prompt if we're in an interactive terminal
    if not sys.stdin.isatty():
        return False

    try:
        answer = input("Run pre-commit on all files now? [y/N] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return False

    return answer in ("y", "yes")
