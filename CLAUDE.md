# CLAUDE.md - AI Assistant Instructions for wtpython

## Project Overview

wtpython is a Python port of the bash `wt` Git worktree manager. It's designed as both a library and CLI tool with cross-platform support.

## Key Project Conventions

### Code Style
- Use Python 3.12+ features
- Type hints on all functions
- Docstrings on all public methods
- Line length: 100 characters (configured in pyproject.toml)
- Use `pathlib.Path` for all path operations
- Use `rich` for terminal output

### Testing
- Run tests: `just test`
- Run with coverage: `just test-cov`
- Tests use pytest with fixtures in conftest.py
- Mock external commands when possible

### Development Workflow
- Use `uv` for dependency management
- Run `just dev` to install development dependencies
- Run `just check` before committing (runs lint + test)
- Format code with `just format`

### Important Patterns

#### Library Usage Pattern
```python
from wtpython import WorktreeManager

wm = WorktreeManager("/path/to/repo")
wm.init()
worktree = wm.new("feature/my-feature", base="main")
wm.merge("my-feature", message="Add feature")
```

#### Exception Handling Pattern
```python
from wtpython import WorktreeManager, WtException

try:
    wm = WorktreeManager()
    wm.new("feature/test")
except WtException as e:
    # Handle any wtpython error
    print(f"Error: {e}")
```

#### Cross-Platform Code Pattern
```python
import os
from pathlib import Path

# Use pathlib for paths
path = Path.home() / ".config" / "wt"

# Check OS when needed
if os.name == "nt":  # Windows
    # Windows-specific code
else:
    # Unix-like code
```

### File Organization

- **src/wtpython/**: Library code
  - `core.py`: Main WorktreeManager class
  - `cli.py`: CLI using click
  - Other modules: Single responsibility each

- **tests/**: Test files
  - Mirror structure of src/
  - Use fixtures from conftest.py

- **Root files**:
  - `pyproject.toml`: Project configuration
  - `justfile`: Task runner commands
  - `LICENSE`: MIT license

### Module Responsibilities

- **core.py**: Orchestrates all operations, main API
- **git.py**: Wraps git commands, no business logic
- **tmux.py**: Optional tmux integration
- **config.py**: Reads/writes configuration files
- **detect.py**: Detects package managers
- **hooks.py**: Executes user hooks
- **models.py**: Data structures only
- **output.py**: Terminal output formatting
- **exceptions.py**: Error definitions
- **cli.py**: Command-line interface

### Cross-Platform Considerations

When modifying code, ensure:

1. **Paths**: Always use `pathlib.Path`, never string concatenation
2. **Commands**: Handle Windows vs Unix differences in subprocess calls
3. **Tmux**: Check `TmuxOps.is_available()` before using
4. **Line endings**: Let git handle them (configured in .gitattributes)
5. **Executables**: Don't assume bash exists on Windows

### Common Tasks

#### Add a new CLI command
1. Add method to WorktreeManager in core.py
2. Add click command to cli.py
3. Add tests to test_core.py
4. Update README.md with usage

#### Add a new exception
1. Define in exceptions.py
2. Add to __all__ in __init__.py
3. Use in appropriate module
4. Handle in cli.py

#### Support a new package manager
1. Add detection logic to detect.py
2. Test on target platform
3. Document in README.md

### Testing Guidelines

- Test public API, not implementation details
- Use temp_git_repo fixture for git operations
- Mock external commands when feasible
- Test both success and error cases
- Ensure tests work on Windows and Unix

### Documentation Updates

When changing functionality:
1. Update docstrings
2. Update README.md if user-facing
3. Update Design.md if architectural
4. Add to CHANGELOG.md (if it exists)

### Git Workflow

- Commit messages: "verb: description" (e.g., "fix: handle spaces in paths")
- Branch names: feature/*, fix/*, docs/* (following wt conventions)
- Run `just check` before committing

### Debugging Tips

- Enable git debug: `GIT_TRACE=1 wt new feature/test`
- Test in Docker: `docker run -it python:3.12 bash`
- Windows testing: Use Git Bash or WSL2
- Check tmux: `tmux -V` and `echo $TMUX`

### Performance Considerations

- Git operations are the bottleneck
- Avoid repeated git calls in loops
- Cache configuration after loading
- Use `--no-validate` flag for faster branch creation

### Security Notes

- Never store credentials in .wt-copy
- Hooks run with full user permissions
- Validate user input in CLI, not library
- Use subprocess with `shell=False` when possible (except Windows)