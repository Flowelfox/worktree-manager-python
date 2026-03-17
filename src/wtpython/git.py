"""Git operations wrapper with cross-platform support."""

import os
import shutil
import subprocess
from pathlib import Path

from .exceptions import GitOperationError, NotInGitRepository
from .models import Worktree

# Resolve git binary path once at import time
_GIT_BIN: str = shutil.which("git") or "git"


class GitOps:
    """Git operations wrapper."""

    @staticmethod
    def run_command(
        cmd: list[str], cwd: Path | None = None, check: bool = True
    ) -> subprocess.CompletedProcess:
        """Run a git command."""
        # Ensure git command with resolved path
        if cmd[0] == "git":
            cmd[0] = _GIT_BIN
        else:
            cmd = [_GIT_BIN] + cmd

        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                check=check,
                # Use shell=True on Windows for better compatibility
                shell=(os.name == "nt"),
            )
            return result
        except FileNotFoundError as e:
            raise GitOperationError(
                "git not found. Please install git and ensure it is in your PATH."
            ) from e
        except subprocess.CalledProcessError as e:
            if check:
                raise GitOperationError(f"Git command failed: {e.stderr}") from e
            return e

    @staticmethod
    def find_repo_root(path: Path | None = None) -> Path:
        """Find the root of the git repository."""
        if path is None:
            path = Path.cwd()

        result = GitOps.run_command(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=path,
            check=False,
        )

        if result.returncode != 0:
            raise NotInGitRepository("Not in a git repository")

        root = Path(result.stdout.strip())

        # If we're inside a worktree (.worktrees/), get the main repo root
        if ".worktrees" in root.parts:
            # Find the index of .worktrees in the path
            parts = list(root.parts)
            worktrees_idx = parts.index(".worktrees")
            # Return everything before .worktrees
            root = Path(*parts[:worktrees_idx])

        return root

    @staticmethod
    def is_inside_worktree(path: Path | None = None) -> bool:
        """Check if we're inside a worktree."""
        try:
            GitOps.find_repo_root(path)  # Verify we're in a git repo
            current = Path.cwd() if path is None else path
            return ".worktrees" in current.parts
        except NotInGitRepository:
            return False

    @staticmethod
    def get_current_branch(path: Path | None = None) -> str:
        """Get the current branch name."""
        result = GitOps.run_command(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=path,
        )
        return result.stdout.strip()

    @staticmethod
    def branch_exists(branch: str, path: Path | None = None) -> bool:
        """Check if a branch exists."""
        result = GitOps.run_command(
            ["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"],
            cwd=path,
            check=False,
        )
        return result.returncode == 0

    @staticmethod
    def create_branch(branch: str, base: str, path: Path | None = None) -> None:
        """Create a new branch."""
        GitOps.run_command(["git", "branch", branch, base], cwd=path)

    @staticmethod
    def checkout_branch(branch: str, path: Path | None = None) -> None:
        """Checkout a branch."""
        GitOps.run_command(["git", "checkout", branch], cwd=path)

    @staticmethod
    def delete_branch(branch: str, force: bool = True, path: Path | None = None) -> None:
        """Delete a branch."""
        flag = "-D" if force else "-d"
        GitOps.run_command(["git", "branch", flag, branch], cwd=path)

    @staticmethod
    def add_worktree(
        worktree_path: Path, branch: str, base: str | None = None, path: Path | None = None
    ) -> None:
        """Add a new worktree."""
        cmd = ["git", "worktree", "add", "-b", branch, str(worktree_path)]
        if base:
            cmd.append(base)
        GitOps.run_command(cmd, cwd=path)

    @staticmethod
    def remove_worktree(
        worktree_path: Path, force: bool = True, path: Path | None = None
    ) -> None:
        """Remove a worktree."""
        flag = "--force" if force else ""
        cmd = ["git", "worktree", "remove"]
        if flag:
            cmd.append(flag)
        cmd.append(str(worktree_path))
        GitOps.run_command(cmd, cwd=path)

    @staticmethod
    def list_worktrees(path: Path | None = None) -> list[Worktree]:
        """List all worktrees."""
        result = GitOps.run_command(
            ["git", "worktree", "list", "--porcelain"],
            cwd=path,
        )

        worktrees = []
        current_worktree = {}

        for line in result.stdout.splitlines():
            if line.startswith("worktree "):
                if current_worktree:
                    # Process previous worktree
                    wt_path = Path(current_worktree["worktree"])
                    if ".worktrees" in wt_path.parts:
                        worktrees.append(
                            Worktree(
                                name=wt_path.name,
                                path=wt_path,
                                branch=current_worktree.get("branch", ""),
                            )
                        )
                current_worktree = {"worktree": line[9:]}
            elif line.startswith("branch "):
                current_worktree["branch"] = line[7:]
            elif line.startswith("HEAD "):
                current_worktree["head"] = line[5:]

        # Process last worktree
        if current_worktree and "worktree" in current_worktree:
            wt_path = Path(current_worktree["worktree"])
            if ".worktrees" in wt_path.parts:
                branch = current_worktree.get("branch", "")
                if branch.startswith("refs/heads/"):
                    branch = branch[11:]
                worktrees.append(
                    Worktree(
                        name=wt_path.name,
                        path=wt_path,
                        branch=branch,
                    )
                )

        return worktrees

    @staticmethod
    def has_uncommitted_changes(path: Path | None = None) -> bool:
        """Check if there are uncommitted changes."""
        # Check for staged or unstaged changes
        result1 = GitOps.run_command(
            ["git", "diff", "--quiet"],
            cwd=path,
            check=False,
        )
        result2 = GitOps.run_command(
            ["git", "diff", "--cached", "--quiet"],
            cwd=path,
            check=False,
        )
        return result1.returncode != 0 or result2.returncode != 0

    @staticmethod
    def has_untracked_files(path: Path | None = None) -> bool:
        """Check if there are untracked files."""
        result = GitOps.run_command(
            ["git", "ls-files", "--others", "--exclude-standard"],
            cwd=path,
        )
        return bool(result.stdout.strip())

    @staticmethod
    def add_all(path: Path | None = None) -> None:
        """Add all changes."""
        GitOps.run_command(["git", "add", "-A"], cwd=path)

    @staticmethod
    def commit(message: str, path: Path | None = None) -> None:
        """Create a commit."""
        GitOps.run_command(["git", "commit", "-m", message], cwd=path)

    @staticmethod
    def merge(
        branch: str, squash: bool = True, no_ff: bool = False, path: Path | None = None
    ) -> None:
        """Merge a branch."""
        cmd = ["git", "merge"]
        if squash:
            cmd.append("--squash")
        elif no_ff:
            cmd.append("--no-ff")
        cmd.append(branch)
        GitOps.run_command(cmd, cwd=path)

    @staticmethod
    def add_to_exclude(patterns: list[str], repo_root: Path) -> None:
        """Add patterns to .git/info/exclude."""
        exclude_file = repo_root / ".git" / "info" / "exclude"
        exclude_file.parent.mkdir(parents=True, exist_ok=True)

        existing = set()
        if exclude_file.exists():
            existing = set(exclude_file.read_text().splitlines())

        with exclude_file.open("a") as f:
            for pattern in patterns:
                if pattern not in existing:
                    f.write(f"{pattern}\n")
