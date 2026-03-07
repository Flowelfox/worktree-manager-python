"""Tmux integration (optional, not available on Windows)."""

import os
import subprocess
from pathlib import Path


class TmuxOps:
    """Tmux operations wrapper."""

    @staticmethod
    def is_available() -> bool:
        """Check if tmux is available."""
        if os.name == "nt":  # Windows
            return False
        try:
            subprocess.run(
                ["tmux", "-V"],
                capture_output=True,
                check=True,
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    @staticmethod
    def is_inside_tmux() -> bool:
        """Check if we're inside a tmux session."""
        return bool(os.environ.get("TMUX"))

    @staticmethod
    def rename_pane(title: str) -> bool:
        """Rename the current tmux pane."""
        if not TmuxOps.is_inside_tmux():
            return False

        try:
            subprocess.run(
                ["tmux", "select-pane", "-T", title],
                capture_output=True,
                check=True,
            )
            return True
        except subprocess.CalledProcessError:
            return False

    @staticmethod
    def close_window(window_name: str) -> bool:
        """Close a tmux window by name."""
        if not TmuxOps.is_inside_tmux():
            return False

        try:
            # Check if window exists
            result = subprocess.run(
                ["tmux", "list-windows", "-F", "#{window_name}"],
                capture_output=True,
                text=True,
                check=True,
            )
            if window_name in result.stdout:
                subprocess.run(
                    ["tmux", "kill-window", "-t", window_name],
                    capture_output=True,
                    check=False,  # Don't fail if window doesn't exist
                )
                return True
        except subprocess.CalledProcessError:
            pass
        return False

    @staticmethod
    def open_in_tmux(_worktree_path: Path, pane_title: str) -> None:
        """Open a worktree in tmux (rename pane if inside tmux).

        Args:
            _worktree_path: Path to worktree (reserved for future use).
            pane_title: Title for the tmux pane.
        """
        if TmuxOps.is_inside_tmux():
            TmuxOps.rename_pane(pane_title)
