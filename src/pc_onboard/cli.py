"""CLI entrypoint for pc-onboard."""

import shutil
from pathlib import Path
from typing import Annotated, Optional

import typer

from pc_onboard.app import run_init
from pc_onboard.detect import DetectionError, detect_manager, detect_python_version
from pc_onboard.mise import MiseError
from pc_onboard.runner import Runner, RunnerError
from pc_onboard.tooling import ToolingError

app = typer.Typer(help="Automate repository onboarding for enterprise pre-commit standards.")


@app.command()
def doctor(
    repo_root: Annotated[
        Path, typer.Option("--repo-root", "-r", help="Path to the repository root.")
    ] = Path("."),
) -> None:
    """Check the current environment and print detection results."""
    repo_root = repo_root.resolve()
    typer.echo(f"Repository: {repo_root}\n")

    # mise availability
    mise_path = shutil.which("mise")
    if mise_path:
        typer.echo(f"  mise: found ({mise_path})")
    else:
        typer.echo("  mise: NOT FOUND — install from https://mise.jdx.dev")

    # Package manager detection
    try:
        manager = detect_manager(repo_root)
        typer.echo(f"  Package manager: {manager}")
    except DetectionError as exc:
        typer.echo(f"  Package manager: NOT DETECTED — {exc}")
        raise typer.Exit(code=1)

    # Python version resolution
    python_version = detect_python_version(repo_root, manager)
    if python_version:
        typer.echo(f"  Python version: {python_version}")
    else:
        typer.echo("  Python version: not found in repo config files")

    # Pre-commit config
    config_path = repo_root / ".pre-commit-config.yaml"
    if config_path.exists():
        typer.echo("  .pre-commit-config.yaml: exists")
    else:
        typer.echo("  .pre-commit-config.yaml: not found")

    typer.echo()


@app.command()
def init(
    repo_root: Annotated[
        Path, typer.Option("--repo-root", "-r", help="Path to the repository root.")
    ] = Path("."),
    run_all: Annotated[
        Optional[bool], typer.Option("--run-all/--no-run-all", help="Run pre-commit on all files.")
    ] = None,
    no_prompt: Annotated[
        bool, typer.Option("--no-prompt", help="Skip interactive prompts.")
    ] = False,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Print every command before execution.")
    ] = False,
) -> None:
    """Onboard this repository to enterprise pre-commit standards."""
    repo_root = repo_root.resolve()
    runner = Runner(verbose=verbose)

    try:
        exit_code = run_init(
            repo_root,
            runner,
            run_all=run_all,
            prompt_run_all=not no_prompt,
        )
    except DetectionError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1)
    except MiseError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1)
    except (ToolingError, RunnerError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1)

    raise typer.Exit(code=exit_code)


if __name__ == "__main__":
    app()
