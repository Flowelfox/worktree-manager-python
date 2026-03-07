"""Core WorktreeManager class - the main library interface."""

import re
from datetime import datetime
from pathlib import Path

from .config import ConfigManager
from .detect import PackageManagerDetector
from .exceptions import (
    GitOperationError,
    InvalidBranchType,
    MergeError,
    UncommittedChanges,
    WorktreeExists,
    WorktreeNotFound,
)
from .git import GitOps
from .hooks import HookExecutor
from .models import Config, Worktree, WorktreeMeta
from .output import confirm, log_info, log_success, log_warn
from .tmux import TmuxOps


class WorktreeManager:
    """Main class for managing git worktrees."""

    def __init__(self, repo_path: str | Path | None = None):
        """Initialize WorktreeManager.

        Args:
            repo_path: Path to git repository. If None, uses current directory.
        """
        if repo_path:
            self.repo_root = GitOps.find_repo_root(Path(repo_path))
        else:
            self.repo_root = GitOps.find_repo_root()

        self.config: Config | None = None
        self._load_config()

    def _load_config(self) -> None:
        """Load configuration if .worktrees exists."""
        if (self.repo_root / ".worktrees").exists():
            self.config = ConfigManager.load_config(self.repo_root)

    def _ensure_init(self) -> None:
        """Ensure .worktrees is initialized."""
        if not self.config:
            log_info("Initializing .worktrees/ directory...")
            self.init()

    @property
    def repo_name(self) -> str:
        """Get repository name."""
        return self.repo_root.name

    def init(self) -> Config:
        """Initialize worktree structure in repository.

        Returns:
            Configuration object.
        """
        worktrees_dir = self.repo_root / ".worktrees"

        if worktrees_dir.exists():
            log_warn(".worktrees/ already exists")
            self.config = ConfigManager.load_config(self.repo_root)
            return self.config

        # Initialize configuration
        self.config = ConfigManager.init_config(self.repo_root)

        # Add to .git/info/exclude
        GitOps.add_to_exclude([".worktrees/", ".wt-meta.json"], self.repo_root)

        log_success(f"Initialized .worktrees/ in {self.repo_root}")
        log_info("Edit .worktrees/.wt-copy to configure files to copy")
        log_info("Edit .worktrees/.wt-hooks.d/*.sh to add custom hooks")

        return self.config

    def branch_to_dir(self, branch: str) -> str:
        """Convert branch name to directory name.

        Args:
            branch: Branch name.

        Returns:
            Directory name.
        """
        # Remove type prefix (feature/, fix/, etc.) and convert / to -
        pattern = rf"^({'|'.join(self.config.valid_branch_types if self.config else ['feature', 'fix', 'docs', 'hotfix', 'tech-debt'])})/(.+)"
        match = re.match(pattern, branch)
        if match:
            return match.group(2).replace("/", "-")
        return branch.replace("/", "-")

    def validate_branch_type(self, branch: str) -> None:
        """Validate branch type.

        Args:
            branch: Branch name to validate.

        Raises:
            InvalidBranchType: If branch type is invalid.
        """
        valid_types = (
            self.config.valid_branch_types
            if self.config
            else ["feature", "fix", "docs", "hotfix", "tech-debt"]
        )
        pattern = rf"^({'|'.join(valid_types)})/"
        if not re.match(pattern, branch):
            raise InvalidBranchType(
                f"Invalid branch type. Must start with: {', '.join(valid_types)}"
            )

    def new(
        self,
        branch: str,
        base: str | None = None,
        open_tmux: bool = False,
        validate_type: bool = True,
    ) -> Worktree:
        """Create a new worktree.

        Args:
            branch: Branch name for the worktree.
            base: Base branch (default: current branch).
            open_tmux: Open in tmux if available.
            validate_type: Validate branch type.

        Returns:
            Created Worktree object.

        Raises:
            WorktreeExists: If worktree already exists.
            InvalidBranchType: If branch type is invalid.
        """
        # Prevent creating worktrees inside worktrees
        if GitOps.is_inside_worktree():
            raise WorktreeExists(
                "Cannot create worktree from inside another worktree. Run from main repo."
            )

        # Validate branch type if requested
        if validate_type:
            self.validate_branch_type(branch)

        # Ensure initialized
        self._ensure_init()

        # Set base branch
        if not base:
            base = GitOps.get_current_branch(self.repo_root)

        # Derive directory name
        dir_name = self.branch_to_dir(branch)
        worktree_path = self.repo_root / ".worktrees" / dir_name

        # Check if already exists
        if worktree_path.exists():
            raise WorktreeExists(f"Worktree already exists: {dir_name}")

        # Create worktree
        log_info(f"Creating worktree: {dir_name} (branch: {branch}, base: {base})")
        GitOps.add_worktree(worktree_path, branch, base, self.repo_root)

        # Write metadata
        meta = WorktreeMeta(base=base, created=datetime.now())
        ConfigManager.write_meta(worktree_path, meta)

        # Copy files
        if self.config:
            copied = ConfigManager.copy_files(self.config, worktree_path)
            for file in copied:
                log_info(f"Copied {file}")

        # Auto-detect and run package manager
        install_cmd = PackageManagerDetector.detect(worktree_path)
        if install_cmd:
            log_info(f"Running: {install_cmd}")
            if PackageManagerDetector.run_install(worktree_path, install_cmd):
                log_success("Dependencies installed")
            else:
                log_warn("Failed to install dependencies")

        # Run hook
        if self.config and self.config.hooks.new_hook:
            HookExecutor.run_hook(
                self.config.hooks.new_hook,
                worktree_path,
                branch,
                "new",
            )

        log_success(f"Created worktree: {dir_name} (from {base})")

        # Create Worktree object
        worktree = Worktree(
            name=dir_name,
            path=worktree_path,
            branch=branch,
            base=base,
            meta=meta,
        )

        # Open in tmux if requested
        if open_tmux and TmuxOps.is_available():
            pane_title = f"{self.repo_name}:{branch}"
            TmuxOps.open_in_tmux(worktree_path, pane_title)
            log_success(f"Opening: {worktree_path}", stderr=True)
        else:
            log_info(f"Path: {worktree_path}")
            if TmuxOps.is_available():
                log_info(f"Use 'wt attach {dir_name}' to open in tmux")

        return worktree

    def list(self) -> list[Worktree]:
        """List all worktrees.

        Returns:
            List of Worktree objects.
        """
        worktrees_dir = self.repo_root / ".worktrees"

        if not worktrees_dir.exists():
            return []

        # Get worktrees from git
        git_worktrees = GitOps.list_worktrees(self.repo_root)

        # Enhance with metadata
        for worktree in git_worktrees:
            meta = ConfigManager.read_meta(worktree.path)
            if meta:
                worktree.base = meta.base
                worktree.meta = meta

        return git_worktrees

    def get(self, name: str) -> Worktree:
        """Get a specific worktree by name.

        Args:
            name: Worktree name.

        Returns:
            Worktree object.

        Raises:
            WorktreeNotFound: If worktree doesn't exist.
        """
        worktree_path = self.repo_root / ".worktrees" / name

        if not worktree_path.exists():
            raise WorktreeNotFound(f"Worktree not found: {name}")

        branch = GitOps.get_current_branch(worktree_path)
        meta = ConfigManager.read_meta(worktree_path)

        return Worktree(
            name=name,
            path=worktree_path,
            branch=branch,
            base=meta.base if meta else None,
            meta=meta,
        )

    def attach(self, name: str) -> Path:
        """Attach to a worktree (open in tmux if available).

        Args:
            name: Worktree name.

        Returns:
            Path to worktree.

        Raises:
            WorktreeNotFound: If worktree doesn't exist.
        """
        worktree = self.get(name)

        # Run hook
        if self.config and self.config.hooks.attach_hook:
            HookExecutor.run_hook(
                self.config.hooks.attach_hook,
                worktree.path,
                worktree.branch,
                "attach",
            )

        # Rename tmux pane if inside tmux
        if TmuxOps.is_inside_tmux():
            pane_title = f"{self.repo_name}:{worktree.branch}"
            TmuxOps.rename_pane(pane_title)
            log_info(f"Renamed tmux pane to: {pane_title}", stderr=True)

        log_success(f"Attaching to: {worktree.path}", stderr=True)

        return worktree.path

    def detach(self) -> Path:
        """Detach from current worktree and return to main repo.

        Returns:
            Path to main repository.

        Raises:
            WorktreeNotFound: If not inside a worktree.
        """
        if not GitOps.is_inside_worktree():
            raise WorktreeNotFound("Not inside a worktree")

        # Rename tmux pane if inside tmux
        if TmuxOps.is_inside_tmux():
            main_branch = GitOps.get_current_branch(self.repo_root)
            pane_title = f"{self.repo_name}:{main_branch}"
            TmuxOps.rename_pane(pane_title)
            log_info(f"Renamed tmux pane to: {pane_title}", stderr=True)

        log_success(f"Detaching to: {self.repo_root}", stderr=True)

        return self.repo_root

    def merge(
        self,
        name: str,
        into: str | None = None,
        message: str | None = None,
        no_ff: bool = False,
        keep: bool = False,
        auto_commit_changes: bool = False,
    ) -> bool:
        """Merge a worktree branch.

        Args:
            name: Worktree name.
            into: Target branch (default: base branch).
            message: Commit message for squash merge.
            no_ff: Use merge commit instead of squash.
            keep: Don't delete worktree/branch after merge.
            auto_commit_changes: Automatically commit uncommitted changes.

        Returns:
            True if merge succeeded.

        Raises:
            WorktreeNotFound: If worktree doesn't exist.
            UncommittedChanges: If there are uncommitted changes and auto_commit_changes is False.
            MergeError: If merge fails.
        """
        worktree = self.get(name)

        if not worktree.base and not into:
            raise MergeError(
                "Could not determine base branch from metadata and no --into specified"
            )

        # Check for uncommitted changes
        if GitOps.has_uncommitted_changes(worktree.path):
            if auto_commit_changes:
                log_info("Committing uncommitted changes...")
                GitOps.add_all(worktree.path)
                GitOps.commit("WIP: uncommitted changes", worktree.path)
            else:
                log_warn("Worktree has uncommitted changes.")
                if confirm("Commit them before merging?"):
                    commit_msg = input("Commit message: ") or "WIP: uncommitted changes"
                    GitOps.add_all(worktree.path)
                    try:
                        GitOps.commit(commit_msg, worktree.path)
                        log_success(f"Changes committed to {worktree.branch}")
                    except GitOperationError:
                        # Pre-commit hooks may have modified files
                        if GitOps.has_uncommitted_changes(worktree.path):
                            log_info("Pre-commit hooks modified files, retrying commit...")
                            GitOps.add_all(worktree.path)
                            GitOps.commit(commit_msg, worktree.path)
                        else:
                            log_info("Nothing to commit after pre-commit hooks ran")
                else:
                    raise UncommittedChanges("Aborting merge. Commit or stash your changes first.")

        # Check for untracked files
        if GitOps.has_untracked_files(worktree.path):
            log_warn("Worktree has untracked files.")
            if confirm("Add and commit them before merging?"):
                commit_msg = input("Commit message: ") or "WIP: add untracked files"
                GitOps.add_all(worktree.path)
                try:
                    GitOps.commit(commit_msg, worktree.path)
                    log_success(f"Untracked files committed to {worktree.branch}")
                except GitOperationError:
                    if GitOps.has_uncommitted_changes(worktree.path):
                        log_info("Pre-commit hooks modified files, retrying commit...")
                        GitOps.add_all(worktree.path)
                        GitOps.commit(commit_msg, worktree.path)
                    else:
                        log_info("Nothing to commit after pre-commit hooks ran")
            else:
                log_info("Continuing without untracked files...")

        # Run hook
        if self.config and self.config.hooks.merge_hook:
            HookExecutor.run_hook(
                self.config.hooks.merge_hook,
                worktree.path,
                worktree.branch,
                "merge",
            )

        # Determine target branch
        target_branch = into or worktree.base
        created_new_branch = False

        if into:
            # Check if target branch exists
            if GitOps.branch_exists(into, self.repo_root):
                log_info(f"Merging into existing branch: {into}")
            else:
                # Create new branch from the worktree's base
                log_info(f"Creating new branch '{into}' from {worktree.base}...")
                GitOps.create_branch(into, worktree.base, self.repo_root)
                created_new_branch = True

        # Check what branch is currently checked out in main worktree
        main_branch = GitOps.get_current_branch(self.repo_root)

        if main_branch != target_branch:
            log_info(f"Switching main worktree to {target_branch}...")
            GitOps.checkout_branch(target_branch, self.repo_root)

        # Merge from the main worktree
        try:
            if no_ff:
                log_info(f"Merging {worktree.branch} with merge commit...")
                GitOps.merge(worktree.branch, squash=False, no_ff=True, path=self.repo_root)
                merge_success = True
            else:
                log_info(f"Squash merging {worktree.branch}...")
                GitOps.merge(worktree.branch, squash=True, path=self.repo_root)

                # Get commit message
                if not message:
                    message = input("Commit message: ") or f"Merge {worktree.branch}"

                GitOps.commit(message, self.repo_root)
                merge_success = True

        except GitOperationError as e:
            # If we created a new branch and merge failed, clean it up
            if created_new_branch:
                log_warn(f"Cleaning up newly created branch {into}...")
                try:
                    GitOps.checkout_branch(worktree.base, self.repo_root)
                    GitOps.delete_branch(into, force=True, path=self.repo_root)
                except GitOperationError:
                    pass
            raise MergeError(f"Merge/commit failed: {e}. Worktree preserved.") from e

        log_success(f"Merged {worktree.branch} into {target_branch}")

        # Cleanup unless --keep
        if not keep:
            # Close tmux window if available
            if TmuxOps.is_available():
                window_name = f"{self.repo_name}:{worktree.branch}"
                TmuxOps.close_window(window_name)

            log_info("Removing worktree...")
            GitOps.remove_worktree(worktree.path, force=True, path=self.repo_root)

            log_info("Deleting branch...")
            try:
                GitOps.delete_branch(worktree.branch, force=True, path=self.repo_root)
            except GitOperationError:
                log_warn(f"Could not delete branch {worktree.branch}")

            log_success(f"Cleaned up {name}")

        return merge_success

    def rm(self, name: str, force: bool = False) -> Path | None:
        """Remove a worktree without merging.

        Args:
            name: Worktree name.
            force: Skip confirmation.

        Returns:
            Path to main repo if we were inside the removed worktree, None otherwise.

        Raises:
            WorktreeNotFound: If worktree doesn't exist.
        """
        worktree = self.get(name)

        # Check if we're inside the worktree being removed
        current_dir = Path.cwd()
        need_cd = current_dir == worktree.path or worktree.path in current_dir.parents

        # Confirm
        if not force and not confirm(f"Delete worktree and branch '{worktree.branch}'?"):
            log_info("Cancelled")
            return None

        # Close tmux window if available
        if TmuxOps.is_available():
            window_name = f"{self.repo_name}:{worktree.branch}"
            TmuxOps.close_window(window_name)

        # Remove worktree
        log_info("Removing worktree...", stderr=True)
        GitOps.remove_worktree(worktree.path, force=True, path=self.repo_root)

        # Delete branch
        log_info("Deleting branch...", stderr=True)
        try:
            GitOps.delete_branch(worktree.branch, force=True, path=self.repo_root)
        except GitOperationError:
            log_warn(f"Could not delete branch {worktree.branch}")

        log_success(f"Removed {name}", stderr=True)

        # Return repo root if we need to cd
        return self.repo_root if need_cd else None
