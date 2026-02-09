"""CLI entrypoint for pc-onboard."""

from pathlib import Path
from typing import Annotated, Optional

import typer

from pc_onboard.app import run_init
from pc_onboard.detect import DetectionError
from pc_onboard.mise import MiseError
from pc_onboard.runner import Runner, RunnerError
from pc_onboard.tooling import ToolingError

app = typer.Typer(help="Automate repository onboarding for enterprise pre-commit standards.")


@app.command()
def doctor(
    repo_root: Annotated[
        Path, typer.Option("--repo-root", "-r", help="Path to the repository root.")
    ] = Path("."),
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Show detailed diagnostic information.")
    ] = False,
) -> None:
    """Check the current environment and print comprehensive diagnostic results."""
    from pc_onboard.app import run_doctor

    repo_root = repo_root.resolve()
    typer.echo(f"Repository: {repo_root}\n")

    checks = run_doctor(repo_root)

    # Print results
    all_passed = True
    for check in checks:
        status = "✓" if check.passed else "✗"
        if check.passed:
            typer.secho(f"  {status} {check.name}: ", fg=typer.colors.GREEN, nl=False)
            typer.echo(check.message)
        else:
            typer.secho(f"  {status} {check.name}: ", fg=typer.colors.RED, nl=False)
            typer.echo(check.message)
            all_passed = False

        # Show source in verbose mode
        if verbose and check.source:
            typer.echo(f"      ({check.source})")

    typer.echo()

    if not all_passed:
        typer.secho("Some checks failed. Run 'pc-onboard init' to set up the repository.", fg=typer.colors.YELLOW)
        raise typer.Exit(code=1)


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
