# wtpython Design Document

## Overview

wtpython is a Python implementation of the `wt` Git worktree manager, designed as both a library and CLI tool with cross-platform support for Windows, macOS, and Linux.

## Architecture

### Why Python?

- **Cross-platform compatibility**: Python runs consistently across Windows, macOS, and Linux
- **Library-first design**: Python makes it easy to expose functionality as an importable library
- **Rich ecosystem**: Excellent libraries for CLI (click), output formatting (rich), and testing (pytest)
- **Maintainability**: Python's readability makes the codebase easier to understand and modify
- **Package management**: Modern Python packaging with uv makes distribution simple

### Module Structure

The project is organized into focused modules, each with a single responsibility:

```
src/wtpython/
├── __init__.py       # Public API exports
├── core.py          # WorktreeManager class - main library interface
├── git.py           # Git operations wrapper
├── tmux.py          # Tmux integration (optional, Unix-only)
├── hooks.py         # Hook execution with cross-platform support
├── config.py        # Configuration management
├── detect.py        # Package manager detection
├── models.py        # Data models (Worktree, Meta, Config)
├── output.py        # Colored output and formatting
├── exceptions.py    # Custom exceptions
└── cli.py          # CLI entry point using click
```

### Library vs CLI Separation

The project follows a strict separation between library and CLI code:

**Library (core.py and supporting modules):**
- No direct I/O to stdout/stderr (except through output.py)
- No `sys.exit()` calls - uses exceptions for error handling
- Returns rich objects (dataclasses) instead of strings
- All functionality accessible programmatically
- Cross-platform by default

**CLI (cli.py):**
- Thin wrapper around library functions
- Handles user interaction and confirmation prompts
- Converts exceptions to error messages
- Outputs paths to stdout for shell wrapper compatibility
- Provides command-line argument parsing

### Data Flow

1. **User Input** → CLI parses arguments
2. **CLI** → Creates WorktreeManager instance
3. **WorktreeManager** → Orchestrates operations using:
   - GitOps for git commands
   - ConfigManager for settings
   - HookExecutor for custom scripts
   - PackageManagerDetector for dependencies
   - TmuxOps for terminal integration (if available)
4. **Operations** → Return Worktree objects or raise exceptions
5. **CLI** → Formats output for user

### Cross-Platform Considerations

**Windows Support:**
- Uses `pathlib.Path` throughout for path handling
- Tmux integration is optional (detected at runtime)
- Hook scripts support PowerShell and batch files
- Package manager detection includes Windows-specific tools
- Git commands use `shell=True` on Windows for better compatibility

**Unix/Linux/macOS:**
- Full tmux integration when available
- Bash hook scripts with executable permissions
- Native git command execution

### Key Design Decisions

1. **Dataclasses for Models**: Using Python dataclasses provides type hints, automatic initialization, and clean data representation.

2. **Rich for Output**: The rich library provides beautiful, cross-platform terminal output with minimal code.

3. **Click for CLI**: Click offers decorator-based command definition, automatic help generation, and robust argument parsing.

4. **Subprocess for External Commands**: Direct subprocess calls provide fine control over git and package manager execution.

5. **Optional Tmux**: Tmux integration is detected at runtime, allowing the tool to work on Windows where tmux isn't available.

6. **Configuration in .worktrees**: Keeping configuration within the repository (in .worktrees/) makes it portable and shareable.

### Error Handling

The library uses a hierarchy of custom exceptions:

```
WtException (base)
├── NotInGitRepository
├── WorktreeNotFound
├── WorktreeExists
├── InvalidBranchType
├── GitOperationError
├── UncommittedChanges
├── MergeError
├── HookExecutionError
└── ConfigurationError
```

This allows consumers to catch specific errors or handle all wtpython errors generically.

### Testing Strategy

- **Unit tests** for individual components (git operations, config parsing)
- **Integration tests** for WorktreeManager operations
- **Fixtures** for temporary git repositories
- **Cross-platform CI** to ensure Windows/Unix compatibility

### Future Enhancements

Potential areas for expansion:

1. **Parallel Operations**: Async/await support for parallel worktree operations
2. **GUI Frontend**: Tkinter or web-based interface
3. **VS Code Extension**: Direct integration with VS Code
4. **Remote Worktrees**: Support for worktrees on remote machines
5. **Worktree Templates**: Predefined configurations for common workflows
6. **Plugin System**: Allow third-party extensions