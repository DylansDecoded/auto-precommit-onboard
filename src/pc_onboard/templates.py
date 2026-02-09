"""Enterprise .pre-commit-config.yaml template."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

_PRE_COMMIT_CONFIG = """\
# Managed by pc-onboard — do not edit manually.
# To update: run `pc-onboard init` again.
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.6
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/sqlfluff/sqlfluff
    rev: 3.3.1
    hooks:
      - id: sqlfluff-lint
        args: [--dialect, sparksql]
      - id: sqlfluff-fix
        args: [--dialect, sparksql]

  - repo: https://github.com/pre-commit/mirrors-prettier
    rev: v4.0.0-alpha.8
    hooks:
      - id: prettier
        types_or: [yaml, markdown, json]
"""


def get_pre_commit_config() -> str:
    """Return the enterprise standard .pre-commit-config.yaml content."""
    return _PRE_COMMIT_CONFIG


def write_pre_commit_config(repo_root: Path) -> Path:
    """Write the enterprise .pre-commit-config.yaml to *repo_root*.

    If the file already exists, backs it up to .pre-commit-config.yaml.backup.TIMESTAMP
    before overwriting. Returns the path to the written config file.
    """
    config_path = repo_root / ".pre-commit-config.yaml"

    if config_path.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = repo_root / f".pre-commit-config.yaml.backup.{timestamp}"
        config_path.rename(backup_path)
        logger.info("Backed up existing config to %s", backup_path)

    config_path.write_text(get_pre_commit_config())
    logger.info("Wrote %s", config_path)
    return config_path
