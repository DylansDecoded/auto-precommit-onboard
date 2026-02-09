"""Tests for pc_onboard.detect module."""

from __future__ import annotations

from pathlib import Path

import pytest

from pc_onboard.detect import (
    DetectionError,
    _resolve_version_specifier,
    detect_manager,
    detect_python_version,
)


# ---------------------------------------------------------------------------
# detect_manager
# ---------------------------------------------------------------------------


class TestDetectManager:
    def test_uv_lock_detected(self, repo: Path) -> None:
        (repo / "uv.lock").touch()
        assert detect_manager(repo) == "uv"

    def test_pipfile_lock_detected(self, repo: Path) -> None:
        (repo / "Pipfile.lock").touch()
        assert detect_manager(repo) == "pipenv"

    def test_pipfile_without_lock_detected(self, repo: Path) -> None:
        (repo / "Pipfile").touch()
        assert detect_manager(repo) == "pipenv"

    def test_uv_takes_precedence_over_pipfile(self, repo: Path) -> None:
        (repo / "uv.lock").touch()
        (repo / "Pipfile").touch()
        assert detect_manager(repo) == "uv"

    def test_neither_raises(self, repo: Path) -> None:
        with pytest.raises(DetectionError, match="Could not detect"):
            detect_manager(repo)


# ---------------------------------------------------------------------------
# detect_python_version — pipenv
# ---------------------------------------------------------------------------


class TestDetectPythonVersionPipenv:
    def test_python_version_from_pipfile(self, repo: Path) -> None:
        (repo / "Pipfile").write_text(
            "[requires]\npython_version = 3.11\n"
        )
        assert detect_python_version(repo, "pipenv") == "3.11"

    def test_python_full_version_from_pipfile(self, repo: Path) -> None:
        (repo / "Pipfile").write_text(
            "[requires]\npython_full_version = 3.11.8\n"
        )
        assert detect_python_version(repo, "pipenv") == "3.11.8"

    def test_full_version_preferred_over_short(self, repo: Path) -> None:
        (repo / "Pipfile").write_text(
            "[requires]\npython_full_version = 3.11.8\npython_version = 3.11\n"
        )
        assert detect_python_version(repo, "pipenv") == "3.11.8"

    def test_fallback_to_python_version_file(self, repo: Path) -> None:
        (repo / "Pipfile").write_text("[packages]\n")
        (repo / ".python-version").write_text("3.12\n")
        assert detect_python_version(repo, "pipenv") == "3.12"

    def test_fallback_to_tool_versions(self, repo: Path) -> None:
        (repo / "Pipfile").write_text("[packages]\n")
        (repo / ".tool-versions").write_text("python 3.12.1\nnode 20.0.0\n")
        assert detect_python_version(repo, "pipenv") == "3.12.1"

    def test_returns_none_when_nothing_found(self, repo: Path) -> None:
        (repo / "Pipfile").write_text("[packages]\n")
        assert detect_python_version(repo, "pipenv") is None


# ---------------------------------------------------------------------------
# detect_python_version — uv
# ---------------------------------------------------------------------------


class TestDetectPythonVersionUv:
    def test_requires_python_range(self, repo: Path) -> None:
        (repo / "pyproject.toml").write_text(
            '[project]\nname = "foo"\nrequires-python = ">=3.11,<3.13"\n'
        )
        assert detect_python_version(repo, "uv") == "3.12"

    def test_requires_python_lower_only(self, repo: Path) -> None:
        (repo / "pyproject.toml").write_text(
            '[project]\nname = "foo"\nrequires-python = ">=3.11"\n'
        )
        assert detect_python_version(repo, "uv") == "3.11"

    def test_requires_python_exact(self, repo: Path) -> None:
        (repo / "pyproject.toml").write_text(
            '[project]\nname = "foo"\nrequires-python = "==3.11.8"\n'
        )
        assert detect_python_version(repo, "uv") == "3.11.8"

    def test_requires_python_inclusive_upper(self, repo: Path) -> None:
        (repo / "pyproject.toml").write_text(
            '[project]\nname = "foo"\nrequires-python = ">=3.11,<=3.12"\n'
        )
        assert detect_python_version(repo, "uv") == "3.12"

    def test_requires_python_compatible_release(self, repo: Path) -> None:
        (repo / "pyproject.toml").write_text(
            '[project]\nname = "foo"\nrequires-python = "~=3.11"\n'
        )
        assert detect_python_version(repo, "uv") == "3.11"

    def test_fallback_to_python_version_file(self, repo: Path) -> None:
        (repo / "pyproject.toml").write_text('[project]\nname = "foo"\n')
        (repo / ".python-version").write_text("3.12\n")
        assert detect_python_version(repo, "uv") == "3.12"

    def test_returns_none_when_nothing_found(self, repo: Path) -> None:
        (repo / "pyproject.toml").write_text('[project]\nname = "foo"\n')
        assert detect_python_version(repo, "uv") is None


# ---------------------------------------------------------------------------
# _resolve_version_specifier (direct unit tests)
# ---------------------------------------------------------------------------


class TestResolveVersionSpecifier:
    @pytest.mark.parametrize(
        "specifier, expected",
        [
            (">=3.11,<3.13", "3.12"),
            (">=3.11,<=3.12", "3.12"),
            (">=3.11", "3.11"),
            ("==3.11.8", "3.11.8"),
            ("~=3.11", "3.11"),
            (">=3.10,<3.12", "3.11"),
        ],
    )
    def test_specifier_resolution(self, specifier: str, expected: str) -> None:
        assert _resolve_version_specifier(specifier) == expected
