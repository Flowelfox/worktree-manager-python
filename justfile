# justfile for wtpython project

# Default recipe - show available commands
default:
    @just --list

# Install development dependencies
dev:
    uv sync --all-extras

# Run tests
test:
    uv run pytest

# Run tests with coverage
test-cov:
    uv run pytest --cov

# Run linting
lint:
    uv run ruff check src/ tests/

# Format code
format:
    uv run ruff format src/ tests/

# Run type checking (if mypy is added)
types:
    @echo "Type checking not configured yet"

# Run all checks
check: lint test

# Build package
build:
    uv build

# Clean build artifacts
clean:
    rm -rf dist/ build/ *.egg-info
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete
    rm -rf .coverage htmlcov/ .pytest_cache/

# Install package locally in editable mode
install:
    uv pip install -e .

# Run the CLI
run *ARGS:
    uv run wt {{ARGS}}

# Create a source distribution
sdist:
    uv build --sdist

# Create a wheel distribution
wheel:
    uv build --wheel

# Show installed version
version:
    @uv run python -c "import wtpython; print(wtpython.__version__)"

# Generate shell completions (if click supports it)
completions:
    @echo "Generating bash completions..."
    @uv run python -c "from wtpython.cli import cli; import click; click.echo(cli.make_context('wt', []).command.get_help_record(None))" || echo "Completion generation not implemented"

# Run a quick smoke test
smoke-test: install
    uv run wt --version
    uv run wt --help