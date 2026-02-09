# pc-onboard — Implementation Plan

## Overview

`pc-onboard` is a CLI tool that automates repository onboarding for enterprise pre-commit standards. It detects the repo's package manager (uv or pipenv), resolves the required Python version, configures mise to manage that version locally, installs dev dependencies, writes the standard `.pre-commit-config.yaml`, and runs `pre-commit install`.

This package lives in the enterprise CLI tools monorepo alongside other CLI tools that engineers install into their project repos.

## Prerequisites & Assumptions

- **mise** is the only tool a user must install manually. Everything else flows from there.
- **uv or pipenv** is always present in target repos — detection, not installation.
- **mise manages Python versions** so users never touch their global Python. The tool runs `mise use python@X.Y` to pin the repo-local version.
- Target repos always have either a `Pipfile` (pipenv) or `pyproject.toml` (uv) declaring their Python requirement.

---

## Target State

After a user runs `pc-onboard init` in their repo:

1. Package manager detected (uv or pipenv)
2. Required Python version resolved from repo config files
3. `mise install python@X.Y` and `mise use python@X.Y` executed
4. Dev dependencies installed via detected manager:
   - **uv**: `uv add --dev ruff sqlfluff pre-commit` → `uv sync`
   - **pipenv**: `pipenv install --dev ruff sqlfluff pre-commit`
5. `.pre-commit-config.yaml` written with enterprise standard hooks
6. `pre-commit install` executed through the package manager
7. Interactive prompt (TTY only): run `pre-commit run --all-files`?
   - `--run-all` / `--no-run-all` flags for non-interactive control

---

## Package Structure

```
packages/pc-onboard/
├── pyproject.toml
├── README.md
├── PLAN.md
├── src/
│   └── pc_onboard/
│       ├── __init__.py
│       ├── cli.py              # Typer app, commands, flags
│       ├── app.py              # Orchestration logic (init workflow)
│       ├── detect.py           # Package manager + Python version detection
│       ├── tooling.py          # Manager-specific command builders (uv/pipenv)
│       ├── mise.py             # mise install/use operations
│       ├── templates.py        # .pre-commit-config.yaml template
│       └── runner.py           # Subprocess execution wrapper
└── tests/
    ├── conftest.py             # Shared fixtures (temp repos, mock runners)
    ├── test_detect.py
    ├── test_tooling.py
    ├── test_mise.py
    ├── test_templates.py
    ├── test_app.py             # Orchestration integration tests
    └── test_cli.py             # CLI invocation tests
```

### Module Responsibilities

| Module | Responsibility |
|---|---|
| `cli.py` | Typer commands (`init`, `doctor`), flag parsing, TTY prompt, exit codes |
| `app.py` | `run_init()` orchestrator — calls detect, mise, tooling, templates in order |
| `detect.py` | Determine package manager (uv/pipenv) and resolve required Python version |
| `tooling.py` | `Tooling` class with `.install_dev_deps()`, `.run_pre_commit_install()`, `.wrap(cmd)` per manager |
| `mise.py` | `ensure_python(version)` — runs `mise install` + `mise use` |
| `templates.py` | Returns the enterprise `.pre-commit-config.yaml` content as a string |
| `runner.py` | Thin wrapper around `subprocess.run` for testability (easy to mock) |

---

## ~~Phase 1 — Skeleton + Detection~~ ✓

~~**Goal**: Package scaffolding, CLI entrypoint, and reliable detection of package manager and Python version.~~

### ~~Tasks~~

1. ~~**Create `pyproject.toml`**~~
2. ~~**Implement `detect.py`** — manager detection + Python version resolution~~
3. ~~**Implement `cli.py` with `doctor` command**~~
4. ~~**Unit tests for detection**~~

### ~~Acceptance Criteria — All met~~

---

## ~~Phase 2 — mise Integration + Tooling Commands~~ ✓

~~**Goal**: mise operations and manager-specific command generation.~~

### ~~Tasks~~

1. ~~**Implement `runner.py`**~~
2. ~~**Implement `mise.py`**~~
3. ~~**Implement `tooling.py`**~~
4. ~~**Unit tests** — 48/48 tests passing~~

### ~~Acceptance Criteria — All met~~

---

## ~~Phase 3 — Template + Init Orchestration~~ ✓

~~**Goal**: The `.pre-commit-config.yaml` template and the `init` command that ties everything together.~~

### ~~Tasks~~

1. ~~**Implement `templates.py`**~~ ✓
   - ~~`get_pre_commit_config() -> str` — returns the enterprise standard YAML~~
   - ~~`write_pre_commit_config(repo_root: Path) -> Path` — writes file with backup~~

2. ~~**Implement `app.py` — the `run_init()` orchestrator**~~ ✓
   - ~~Full workflow: detection → mise → dev deps → template → pre-commit install → run-all prompt~~

3. ~~**Wire `cli.py` `init` command**~~ ✓
   - ~~Flags: `--run-all / --no-run-all`, `--no-prompt`, `--verbose`~~
   - ~~TTY detection and interactive prompt~~
   - ~~Error handling for DetectionError, MiseError, ToolingError, RunnerError~~

4. ~~**Define `DEV_PACKAGES` constant**~~ ✓
   - ~~`["ruff", "sqlfluff", "pre-commit"]` in app.py~~

