"""Shared fixtures for pc-onboard tests."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    """Return a temporary directory acting as a repo root."""
    return tmp_path
