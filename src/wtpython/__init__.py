"""wtpython - Git Worktree Manager with tmux integration.

A Python library and CLI tool for managing git worktrees with enhanced features
like automatic dependency installation, file copying, and tmux integration.

Cross-platform support for Windows, macOS, and Linux.
"""

from .core import WorktreeManager
from .exceptions import (
    ConfigurationError,
    GitOperationError,
    HookExecutionError,
    InvalidBranchType,
    MergeError,
    NotInGitRepository,
    UncommittedChanges,
    WorktreeExists,
    WorktreeNotFound,
    WtException,
)
from .models import Config, HookConfig, Worktree, WorktreeMeta

__version__ = "1.1.0"
__author__ = "flowelfox"

__all__ = [
    # Main class
    "WorktreeManager",
    # Models
    "Worktree",
    "WorktreeMeta",
    "Config",
    "HookConfig",
    # Exceptions
    "WtException",
    "NotInGitRepository",
    "WorktreeNotFound",
    "WorktreeExists",
    "InvalidBranchType",
    "GitOperationError",
    "UncommittedChanges",
    "MergeError",
    "HookExecutionError",
    "ConfigurationError",
]