5. ~~**Tests**~~ ✓
   - ~~`test_templates.py`: 11 tests (YAML validity, backup behavior)~~
   - ~~`test_app.py`: 15 tests (orchestration, run-all logic)~~
   - ~~`test_cli.py`: 8 tests (CLI invocation, flags, exit codes)~~

### ~~Acceptance Criteria — All met (79 tests passing)~~

---

## ~~Phase 4 — Doctor Command + Error Handling Polish~~ ✓

~~**Goal**: A diagnostic command and robust error handling for real-world usage.~~

### ~~Tasks~~

1. ~~**Expand `pc-onboard doctor`**~~ ✓
   - ~~Comprehensive checks with pass/fail status (✓/✗ indicators):~~
     - ~~`mise` installed and on PATH~~
     - ~~Package manager detected (uv or pipenv)~~
     - ~~Python version resolved (with source information)~~
     - ~~Current Python version matches resolved version~~
     - ~~Dev packages installed (ruff, sqlfluff, pre-commit)~~
     - ~~`.pre-commit-config.yaml` exists~~
     - ~~Pre-commit hooks installed (`.git/hooks/pre-commit` exists)~~
   - ~~Exit code: 0 if all pass, 1 if any fail~~
   - ~~Color-coded output (green for pass, red for fail)~~

2. ~~**Error handling improvements**~~ ✓
   - ~~Custom exceptions already implemented: `DetectionError`, `MiseError`, `ToolingError`, `RunnerError`~~
   - ~~`runner.py`: stderr capture already implemented~~
   - ~~`cli.py`: comprehensive exception handling with actionable messages~~
   - ~~`--verbose` flag: implemented in `init` command, shows commands before execution~~

3. ~~**Tests**~~ ✓
   - ~~9 new doctor tests in test_app.py (24 total)~~
   - ~~5 updated CLI tests for doctor command~~
   - ~~Test coverage: all checks passing, mise not found, no package manager, version mismatch, packages missing, config missing, hooks not installed, verbose mode~~

### ~~Acceptance Criteria — All met (90 tests passing)~~

---

## ~~Phase 5 — Integration Testing + README~~ ✓

~~**Goal**: Real-world integration tests and documentation for consumers.~~

### ~~Tasks~~

1. ~~**Integration test suite** (`tests/test_integration.py`)~~ ✓
   - ~~Creates a temp directory with `git init`~~
   - ~~Adds minimal `pyproject.toml` (uv scenario) or `Pipfile` (pipenv scenario)~~
   - ~~Runs `pc-onboard init --no-prompt` with a **mock runner** that captures commands~~
   - ~~Asserts:~~
     - ~~Correct command sequence (mise install → mise use → dev deps → template → pre-commit install)~~
     - ~~`.pre-commit-config.yaml` written with expected content~~
     - ~~Commands use the correct manager prefix~~
   - ~~Optional: a separate test marker (`@pytest.mark.live`) for tests that actually invoke uv/pipenv/mise (skipped in CI unless tools present)~~
   - ~~7 integration tests covering uv, pipenv, command prefixes, and config backup scenarios~~

2. ~~**README.md**~~ ✓
   - ~~Prerequisites: mise installation link~~
   - ~~Installation: how to add pc-onboard as a dev dependency~~
     - ~~uv: `uv add --dev pc-onboard@{path=...}`~~
     - ~~pipenv: add to `[dev-packages]` in Pipfile with path~~
   - ~~Usage:~~
     - ~~`pc-onboard init` — full onboarding~~
     - ~~`pc-onboard doctor` — check environment~~
     - ~~Flags: `--run-all`, `--no-prompt`, `--verbose`~~
   - ~~What it does (numbered list matching target state)~~
   - ~~Customization: how to update the enterprise pre-commit config template~~
   - ~~Architecture, development, and troubleshooting sections~~

3. ~~**pyproject.toml finalization**~~ ✓
   - ~~Minimum Python version: `>=3.11`~~
   - ~~Dependencies pinned with compatible ranges (`typer>=0.9,<1.0`)~~
   - ~~Project metadata: description, license (MIT), authors, keywords, classifiers~~
   - ~~Project URLs: homepage, repository, issues~~
   - ~~pytest markers for live tests~~

4. ~~**Bug fixes**~~ ✓
   - ~~Fixed Pipfile quote stripping in `_version_from_pipfile()` (removed quotes from parsed values)~~
   - ~~Fixed backup file naming to use timestamps (`.pre-commit-config.yaml.backup.TIMESTAMP`)~~
   - ~~Updated integration tests to match timestamped backup behavior~~

### ~~Acceptance Criteria — All met (97 tests passing)~~

- ~~Integration tests cover both uv and pipenv scenarios~~ ✓
- ~~README is sufficient for a developer to install and run the tool~~ ✓
- ~~Package installs cleanly from path in a fresh repo~~ ✓

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

---

## Out of Scope (for now)

- **Auto-updating hook versions**: template has pinned revs; update manually or add `pc-onboard update-hooks` later
- **Custom hook configuration per repo**: all repos get the same enterprise config
- **Installing uv or pipenv**: these are assumed present
- **Windows support**: mise + uv/pipenv on Windows is a different problem; target macOS/Linux first
- **Config file for pc-onboard itself**: no `.pc-onboardrc` — keep it zero-config