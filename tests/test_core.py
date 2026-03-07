"""Tests for the core WorktreeManager class."""

import os
from pathlib import Path

import pytest

from wtpython import InvalidBranchType, WorktreeExists, WorktreeManager, WorktreeNotFound


class TestWorktreeManager:
    """Test WorktreeManager functionality."""

    def test_init(self, temp_git_repo: Path) -> None:
        """Test initialization of worktree structure."""
        wm = WorktreeManager(temp_git_repo)
        config = wm.init()

        # Check directories were created
        assert (temp_git_repo / ".worktrees").exists()
        assert (temp_git_repo / ".worktrees" / ".wt-copy").exists()
        assert (temp_git_repo / ".worktrees" / ".wt-hooks.d").exists()

        # Check hooks were created
        hooks_dir = temp_git_repo / ".worktrees" / ".wt-hooks.d"
        assert (hooks_dir / "new.sh").exists()
        assert (hooks_dir / "attach.sh").exists()
        assert (hooks_dir / "merge.sh").exists()

        # Check config was loaded
        assert config.repo_root == temp_git_repo
        assert config.worktrees_dir == temp_git_repo / ".worktrees"

    def test_branch_to_dir(self, temp_git_repo: Path) -> None:
        """Test converting branch names to directory names."""
        wm = WorktreeManager(temp_git_repo)
        wm.init()

        assert wm.branch_to_dir("feature/my-feature") == "my-feature"
        assert wm.branch_to_dir("fix/bug-123") == "bug-123"
        assert wm.branch_to_dir("feature/scope/name") == "scope-name"
        assert wm.branch_to_dir("regular-branch") == "regular-branch"

    def test_validate_branch_type(self, temp_git_repo: Path) -> None:
        """Test branch type validation."""
        wm = WorktreeManager(temp_git_repo)
        wm.init()

        # Valid branch types
        wm.validate_branch_type("feature/test")
        wm.validate_branch_type("fix/test")
        wm.validate_branch_type("docs/test")
        wm.validate_branch_type("hotfix/test")
        wm.validate_branch_type("tech-debt/test")

        # Invalid branch types
        with pytest.raises(InvalidBranchType):
            wm.validate_branch_type("invalid/test")
        with pytest.raises(InvalidBranchType):
            wm.validate_branch_type("test")

    def test_new_worktree(self, temp_git_repo: Path) -> None:
        """Test creating a new worktree."""
        wm = WorktreeManager(temp_git_repo)
        wm.init()

        # Create a worktree
        worktree = wm.new("feature/test-feature", base="master")

        assert worktree.name == "test-feature"
        assert worktree.path == temp_git_repo / ".worktrees" / "test-feature"
        assert worktree.branch == "feature/test-feature"
        assert worktree.base == "master"
        assert worktree.path.exists()

        # Check metadata was written
        meta_file = worktree.path / ".wt-meta.json"
        assert meta_file.exists()

    def test_new_worktree_already_exists(self, temp_git_repo: Path) -> None:
        """Test that creating duplicate worktree fails."""
        wm = WorktreeManager(temp_git_repo)
        wm.init()

        # Create first worktree
        wm.new("feature/test-feature")

        # Try to create duplicate
        with pytest.raises(WorktreeExists):
            wm.new("feature/test-feature")

    def test_list_worktrees(self, temp_git_repo: Path) -> None:
        """Test listing worktrees."""
        wm = WorktreeManager(temp_git_repo)
        wm.init()

        # Initially empty
        assert len(wm.list()) == 0

        # Create some worktrees
        wm.new("feature/feature-1")
        wm.new("fix/bug-1")

        # List should return both
        worktrees = wm.list()
        assert len(worktrees) == 2
        names = {wt.name for wt in worktrees}
        assert "feature-1" in names
        assert "bug-1" in names

    def test_get_worktree(self, temp_git_repo: Path) -> None:
        """Test getting a specific worktree."""
        wm = WorktreeManager(temp_git_repo)
        wm.init()

        # Create worktree
        wm.new("feature/test-feature")

        # Get it
        worktree = wm.get("test-feature")
        assert worktree.name == "test-feature"
        assert worktree.branch == "feature/test-feature"

        # Get non-existent
        with pytest.raises(WorktreeNotFound):
            wm.get("non-existent")

    def test_attach_detach(self, temp_git_repo: Path, monkeypatch) -> None:
        """Test attach and detach functionality."""
        # Change to temp repo directory
        monkeypatch.chdir(temp_git_repo)

        wm = WorktreeManager(temp_git_repo)
        wm.init()

        # Create worktree
        wm.new("feature/test-feature")

        # Attach returns path
        path = wm.attach("test-feature")
        assert path == temp_git_repo / ".worktrees" / "test-feature"

        # Simulate being in worktree
        worktree_path = temp_git_repo / ".worktrees" / "test-feature"
        monkeypatch.chdir(worktree_path)

        # Detach returns main repo path
        path = wm.detach()
        assert path == temp_git_repo

    def test_rm_worktree(self, temp_git_repo: Path) -> None:
        """Test removing a worktree."""
        wm = WorktreeManager(temp_git_repo)
        wm.init()

        # Create worktree
        wm.new("feature/test-feature")
        worktree_path = temp_git_repo / ".worktrees" / "test-feature"
        assert worktree_path.exists()

        # Remove it
        wm.rm("test-feature", force=True)

        # Should be gone
        assert not worktree_path.exists()
        assert len(wm.list()) == 0

        # Removing non-existent should fail
        with pytest.raises(WorktreeNotFound):
            wm.rm("non-existent")

    def test_copy_files(self, temp_git_repo: Path) -> None:
        """Test file copying to new worktrees."""
        wm = WorktreeManager(temp_git_repo)
        wm.init()

        # Create some files to copy
        (temp_git_repo / ".env").write_text("SECRET=value")
        (temp_git_repo / ".env.local").write_text("LOCAL=value")
        (temp_git_repo / "other.txt").write_text("not copied")

        # Create worktree
        worktree = wm.new("feature/test-feature")

        # Check files were copied
        assert (worktree.path / ".env").exists()
        assert (worktree.path / ".env.local").exists()
        assert not (worktree.path / "other.txt").exists()

    @pytest.mark.skipif(os.name == "nt", reason="Merge test may fail on Windows CI")
    def test_merge_worktree(self, temp_git_repo: Path) -> None:
        """Test merging a worktree."""
        wm = WorktreeManager(temp_git_repo)
        wm.init()

        # Create worktree
        wm.new("feature/test-feature")
        worktree_path = temp_git_repo / ".worktrees" / "test-feature"

        # Make a change in worktree
        (worktree_path / "new_file.txt").write_text("test content")
        import subprocess

        subprocess.run(["git", "add", "."], cwd=worktree_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Add new file"],
            cwd=worktree_path,
            check=True,
        )

        # Merge it
        wm.merge("test-feature", message="Merge test feature", keep=False)

        # Worktree should be gone
        assert not worktree_path.exists()

        # Change should be in main branch
        assert (temp_git_repo / "new_file.txt").exists()
