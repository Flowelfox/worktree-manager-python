"""Output formatting utilities with cross-platform support."""

import sys

from rich.console import Console
from rich.text import Text

# Create console instance for rich output
console = Console(stderr=True)
console_stdout = Console()


class Output:
    """Output formatting with colored messages."""

    @staticmethod
    def info(message: str, stderr: bool = True) -> None:
        """Print info message with blue indicator."""
        text = Text()
        text.append("ℹ ", style="blue")
        text.append(message)
        if stderr:
            console.print(text)
        else:
            console_stdout.print(text)

    @staticmethod
    def success(message: str, stderr: bool = True) -> None:
        """Print success message with green checkmark."""
        text = Text()
        text.append("✓ ", style="green")
        text.append(message)
        if stderr:
            console.print(text)
        else:
            console_stdout.print(text)

    @staticmethod
    def warn(message: str) -> None:
        """Print warning message with yellow indicator."""
        text = Text()
        text.append("⚠ ", style="yellow")
        text.append(message)
        console.print(text)

    @staticmethod
    def error(message: str) -> None:
        """Print error message with red X."""
        text = Text()
        text.append("✗ ", style="red")
        text.append(message)
        console.print(text)  # console already outputs to stderr

    @staticmethod
    def print(message: str, stderr: bool = False) -> None:
        """Print plain message."""
        if stderr:
            console.print(message)
        else:
            console_stdout.print(message)

    @staticmethod
    def print_table_header(columns: list[tuple[str, int]]) -> None:
        """Print formatted table header."""
        header_text = Text()
        for col_name, width in columns:
            header_text.append(f"{col_name:<{width}}", style="bold")
        console_stdout.print(header_text)
        console_stdout.print("-" * sum(width for _, width in columns))


def confirm(prompt: str, default: bool = False) -> bool:
    """Ask for user confirmation."""
    suffix = " [Y/n] " if default else " [y/N] "
    response = console.input(prompt + suffix).strip().lower()

    if not response:
        return default

    return response in ("y", "yes")


# Convenience functions for backward compatibility
def log_info(message: str, stderr: bool = True) -> None:
    """Print info message."""
    Output.info(message, stderr)


def log_success(message: str, stderr: bool = True) -> None:
    """Print success message."""
    Output.success(message, stderr)


def log_warn(message: str) -> None:
    """Print warning message."""
    Output.warn(message)


def log_error(message: str) -> None:
    """Print error message."""
    Output.error(message)
