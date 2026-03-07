"""Command-line interface for wtpython."""

import sys

import click
from rich.table import Table

from . import __version__
from .core import WorktreeManager
from .exceptions import WtException
from .output import console_stdout, log_error, log_info
from .tmux import TmuxOps


@click.group(invoke_without_command=True)
@click.pass_context
@click.version_option(version=__version__, prog_name="wt")
def cli(ctx: click.Context) -> None:
    """Git Worktree Manager with tmux integration.

    A cross-platform tool for managing git worktrees with enhanced features
    like automatic dependency installation, file copying, and tmux integration.
    """
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@cli.command()
def init() -> None:
    """Initialize worktree structure in repository."""
    try:
        wm = WorktreeManager()
        wm.init()
    except WtException as e:
        log_error(str(e))
        sys.exit(1)


@cli.command()
@click.argument("branch")
@click.option("--base", help="Base branch (default: current branch)")
@click.option("--open", is_flag=True, help="Open in tmux after creation (if available)")
@click.option("--no-validate", is_flag=True, help="Skip branch type validation")
def new(branch: str, base: str | None, open: bool, no_validate: bool) -> None:
    """Create a new worktree with branch."""
    try:
        wm = WorktreeManager()
        worktree = wm.new(branch, base=base, open_tmux=open, validate_type=not no_validate)

        # Output path to stdout for shell wrapper
        if open and TmuxOps.is_available():
            print(worktree.path)

    except WtException as e:
        log_error(str(e))
        sys.exit(1)


@cli.command(name="list")
def list_cmd() -> None:
    """List all worktrees."""
    try:
        wm = WorktreeManager()
        worktrees = wm.list()

        if not worktrees:
            log_info("No worktrees found. Run 'wt init' first.")
            return

        # Create rich table
        table = Table(show_header=True, header_style="bold")
        table.add_column("NAME", width=30)
        table.add_column("BRANCH", width=40)
        table.add_column("BASE", width=10)
        table.add_column("PATH")

        for worktree in worktrees:
            table.add_row(
                worktree.name,
                worktree.branch,
                worktree.base or "-",
                worktree.relative_path,
            )

        console_stdout.print(table)

    except WtException as e:
        log_error(str(e))
        sys.exit(1)


@cli.command()
@click.argument("name")
def attach(name: str) -> None:
    """Open worktree in tmux (if available)."""
    try:
        wm = WorktreeManager()
        path = wm.attach(name)

        # Output path to stdout for shell wrapper
        print(path)

    except WtException as e:
        log_error(str(e))
        sys.exit(1)


@cli.command()
def detach() -> None:
    """Return to main repo from worktree."""
    try:
        wm = WorktreeManager()
        path = wm.detach()

        # Output path to stdout for shell wrapper
        print(path)

    except WtException as e:
        log_error(str(e))
        sys.exit(1)


@cli.command()
@click.argument("name")
@click.option("--into", help="Target branch to merge into (creates if doesn't exist)")
@click.option("--message", "-m", help="Commit message for squash merge")
@click.option("--no-ff", is_flag=True, help="Use merge commit instead of squash")
@click.option("--keep", is_flag=True, help="Don't delete worktree/branch after merge")
def merge(
    name: str,
    into: str | None,
    message: str | None,
    no_ff: bool,
    keep: bool,
) -> None:
    """Merge worktree branch and cleanup."""
    try:
        wm = WorktreeManager()
        wm.merge(name, into=into, message=message, no_ff=no_ff, keep=keep)

    except WtException as e:
        log_error(str(e))
        sys.exit(1)


@cli.command()
@click.argument("name")
@click.option("-y", "--yes", is_flag=True, help="Skip confirmation prompt")
def rm(name: str, yes: bool) -> None:
    """Remove worktree without merging."""
    try:
        wm = WorktreeManager()
        path = wm.rm(name, force=yes)

        # Output path to stdout if we need to cd
        if path:
            print(path)

    except WtException as e:
        log_error(str(e))
        sys.exit(1)


@cli.command()
@click.argument("command", required=False)
def help(command: str | None) -> None:
    """Show help for commands."""
    if command:
        # Get help for specific command
        cmd = cli.commands.get(command)
        if cmd:
            ctx = click.Context(cmd)
            click.echo(cmd.get_help(ctx))
        else:
            log_error(f"Unknown command: {command}")
            sys.exit(1)
    else:
        # Show general help
        ctx = click.Context(cli)
        click.echo(ctx.get_help())


def main() -> None:
    """Main entry point."""
    try:
        cli()
    except KeyboardInterrupt:
        log_error("Interrupted by user")
        sys.exit(130)
    except Exception as e:
        log_error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
