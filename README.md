# wtpython

A cross-platform Git worktree manager with automatic dependency installation, file synchronization, and tmux integration. Available as both a Python library and CLI tool.

This is a Python implementation of the original [wt](https://github.com/flowelfox/wt) bash script, with added Windows support and library API.

## Features

- 🌳 **Simplified worktree management** - Create, list, attach, and merge worktrees with ease
- 📦 **Automatic dependency installation** - Detects and runs package managers (npm, pip, cargo, etc.)
- 📁 **File synchronization** - Automatically copies configured files (.env, etc.) to new worktrees
- 🖥️ **Tmux integration** - Seamlessly integrates with tmux sessions (Unix/Linux/macOS)
- 🪝 **Custom hooks** - Run scripts on worktree events (new, attach, merge)
- 🔀 **Smart merging** - Squash or merge commits with automatic cleanup
- 🐍 **Python library** - Use as a library in your Python projects
- 🖥️ **Cross-platform** - Works on Windows, macOS, and Linux

## Installation

### Using pip

```bash
pip install wtpython
```

### Using uv (recommended)

```bash
uv pip install wtpython
```

### From source

```bash
git clone https://github.com/flowelfox/wtpython.git
cd wtpython
uv pip install -e .
```

## Quick Start

### CLI Usage

Initialize in your git repository:

```bash
cd your-git-repo
wt init
```

Create a new worktree:

```bash
wt new feature/awesome-feature
```

List worktrees:

```bash
wt list
```

Attach to a worktree:

```bash
wt attach awesome-feature
```

Merge and cleanup:

```bash
wt merge awesome-feature --message "Add awesome feature"
```

### Library Usage

```python
from wtpython import WorktreeManager

# Initialize manager
wm = WorktreeManager("/path/to/repo")

# Initialize worktree structure
wm.init()

# Create a new worktree
worktree = wm.new("feature/my-feature", base="main")
print(f"Created worktree at {worktree.path}")

# List all worktrees
for wt in wm.list():
    print(f"{wt.name}: {wt.branch} ({wt.base})")

# Merge a worktree
wm.merge("my-feature", message="Add my feature")
```

## Commands

### `wt init`

Initialize the worktree structure in a repository.

Creates:
- `.worktrees/` - Directory for worktrees
- `.worktrees/.wt-copy` - File patterns to copy to new worktrees
- `.worktrees/.wt-hooks.d/` - Hook scripts directory

### `wt new <branch> [options]`

Create a new worktree with a branch.

Options:
- `--base <branch>` - Base branch (default: current branch)
- `--open` - Open in tmux after creation (Unix/Linux/macOS only)
- `--no-validate` - Skip branch type validation

Example:
```bash
wt new feature/user-auth --base develop --open
```

### `wt list`

List all worktrees in a formatted table.

```bash
wt list
```

Output:
```
NAME            BRANCH                      BASE     PATH
user-auth       feature/user-auth           develop  .worktrees/user-auth
api-update      fix/api-update              main     .worktrees/api-update
```

### `wt attach <name>`

Open a worktree (with tmux integration if available).

```bash
wt attach user-auth
```

### `wt detach`

Return to the main repository from a worktree.

```bash
wt detach
```

### `wt merge <name> [options]`

Merge a worktree branch and clean up.

Options:
- `--into <branch>` - Target branch (creates if doesn't exist)
- `--message/-m <message>` - Commit message for squash
- `--no-ff` - Use merge commit instead of squash
- `--keep` - Don't delete worktree/branch after merge

Examples:
```bash
# Squash merge with message
wt merge user-auth --message "Add user authentication"

# Merge into a different branch
wt merge hotfix-123 --into release-2.0

# Merge commit (no squash)
wt merge feature-xyz --no-ff

# Keep worktree after merge
wt merge experimental --keep
```

### `wt rm <name> [options]`

Remove a worktree without merging.

Options:
- `-y/--yes` - Skip confirmation

```bash
wt rm abandoned-feature -y
```

## Configuration

### File Copying (.worktrees/.wt-copy)

Configure which files to copy to new worktrees:

```bash
# .worktrees/.wt-copy
# Files to copy to new worktrees (glob patterns supported)
.env*
config/local.json
*.key
```

### Hooks (.worktrees/.wt-hooks.d/)

Create executable scripts that run on worktree events:

- `new.sh` - Runs after creating a worktree
- `attach.sh` - Runs when attaching to a worktree
- `merge.sh` - Runs before merging a worktree

Example hook:
```bash
#!/usr/bin/env bash
# .worktrees/.wt-hooks.d/new.sh
worktree_path="$1"
branch="$2"

echo "Setting up worktree for $branch"
# Your custom setup here
```

**Note on Windows**: Hooks can be PowerShell (`.ps1`) or batch (`.bat`) scripts.

## Package Manager Detection

Automatically detects and runs the appropriate package manager:

| Language | Files Detected | Command Run |
|----------|---------------|-------------|
| Node.js | package.json + pnpm-lock.yaml | `pnpm install` |
| Node.js | package.json + yarn.lock | `yarn install` |
| Node.js | package.json + bun.lockb | `bun install` |
| Node.js | package.json | `npm install` |
| Python | pyproject.toml + poetry.lock | `poetry install` |
| Python | pyproject.toml + uv.lock | `uv sync` |
| Python | pyproject.toml | `pip install -e .` |
| Python | requirements.txt | `pip install -r requirements.txt` |
| Python | Pipfile | `pipenv install` |
| Rust | Cargo.toml | `cargo build` |
| Go | go.mod | `go mod download` |
| Ruby | Gemfile | `bundle install` |
| .NET | *.csproj | `dotnet restore` |
| Java | pom.xml | `mvn install` |
| Java | build.gradle | `./gradlew build` |

## Branch Naming Convention

By default, branches must follow the pattern: `type/description`

Valid types:
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation
- `hotfix/` - Urgent fixes
- `tech-debt/` - Technical debt

Use `--no-validate` to skip validation.

## Shell Wrapper for Directory Changes

The CLI outputs paths to stdout for shell integration. Create a shell function to enable `cd` functionality:

### Bash/Zsh

Add to your `.bashrc` or `.zshrc`:

```bash
wt() {
    case "$1" in
        attach|detach)
            local path
            path="$(command wt "$@")"
            [[ -n "$path" && -d "$path" ]] && cd "$path"
            ;;
        new)
            if [[ " $* " =~ " --open " ]]; then
                local path
                path="$(command wt "$@")"
                [[ -n "$path" && -d "$path" ]] && cd "$path"
            else
                command wt "$@"
            fi
            ;;
        rm)
            local path
            path="$(command wt "$@")"
            [[ -n "$path" && -d "$path" ]] && cd "$path"
            ;;
        *)
            command wt "$@"
            ;;
    esac
}
```

### PowerShell (Windows)

Add to your PowerShell profile:

```powershell
function wt {
    $cmd = $args[0]
    switch ($cmd) {
        "attach" {
            $path = & wt.exe $args
            if ($path -and (Test-Path $path)) { Set-Location $path }
        }
        "detach" {
            $path = & wt.exe $args
            if ($path -and (Test-Path $path)) { Set-Location $path }
        }
        "new" {
            if ($args -contains "--open") {
                $path = & wt.exe $args
                if ($path -and (Test-Path $path)) { Set-Location $path }
            } else {
                & wt.exe $args
            }
        }
        "rm" {
            $path = & wt.exe $args
            if ($path -and (Test-Path $path)) { Set-Location $path }
        }
        default {
            & wt.exe $args
        }
    }
}
```

## Platform-Specific Notes

### Windows
- Tmux integration is not available
- Hooks can be PowerShell (.ps1) or batch (.bat) scripts
- Use Git Bash or WSL for a more Unix-like experience
- Path separators are handled automatically

### macOS/Linux
- Full tmux integration available
- Bash hooks with executable permissions
- Native git command execution

## Library API Reference

### WorktreeManager

Main class for managing worktrees.

```python
class WorktreeManager:
    def __init__(self, repo_path: Optional[str | Path] = None)
    def init(self) -> Config
    def new(self, branch: str, base: Optional[str] = None,
            open_tmux: bool = False, validate_type: bool = True) -> Worktree
    def list(self) -> list[Worktree]
    def get(self, name: str) -> Worktree
    def attach(self, name: str) -> Path
    def detach(self) -> Path
    def merge(self, name: str, into: Optional[str] = None,
              message: Optional[str] = None, no_ff: bool = False,
              keep: bool = False) -> bool
    def rm(self, name: str, force: bool = False) -> Optional[Path]
```

### Models

```python
@dataclass
class Worktree:
    name: str
    path: Path
    branch: str
    base: Optional[str]
    meta: Optional[WorktreeMeta]

@dataclass
class WorktreeMeta:
    base: str
    created: datetime
```

### Exceptions

All exceptions inherit from `WtException`:

- `NotInGitRepository` - Not in a git repository
- `WorktreeNotFound` - Worktree doesn't exist
- `WorktreeExists` - Worktree already exists
- `InvalidBranchType` - Invalid branch type
- `GitOperationError` - Git command failed
- `UncommittedChanges` - Uncommitted changes exist
- `MergeError` - Merge operation failed
- `HookExecutionError` - Hook script failed

## Development

### Setup

```bash
# Clone the repository
git clone https://github.com/flowelfox/wtpython.git
cd wtpython

# Install development dependencies
uv sync --all-extras

# Or with just
just dev
```

### Running Tests

```bash
# Run tests
just test

# Run with coverage
just test-cov

# Run linting
just lint

# Format code
just format

# Run all checks
just check
```

### Building

```bash
# Build package
just build

# Create source distribution
just sdist

# Create wheel
just wheel
```

## Differences from Original Bash Version

- **Cross-platform**: Works on Windows, not just Unix-like systems
- **Library API**: Can be imported and used in Python projects
- **Better error messages**: Rich exception hierarchy
- **Enhanced output**: Colored output with rich library
- **Type safety**: Full type hints throughout
- **Tested**: Comprehensive test suite
- **No install script**: Use standard Python package installation

## License

MIT License - see [LICENSE](LICENSE) file.

## Credits

Original bash implementation by [flowelfox](https://github.com/flowelfox).

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch (`wt new feature/your-feature`)
3. Make your changes
4. Run tests (`just test`)
5. Submit a pull request

## Troubleshooting

### "Not in a git repository"
- Ensure you're in a git repository
- Run `git init` if needed

### "Cannot create worktree from inside another worktree"
- Return to main repository with `wt detach`
- Or `cd` to the main repository manually

### Hook not running on Windows
- Ensure hook has proper extension (.ps1, .bat, or .sh with Git Bash)
- Check execution permissions

### Package manager not detected
- Ensure package files are present (package.json, requirements.txt, etc.)
- Check that the package manager is installed

### Tmux features not working
- Tmux is only available on Unix-like systems
- Ensure tmux is installed: `tmux -V`
- Check you're inside a tmux session: `echo $TMUX`