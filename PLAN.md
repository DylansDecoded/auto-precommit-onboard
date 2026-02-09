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

## Phase 1 — Skeleton + Detection

**Goal**: Package scaffolding, CLI entrypoint, and reliable detection of package manager and Python version.

### Tasks

1. **Create `pyproject.toml`**
   - Package name: `pc-onboard`
   - Console script: `pc-onboard = "pc_onboard.cli:app"`
   - Dependencies: `typer>=0.9`
   - Dev dependencies: `pytest`, `pytest-tmp-files` (or similar)

2. **Implement `detect.py`**
   - `detect_manager(repo_root: Path) -> Literal["uv", "pipenv"]`
     - `uv.lock` present → `"uv"`
     - `Pipfile.lock` or `Pipfile` present → `"pipenv"`
     - Neither → raise `DetectionError` with clear message
   - `detect_python_version(repo_root: Path, manager: str) -> str | None`
     - **pipenv path**: Parse `Pipfile` → `[requires].python_version` (e.g., `"3.11"`) or `python_full_version`
     - **uv path**: Parse `pyproject.toml` → `[project].requires-python` (e.g., `">=3.11,<3.13"`)
     - **Fallback**: `.python-version` file, then `.tool-versions` file
     - **Version resolution policy** (for specifier ranges):
       - `>=3.11,<3.13` → `"3.12"` (highest minor below upper bound)
       - `>=3.11` (no upper) → `"3.11"` (use the lower bound — conservative, predictable)
       - Exact: `==3.11.8` → `"3.11.8"`
     - Returns `None` if nothing found (caller decides whether to warn or fail)

3. **Implement `cli.py` with `doctor` command**
   - `pc-onboard doctor`: prints detected manager, Python version, mise availability
   - Useful for debugging and validates the detection logic end-to-end

4. **Unit tests for detection**
   - Test each manager detection signal (uv.lock, Pipfile, both, neither)
   - Test Python version parsing for each source (Pipfile, pyproject.toml, .python-version, .tool-versions)
   - Test range resolution: `>=3.11,<3.13` → `3.12`, `>=3.11` → `3.11`, `==3.11.8` → `3.11.8`
   - Test fallback ordering: pyproject.toml preferred over .python-version for uv repos
   - Test `None` return when no version info found

### Acceptance Criteria

- `pip install -e packages/pc-onboard` works
- `pc-onboard doctor` runs and prints detection results
- All detection unit tests pass

---

## Phase 2 — mise Integration + Tooling Commands

**Goal**: mise operations and manager-specific command generation.

### Tasks

1. **Implement `runner.py`**
   - `run(cmd: list[str], check: bool = True, capture: bool = False) -> subprocess.CompletedProcess`
   - Wraps `subprocess.run` — the single point of subprocess execution
   - Logs commands before execution (for verbose mode)
   - Raises `RunnerError` on non-zero exit when `check=True`

2. **Implement `mise.py`**
   - `ensure_python(version: str, runner: Runner) -> None`
     - Checks `mise --version` is available (raises clear error if not)
     - Runs `mise install python@{version}`
     - Runs `mise use python@{version}`
   - If version is `None`, skip with a warning log

3. **Implement `tooling.py`**
   - `Tooling` base with two implementations: `UvTooling`, `PipenvTooling`
   - Factory: `Tooling.for_manager(manager: str) -> Tooling`
   - Methods:
     - `install_dev_deps(packages: list[str]) -> list[list[str]]` — returns command lists
       - uv: `[["uv", "add", "--dev", *packages], ["uv", "sync"]]`
       - pipenv: `[["pipenv", "install", "--dev", *packages]]`
     - `run_pre_commit_install() -> list[str]`
       - uv: `["uv", "run", "pre-commit", "install"]`
       - pipenv: `["pipenv", "run", "pre-commit", "install"]`
     - `wrap(cmd: list[str]) -> list[str]`
       - uv: `["uv", "run", *cmd]`
       - pipenv: `["pipenv", "run", *cmd]`

4. **Unit tests**
   - `mise.py`: mock runner, verify correct commands issued, verify skip on `None` version
   - `tooling.py`: verify command lists for both managers, verify `wrap()` prefixing
   - `runner.py`: test error handling, test `check=False` behavior

### Acceptance Criteria

- Tooling generates correct commands for both uv and pipenv
- mise module issues correct install/use commands via mock runner
- All unit tests pass

---

## Phase 3 — Template + Init Orchestration

**Goal**: The `.pre-commit-config.yaml` template and the `init` command that ties everything together.

### Tasks

