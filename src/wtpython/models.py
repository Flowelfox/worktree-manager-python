"""Data models for wtpython."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class WorktreeMeta:
    """Metadata for a worktree."""

    base: str
    created: datetime

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "base": self.base,
            "created": self.created.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WorktreeMeta":
        """Create from dictionary."""
        return cls(
            base=data["base"],
            created=datetime.fromisoformat(data["created"]),
        )


@dataclass
class Worktree:
    """Represents a git worktree."""

    name: str
    path: Path
    branch: str
    base: str | None = None
    meta: WorktreeMeta | None = None

    @property
    def relative_path(self) -> str:
        """Get relative path from repo root."""
        return str(self.path.relative_to(self.path.parent.parent))


@dataclass
class HookConfig:
    """Configuration for hooks."""

    new_hook: Path | None = None
    attach_hook: Path | None = None
    merge_hook: Path | None = None

    @classmethod
    def from_hooks_dir(cls, hooks_dir: Path) -> "HookConfig":
        """Create from hooks directory."""
        return cls(
            new_hook=hooks_dir / "new.sh" if (hooks_dir / "new.sh").exists() else None,
            attach_hook=hooks_dir / "attach.sh" if (hooks_dir / "attach.sh").exists() else None,
            merge_hook=hooks_dir / "merge.sh" if (hooks_dir / "merge.sh").exists() else None,
        )


@dataclass
class Config:
    """Configuration for worktree manager."""

    repo_root: Path
    worktrees_dir: Path
    copy_patterns: list[str] = field(default_factory=list)
    hooks: HookConfig = field(default_factory=HookConfig)
    valid_branch_types: list[str] = field(
        default_factory=lambda: ["feature", "fix", "docs", "hotfix", "tech-debt"]
    )

    @property
    def copy_file(self) -> Path:
        """Path to .wt-copy file."""
        return self.worktrees_dir / ".wt-copy"

    @property
    def hooks_dir(self) -> Path:
        """Path to hooks directory."""
        return self.worktrees_dir / ".wt-hooks.d"
