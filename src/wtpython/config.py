"""Configuration management for wtpython."""

import json
from pathlib import Path

from .models import Config, HookConfig, WorktreeMeta


class ConfigManager:
    """Manage wtpython configuration."""

    @staticmethod
    def load_config(repo_root: Path) -> Config:
        """Load configuration from repository."""
        worktrees_dir = repo_root / ".worktrees"

        config = Config(
            repo_root=repo_root,
            worktrees_dir=worktrees_dir,
        )

        # Load copy patterns
        copy_file = worktrees_dir / ".wt-copy"
        if copy_file.exists():
            patterns = []
            for line in copy_file.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    patterns.append(line)
            config.copy_patterns = patterns

        # Load hooks
        hooks_dir = worktrees_dir / ".wt-hooks.d"
        if hooks_dir.exists():
            config.hooks = HookConfig.from_hooks_dir(hooks_dir)

        return config

    @staticmethod
    def init_config(repo_root: Path) -> Config:
        """Initialize configuration in repository."""
        worktrees_dir = repo_root / ".worktrees"
        worktrees_dir.mkdir(exist_ok=True)

        # Create .wt-copy with defaults
        copy_file = worktrees_dir / ".wt-copy"
        if not copy_file.exists():
            copy_file.write_text(
                "# Files to copy to new worktrees (glob patterns supported)\n.env*\n"
            )

        # Create hooks directory and templates
        hooks_dir = worktrees_dir / ".wt-hooks.d"
        hooks_dir.mkdir(exist_ok=True)

        for hook_name in ["new", "attach", "merge"]:
            hook_file = hooks_dir / f"{hook_name}.sh"
            if not hook_file.exists():
                hook_file.write_text(
                    "#!/usr/bin/env bash\n"
                    "# Hook script - receives: $1 = worktree path, $2 = branch name\n"
                    'worktree_path="$1"\n'
                    'branch="$2"\n'
                    "\n"
                    "# Add your custom logic here\n"
                )
                # Make executable on Unix-like systems
                if hasattr(hook_file, "chmod"):
                    hook_file.chmod(0o755)

        return ConfigManager.load_config(repo_root)

    @staticmethod
    def copy_files(config: Config, worktree_path: Path) -> list[str]:
        """Copy files to worktree based on patterns."""
        copied = []

        for pattern in config.copy_patterns:
            # Handle glob patterns
            for source_file in config.repo_root.glob(pattern):
                if source_file.is_file() and source_file.name != ".git":
                    dest_file = worktree_path / source_file.name
                    dest_file.write_bytes(source_file.read_bytes())
                    copied.append(source_file.name)

        return copied

    @staticmethod
    def write_meta(worktree_path: Path, meta: WorktreeMeta) -> None:
        """Write metadata to worktree."""
        meta_file = worktree_path / ".wt-meta.json"
        meta_file.write_text(json.dumps(meta.to_dict(), indent=2))

    @staticmethod
    def read_meta(worktree_path: Path) -> WorktreeMeta | None:
        """Read metadata from worktree."""
        meta_file = worktree_path / ".wt-meta.json"
        if not meta_file.exists():
            return None

        try:
            data = json.loads(meta_file.read_text())
            return WorktreeMeta.from_dict(data)
        except (json.JSONDecodeError, KeyError):
            return None