1. **Implement `templates.py`**
   - `get_pre_commit_config() -> str` — returns the enterprise standard YAML
   - Template content (adjust versions/repos to your enterprise standards):

   ```yaml
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

   - `write_pre_commit_config(repo_root: Path) -> Path` — writes file, returns path
   - If file already exists: back up to `.pre-commit-config.yaml.bak`, then overwrite
   - Log whether file was created fresh or replaced

2. **Implement `app.py` — the `run_init()` orchestrator**
   ```
   run_init(repo_root, run_all: bool | None, prompt_run_all: bool) -> int:
       1. manager = detect_manager(repo_root)
       2. python_version = detect_python_version(repo_root, manager)
       3. ensure_python(python_version, runner)
       4. tooling = Tooling.for_manager(manager)
       5. for cmd in tooling.install_dev_deps(DEV_PACKAGES):
              runner.run(cmd)
       6. write_pre_commit_config(repo_root)
       7. runner.run(tooling.run_pre_commit_install())
       8. handle run-all prompt/flag logic
       9. return exit_code
   ```

3. **Wire `cli.py` `init` command**
   - Flags:
     - `--run-all / --no-run-all` (default: None — defer to prompt)
     - `--no-prompt` (skip interactive prompt, default to no run-all)
   - TTY detection: only prompt if `sys.stdin.isatty()` and `--no-prompt` not set
   - Exit code: 0 on success, pre-commit's exit code if run-all executed, 1 on errors

4. **Define `DEV_PACKAGES` constant**
   - `["ruff", "sqlfluff", "pre-commit"]`
   - Centralized so it's easy to update enterprise-wide

5. **Tests**
   - `test_templates.py`: verify YAML content is valid, verify backup behavior on existing file
   - `test_app.py`: mock runner + filesystem, verify full orchestration order:
     - detection → mise → dev deps → template → pre-commit install
   - `test_cli.py`: invoke via `CliRunner`, verify exit codes, verify flag behavior

### Acceptance Criteria

- `pc-onboard init` runs the full workflow in a test repo (mocked subprocess)
- Template written matches enterprise standard
- Existing config backed up before overwrite
- All unit and integration tests pass

---

## Phase 4 — Doctor Command + Error Handling Polish

**Goal**: A diagnostic command and robust error handling for real-world usage.

### Tasks

1. **Expand `pc-onboard doctor`**
   - Checks (each prints pass/fail):
     - `mise` installed and on PATH
     - Package manager detected (uv or pipenv)
     - Python version resolved (and from which source)
     - Current Python version matches resolved version
     - Dev packages installed (ruff, sqlfluff, pre-commit importable)
     - `.pre-commit-config.yaml` exists
     - Pre-commit hooks installed (`.git/hooks/pre-commit` exists)
   - Exit code: 0 if all pass, 1 if any fail

2. **Error handling improvements**
   - Custom exceptions: `DetectionError`, `MiseError`, `ToolingError`
   - `runner.py`: capture stderr on failure, include in error message
   - `app.py`: catch each phase's errors, print actionable messages:
     - "mise not found — install from https://mise.jdx.dev"
     - "No Python version found in Pipfile or pyproject.toml"
     - "uv sync failed — check your pyproject.toml dependencies"
   - `--verbose` flag: print every command before execution

3. **Tests**
   - Doctor with all tools present vs missing
   - Error paths: mise not installed, detection fails, subprocess fails
   - Verbose mode outputs commands

### Acceptance Criteria

- `pc-onboard doctor` gives clear pass/fail for each prerequisite
- Errors produce actionable messages, not stack traces
- `--verbose` shows all commands being executed

---

## Phase 5 — Integration Testing + README

**Goal**: Real-world integration tests and documentation for consumers.

### Tasks

1. **Integration test suite** (`tests/test_integration.py`)
   - Creates a temp directory with `git init`
   - Adds minimal `pyproject.toml` (uv scenario) or `Pipfile` (pipenv scenario)
   - Runs `pc-onboard init --no-prompt` with a **mock runner** that captures commands
   - Asserts:
     - Correct command sequence (mise install → mise use → dev deps → template → pre-commit install)
     - `.pre-commit-config.yaml` written with expected content
     - Commands use the correct manager prefix
   - Optional: a separate test marker (`@pytest.mark.live`) for tests that actually invoke uv/pipenv/mise (skipped in CI unless tools present)

2. **README.md**
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

3. **pyproject.toml finalization**
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

---

## Out of Scope (for now)

- **Auto-updating hook versions**: template has pinned revs; update manually or add `pc-onboard update-hooks` later
- **Custom hook configuration per repo**: all repos get the same enterprise config
- **Installing uv or pipenv**: these are assumed present
- **Windows support**: mise + uv/pipenv on Windows is a different problem; target macOS/Linux first
- **Config file for pc-onboard itself**: no `.pc-onboardrc` — keep it zero-config