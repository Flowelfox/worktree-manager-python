"""Custom exceptions for wtpython."""


class WtException(Exception):
    """Base exception for wtpython."""

    pass


class NotInGitRepository(WtException):
    """Raised when not in a git repository."""

    pass


class WorktreeNotFound(WtException):
    """Raised when a worktree is not found."""

    pass


class WorktreeExists(WtException):
    """Raised when a worktree already exists."""

    pass


class InvalidBranchType(WtException):
    """Raised when branch type is invalid."""

    pass


class GitOperationError(WtException):
    """Raised when a git operation fails."""

    pass


class UncommittedChanges(WtException):
    """Raised when there are uncommitted changes."""

    pass


class MergeError(WtException):
    """Raised when merge operation fails."""

    pass


class HookExecutionError(WtException):
    """Raised when hook execution fails."""

    pass


class ConfigurationError(WtException):
    """Raised when configuration is invalid."""

    pass
