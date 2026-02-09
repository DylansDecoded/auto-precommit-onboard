# pc-onboard

Automate repository onboarding for enterprise pre-commit standards.

`pc-onboard` is a CLI tool that detects your repository's package manager (uv or pipenv), resolves the required Python version, configures [mise](https://mise.jdx.dev) to manage that version locally, installs development dependencies, writes the enterprise-standard `.pre-commit-config.yaml`, and runs `pre-commit install` — all in a single command.

## Prerequisites

**mise** is the only tool you must install manually. Everything else flows from there.

- **Install mise**: Follow the instructions at [https://mise.jdx.dev](https://mise.jdx.dev)
  - macOS: `brew install mise`
  - Linux: `curl https://mise.jdx.dev/install.sh | sh`

Your target repository must already use **uv** or **pipenv** for package management. `pc-onboard` will detect which one you're using and configure accordingly.

## Installation

Install `pc-onboard` as a development dependency in your project:

### With uv

```bash
uv add --dev pc-onboard
```

Or if installing from a local path (e.g., from a monorepo):

```bash
uv add --dev pc-onboard --path ../path/to/pc-onboard
```

### With pipenv

Add to your `Pipfile` under `[dev-packages]`:

```toml
[dev-packages]
pc-onboard = {path = "../path/to/pc-onboard"}
```

Then run:

```bash
pipenv install --dev
```

## Usage

### Quick Start

Run the init command in your repository root:

```bash
pc-onboard init
```

This will:
1. Detect your package manager (uv or pipenv)
2. Resolve the required Python version from your config files
3. Install and activate Python via mise (`mise use python@X.Y`)
4. Install dev dependencies (`ruff`, `sqlfluff`, `pre-commit`)
5. Write `.pre-commit-config.yaml` with enterprise standard hooks
6. Run `pre-commit install` to set up git hooks
7. Prompt to run `pre-commit run --all-files` (interactive only)

### Check Your Environment

Before running init, check if your environment is properly configured:

```bash
pc-onboard doctor
```

This runs comprehensive diagnostics and shows:
- ✓ mise installed and on PATH
- ✓ Package manager detected
- ✓ Python version resolved from config
- ✓ Current Python matches required version
- ✓ Dev packages installed
- ✓ .pre-commit-config.yaml exists
- ✓ Pre-commit hooks installed

Use `--verbose` to see additional details like which file provided the Python version:

```bash
pc-onboard doctor --verbose
```

### Command Options

#### `pc-onboard init`

**Flags:**

- `--repo-root PATH` or `-r PATH`: Specify the repository root (default: current directory)
- `--run-all` / `--no-run-all`: Control whether to run `pre-commit run --all-files` after setup
  - Without this flag, you'll be prompted interactively (if running in a TTY)
  - Use `--no-run-all` to skip the prompt and the run
- `--no-prompt`: Disable all interactive prompts (equivalent to `--no-run-all`)
- `--verbose` or `-v`: Show all commands before they execute

**Examples:**

```bash
# Run init and automatically run pre-commit on all files
pc-onboard init --run-all

# Run init but skip running pre-commit on all files
pc-onboard init --no-run-all

# Run init in a different directory with verbose output
pc-onboard init --repo-root ~/projects/my-repo --verbose
```

#### `pc-onboard doctor`

**Flags:**

- `--repo-root PATH` or `-r PATH`: Specify the repository root (default: current directory)
- `--verbose` or `-v`: Show detailed diagnostic information (e.g., which file provided Python version)

**Examples:**

```bash
# Check current directory
pc-onboard doctor

# Check with verbose output
pc-onboard doctor --verbose

# Check a different repository
pc-onboard doctor --repo-root ~/projects/my-repo
```

## What It Does

When you run `pc-onboard init`, here's the complete workflow:

1. **Detects package manager** by looking for:
   - `uv.lock` → uv
   - `Pipfile` or `Pipfile.lock` → pipenv
   - Exits with an error if neither is found

2. **Resolves Python version** from:
   - **uv**: `requires-python` in `pyproject.toml`
   - **pipenv**: `python_version` or `python_full_version` in `Pipfile`
   - Falls back to `.python-version` or `.tool-versions` if not found in primary config

3. **Installs and activates Python** via mise:
   - Runs `mise install python@X.Y`
   - Runs `mise use python@X.Y` to pin it locally for the repo
   - Creates/updates `.tool-versions` in your repository

4. **Installs development dependencies**:
   - **uv**: `uv add --dev ruff sqlfluff pre-commit && uv sync`
   - **pipenv**: `pipenv install --dev ruff sqlfluff pre-commit`

5. **Writes `.pre-commit-config.yaml`** with enterprise-standard hooks:
   - Ruff (linting and formatting)
   - SQLFluff (SQL linting and formatting for SparkSQL)
   - Prettier (YAML, Markdown, JSON formatting)
   - Backs up existing config if present (`.pre-commit-config.yaml.backup.TIMESTAMP`)

6. **Runs `pre-commit install`** through your package manager:
   - **uv**: `uv run pre-commit install`
   - **pipenv**: `pipenv run pre-commit install`
   - This installs the git hooks in `.git/hooks/pre-commit`

7. **Optionally runs `pre-commit run --all-files`**:
   - Interactive prompt if running in a TTY
   - Controlled by `--run-all` / `--no-run-all` flags
   - Returns the exit code from pre-commit if executed

## Python Version Resolution

`pc-onboard` uses a conservative version resolution algorithm:

- **Exact pins** (`==3.11.8`): uses that exact version
- **Ranges with upper bound** (`>=3.11,<3.13`): uses the highest compatible minor version (e.g., `3.12`)
- **Lower bound only** (`>=3.11`): uses the lower bound (e.g., `3.11`)
- **Compatible release** (`~=3.11`): uses the specified version (e.g., `3.11`)

This avoids querying for the latest available Python version and instead picks a known-good version based on your constraints.

## Customization

### Updating the Pre-Commit Config Template

The enterprise `.pre-commit-config.yaml` template is defined in [`src/pc_onboard/templates.py`](src/pc_onboard/templates.py).

To customize for your organization:

1. Edit the `get_pre_commit_config()` function in `templates.py`
2. Update hook versions, add/remove hooks, or change configurations
3. Reinstall `pc-onboard` in your projects
4. Run `pc-onboard init` again to update existing repositories

**Current default hooks:**

- **ruff-pre-commit** (v0.8.6): Python linting and formatting
- **sqlfluff** (3.3.1): SQL linting and formatting (SparkSQL dialect)
- **mirrors-prettier** (v4.0.0-alpha.8): YAML, Markdown, JSON formatting

### Changing Development Packages

The default dev dependencies are defined in [`src/pc_onboard/app.py`](src/pc_onboard/app.py) as:

```python
DEV_PACKAGES = ["ruff", "sqlfluff", "pre-commit"]
```

To add or remove packages, modify this list and reinstall.

## Architecture

`pc-onboard` is designed for testability and maintainability:

- **`cli.py`**: Typer commands, flag parsing, TTY detection, error handling
- **`app.py`**: Orchestration logic (`run_init()`, `run_doctor()`)
- **`detect.py`**: Package manager and Python version detection
- **`tooling.py`**: Manager-specific command builders (uv vs pipenv)
- **`mise.py`**: mise operations (`install`, `use`)
- **`templates.py`**: Pre-commit config template and file writing
- **`runner.py`**: Subprocess execution wrapper for testability

All logic is unit tested with >90 tests covering detection, version resolution, command generation, orchestration, and error handling.

## Development

### Running Tests

```bash
# Run all tests (excluding live tests)
pytest

# Run with coverage
pytest --cov=pc_onboard

# Run only integration tests
pytest tests/test_integration.py

# Run live tests (requires mise, uv, git installed)
pytest -m live
```

### Test Structure

- **Unit tests** (`test_*.py`): Fast, no external tools required
- **Integration tests** (`test_integration.py`): Mock runner captures commands
- **Live tests** (`@pytest.mark.live`): Actually invoke tools (skipped by default)

## Troubleshooting

### `mise: command not found`

Install mise from [https://mise.jdx.dev](https://mise.jdx.dev). Make sure it's on your PATH:

```bash
which mise
```

### `Could not detect package manager`

Ensure your repository has either:
- `uv.lock` (for uv), or
- `Pipfile` or `Pipfile.lock` (for pipenv)

### `Python version not found in repo config files`

Add a Python version requirement to your config:

**For uv** (`pyproject.toml`):
```toml
[project]
requires-python = ">=3.11"
```

**For pipenv** (`Pipfile`):
```toml
[requires]
python_version = "3.11"
```

Alternatively, create a `.python-version` file:
```
3.11
```

### Pre-commit hooks fail after installation

Run doctor to diagnose:

```bash
pc-onboard doctor --verbose
```

Check that:
- Python version matches requirements
- Dev packages are installed
- Git hooks are present in `.git/hooks/pre-commit`

## License

[Add your license here]

## Contributing

[Add contributing guidelines here]
