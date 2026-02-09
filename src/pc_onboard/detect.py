"""Package manager detection and Python version resolution."""

from __future__ import annotations

import configparser
import re
from pathlib import Path
from typing import Literal


class DetectionError(Exception):
    """Raised when package manager detection fails."""


def detect_manager(repo_root: Path) -> Literal["uv", "pipenv"]:
    """Detect whether the repo uses uv or pipenv.

    Detection order:
      1. uv.lock present → "uv"
      2. Pipfile.lock or Pipfile present → "pipenv"
      3. Neither → raise DetectionError
    """
    if (repo_root / "uv.lock").exists():
        return "uv"
    if (repo_root / "Pipfile.lock").exists() or (repo_root / "Pipfile").exists():
        return "pipenv"
    raise DetectionError(
        "Could not detect package manager. "
        "Expected uv.lock (uv) or Pipfile/Pipfile.lock (pipenv) in "
        f"{repo_root}"
    )


def detect_python_version(repo_root: Path, manager: str) -> str | None:
    """Resolve the required Python version from repo config files.

    Lookup order depends on the manager:
      - pipenv: Pipfile → .python-version → .tool-versions
      - uv: pyproject.toml → .python-version → .tool-versions

    Returns a version string (e.g. "3.12") or None if nothing found.
    """
    if manager == "pipenv":
        version = _version_from_pipfile(repo_root / "Pipfile")
        if version:
            return version
    elif manager == "uv":
        version = _version_from_pyproject(repo_root / "pyproject.toml")
        if version:
            return version

    # Fallbacks shared by both managers
    version = _version_from_python_version_file(repo_root / ".python-version")
    if version:
        return version

    version = _version_from_tool_versions(repo_root / ".tool-versions")
    if version:
        return version

    return None


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _version_from_pipfile(path: Path) -> str | None:
    """Extract python_version or python_full_version from a Pipfile."""
    if not path.exists():
        return None

    config = configparser.ConfigParser()
    config.read(path)

    if config.has_option("requires", "python_full_version"):
        return config.get("requires", "python_full_version")
    if config.has_option("requires", "python_version"):
        return config.get("requires", "python_version")

    return None


def _version_from_pyproject(path: Path) -> str | None:
    """Extract and resolve requires-python from pyproject.toml."""
    if not path.exists():
        return None

    try:
        import tomllib
    except ModuleNotFoundError:  # Python < 3.11
        return None

    with open(path, "rb") as f:
        data = tomllib.load(f)

    specifier = data.get("project", {}).get("requires-python")
    if not specifier:
        return None

    return _resolve_version_specifier(specifier)


def _version_from_python_version_file(path: Path) -> str | None:
    """Read version from a .python-version file."""
    if not path.exists():
        return None
    text = path.read_text().strip()
    return text if text else None


def _version_from_tool_versions(path: Path) -> str | None:
    """Read python version from a .tool-versions file."""
    if not path.exists():
        return None
    for line in path.read_text().splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0] == "python":
            return parts[1]
    return None


def _resolve_version_specifier(specifier: str) -> str:
    """Resolve a PEP 440 version specifier to a concrete minor version.

    Examples:
      ">=3.11,<3.13"  → "3.12"
      ">=3.11,<=3.12" → "3.12"
      ">=3.11"        → "3.11"
      "==3.11.8"      → "3.11.8"
      "~=3.11"        → "3.11"
    """
    specifier = specifier.strip()

    # Exact pin
    exact = re.search(r"==\s*([\d.]+)", specifier)
    if exact:
        return exact.group(1)

    # Compatible release (~=3.11 means >=3.11, <4.0 effectively)
    compat = re.search(r"~=\s*([\d.]+)", specifier)
    if compat:
        return compat.group(1)

    upper: tuple[int, int] | None = None
    upper_inclusive = False
    lower: tuple[int, int] | None = None

    for constraint in specifier.split(","):
        constraint = constraint.strip()

        m = re.match(r"<=\s*(\d+)\.(\d+)", constraint)
        if m:
            upper = (int(m.group(1)), int(m.group(2)))
            upper_inclusive = True
            continue

        m = re.match(r"<\s*(\d+)\.(\d+)", constraint)
        if m:
            upper = (int(m.group(1)), int(m.group(2)))
            upper_inclusive = False
            continue

        m = re.match(r">=\s*(\d+)\.(\d+)", constraint)
        if m:
            lower = (int(m.group(1)), int(m.group(2)))
            continue

    # Range with upper bound: pick highest minor below upper
    if upper is not None:
        major, minor = upper
        if upper_inclusive:
            return f"{major}.{minor}"
        else:
            return f"{major}.{minor - 1}"

    # Lower bound only: use the lower bound
    if lower is not None:
        major, minor = lower
        return f"{major}.{minor}"

    # Couldn't parse anything useful — try to extract any version-like string
    fallback = re.search(r"(\d+\.\d+(?:\.\d+)?)", specifier)
    if fallback:
        return fallback.group(1)

    return specifier
