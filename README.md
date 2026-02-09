### Integration test suite (`tests/test_integration.py`)
   - Creates a temp directory with `git init`
   - Adds minimal `pyproject.toml` (uv scenario) or `Pipfile` (pipenv scenario)
   - Runs `pc-onboard init --no-prompt` with a **mock runner** that captures commands
   - Asserts:
     - Correct command sequence (mise install → mise use → dev deps → template → pre-commit install)
     - `.pre-commit-config.yaml` written with expected content
     - Commands use the correct manager prefix
   - Optional: a separate test marker (`@pytest.mark.live`) for tests that actually invoke uv/pipenv/mise (skipped in CI unless tools present)

## Overview

### Prerequisites
   - Prerequisites: mise installation link
   - Installation: how to add pc-onboard as a dev dependency from the CLI tools repo
     - uv: `uv add --dev pc-onboard@{path=...}`
     - pipenv: add to `[dev-packages]` in Pipfile with path
   - Usage:
     - `pc-onboard init` — full onboarding
     - `pc-onboard doctor` — check environment
     - Flags: `--run-all`, `--no-prompt`, `--verbose`
   - What it does (numbered list matching target state)
   - Customization: how to update the enterprise pre-commit config template

### pyproject.toml finalization
   - Minimum Python version for pc-onboard itself
   - All dependencies pinned with compatible ranges
   - Project metadata (description, license, authors)

### Acceptance Criteria

- Integration tests cover both uv and pipenv scenarios
- README is sufficient for a developer to install and run the tool
- Package installs cleanly from path in a fresh repo

---

## Version Resolution Algorithm

This is critical enough to specify explicitly.

```
Given a requires-python specifier (e.g., ">=3.11,<3.13"):

1. Parse all version constraints
2. If exact pin (==X.Y.Z): use that version as-is
3. If range with upper bound (<3.13 or <=3.12):
   - Take the upper bound minor version
   - Subtract 1 if exclusive (<3.13 → 3.12)
   - Use as minor-only: "3.12"
4. If lower bound only (>=3.11):
   - Use the lower bound minor: "3.11"
5. If no parseable version info: return None

Examples:
  ">=3.11,<3.13"  → "3.12"
  ">=3.11,<=3.12" → "3.12"
  ">=3.11"        → "3.11"
  "==3.11.8"      → "3.11.8"
  "~=3.11"        → "3.11"
```

This is deliberately conservative — it picks a known-good version rather than querying mise for the latest available.

---

## Enterprise Pre-Commit Config (Default Template)

```yaml
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
```

> **Note**: Update revs to your enterprise-approved versions before shipping. The sqlfluff dialect should match your Databricks SQL/SparkSQL usage.

---

## Testing Strategy Summary

| Layer | What | How | Speed |
|---|---|---|---|
| Unit | Detection logic, version parsing, command generation | pytest, tmp_path, no subprocess | Fast |
| Unit | mise/tooling modules | Mock runner, verify commands | Fast |
| Unit | Template content, backup behavior | tmp_path filesystem | Fast |
| Integration | Full init workflow | Temp git repo, mock runner captures command sequence | Medium |
| Live (optional) | Actual tool invocation | `@pytest.mark.live`, requires uv/pipenv/mise installed | Slow |

All tests except `@pytest.mark.live` should run without any external tools installed.

## TODO/Out of Scope

- **Auto-updating hook versions**: template has pinned revs; update manually or add `pc-onboard update-hooks` later
- **Custom hook configuration per repo**: all repos get the same enterprise config
- **Installing uv or pipenv**: these are assumed present
- **Windows support**: mise + uv/pipenv on Windows is a different problem; target macOS/Linux first
- **Config file for pc-onboard itself**: no `.pc-onboardrc` — keep it zero-config

