"""Init orchestration — ties detection, mise, tooling, and templates together."""

from __future__ import annotations

import importlib.util
import logging
import shutil
import subprocess
import sys
from pathlib import Path

from pc_onboard.detect import DetectionError, detect_manager, detect_python_version
from pc_onboard.mise import ensure_python
from pc_onboard.runner import Runner
from pc_onboard.templates import write_pre_commit_config
from pc_onboard.tooling import Tooling

logger = logging.getLogger(__name__)

DEV_PACKAGES: list[str] = ["ruff", "sqlfluff", "pre-commit"]


class DoctorCheck:
    """Result of a single doctor diagnostic check."""

    def __init__(self, name: str, passed: bool, message: str, source: str = ""):
        self.name = name
        self.passed = passed
        self.message = message
        self.source = source


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


def run_doctor(repo_root: Path) -> list[DoctorCheck]:
    """Run comprehensive environment diagnostics.

    Returns a list of DoctorCheck results. Each check has:
      - name: short identifier
      - passed: bool indicating success
      - message: human-readable status
      - source: additional context (e.g., which file provided the version)
    """
    checks: list[DoctorCheck] = []

    # Check 1: mise installed and on PATH
    mise_path = shutil.which("mise")
    if mise_path:
        checks.append(
            DoctorCheck(
                "mise",
                True,
                f"found at {mise_path}",
            )
        )
    else:
        checks.append(
            DoctorCheck(
                "mise",
                False,
                "NOT FOUND — install from https://mise.jdx.dev",
            )
        )

    # Check 2: Package manager detected
    try:
        manager = detect_manager(repo_root)
        checks.append(
            DoctorCheck(
                "package_manager",
                True,
                f"detected: {manager}",
            )
        )
    except DetectionError as exc:
        checks.append(
            DoctorCheck(
                "package_manager",
                False,
                f"NOT DETECTED — {exc}",
            )
        )
        # Can't proceed with manager-dependent checks
        manager = None

    # Check 3: Python version resolved (and from which source)
    if manager:
        python_version = detect_python_version(repo_root, manager)
        if python_version:
            # Determine source
            source = _detect_version_source(repo_root, manager)
            checks.append(
                DoctorCheck(
                    "python_version",
                    True,
                    f"resolved: {python_version}",
                    source=source,
                )
            )
        else:
            checks.append(
                DoctorCheck(
                    "python_version",
                    False,
                    "not found in repo config files",
                )
            )
    else:
        checks.append(
            DoctorCheck(
                "python_version",
                False,
                "cannot check (no package manager detected)",
            )
        )
        python_version = None

    # Check 4: Current Python version matches resolved version
    if python_version:
        current_version = _get_current_python_version()
        if current_version:
            # Compare major.minor only
            resolved_minor = ".".join(python_version.split(".")[:2])
            current_minor = ".".join(current_version.split(".")[:2])
            if resolved_minor == current_minor:
                checks.append(
                    DoctorCheck(
                        "python_match",
                        True,
                        f"current Python {current_version} matches {python_version}",
                    )
                )
            else:
                checks.append(
                    DoctorCheck(
                        "python_match",
                        False,
                        f"current Python {current_version} does not match required {python_version}",
                    )
                )
        else:
            checks.append(
                DoctorCheck(
                    "python_match",
                    False,
                    "cannot determine current Python version",
                )
            )
    else:
        checks.append(
            DoctorCheck(
                "python_match",
                False,
                "cannot check (no Python version resolved)",
            )
        )

    # Check 5: Dev packages installed (importable)
    for package in DEV_PACKAGES:
        if _is_package_importable(package):
            checks.append(
                DoctorCheck(
                    f"package_{package}",
                    True,
                    f"{package} is installed",
                )
            )
        else:
            checks.append(
                DoctorCheck(
                    f"package_{package}",
                    False,
                    f"{package} is NOT installed",
                )
            )

    # Check 6: .pre-commit-config.yaml exists
    config_path = repo_root / ".pre-commit-config.yaml"
    if config_path.exists():
        checks.append(
            DoctorCheck(
                "pre_commit_config",
                True,
                ".pre-commit-config.yaml exists",
            )
        )
    else:
        checks.append(
            DoctorCheck(
                "pre_commit_config",
                False,
                ".pre-commit-config.yaml not found",
            )
        )

    # Check 7: Pre-commit hooks installed (.git/hooks/pre-commit exists)
    git_hook_path = repo_root / ".git" / "hooks" / "pre-commit"
    if git_hook_path.exists():
        checks.append(
            DoctorCheck(
                "pre_commit_hooks",
                True,
                "pre-commit hooks installed in .git/hooks",
            )
        )
    else:
        checks.append(
            DoctorCheck(
                "pre_commit_hooks",
                False,
                "pre-commit hooks NOT installed in .git/hooks",
            )
        )

    return checks


def _detect_version_source(repo_root: Path, manager: str) -> str:
    """Determine which file provided the Python version."""
    if manager == "pipenv":
        pipfile = repo_root / "Pipfile"
        if pipfile.exists():
            content = pipfile.read_text()
            if "python_version" in content or "python_full_version" in content:
                return "from Pipfile"
    elif manager == "uv":
        pyproject = repo_root / "pyproject.toml"
        if pyproject.exists():
            content = pyproject.read_text()
            if "requires-python" in content:
                return "from pyproject.toml"

    # Fallbacks
    if (repo_root / ".python-version").exists():
        return "from .python-version"
    if (repo_root / ".tool-versions").exists():
        return "from .tool-versions"

    return "unknown source"


def _get_current_python_version() -> str | None:
    """Get the current Python version (e.g., '3.11.8')."""
    try:
        result = subprocess.run(
            ["python", "--version"],
            capture_output=True,
            text=True,
            check=True,
        )
        # Output format: "Python 3.11.8"
        version_str = result.stdout.strip()
        if version_str.startswith("Python "):
            return version_str.split()[1]
        return None
    except (subprocess.CalledProcessError, FileNotFoundError, IndexError):
        return None


def _is_package_importable(package: str) -> bool:
    """Check if a package can be imported."""
    # Handle package name differences (e.g., pre-commit → precommit doesn't work)
    # For pre-commit, we check if it's available as a script instead
    if package == "pre-commit":
        return shutil.which("pre-commit") is not None

    # For other packages, try importing
    spec = importlib.util.find_spec(package)
    return spec is not None
