"""Package manager detection with cross-platform support."""

import os
import subprocess
from pathlib import Path


class PackageManagerDetector:
    """Detect and run package managers."""

    @staticmethod
    def detect(worktree_path: Path) -> str | None:
        """Detect package manager and return install command."""
        # Node.js / JavaScript
        if (worktree_path / "package.json").exists():
            if (worktree_path / "pnpm-lock.yaml").exists():
                return "pnpm install"
            elif (worktree_path / "yarn.lock").exists():
                return "yarn install"
            elif (worktree_path / "bun.lockb").exists():
                return "bun install"
            else:
                return "npm install"

        # Python
        if (worktree_path / "pyproject.toml").exists():
            pyproject = (worktree_path / "pyproject.toml").read_text()
            if "poetry" in pyproject:
                return "poetry install"
            elif (worktree_path / "uv.lock").exists():
                return "uv sync"
            else:
                return "pip install -e ."
        elif (worktree_path / "requirements.txt").exists():
            return "pip install -r requirements.txt"
        elif (worktree_path / "Pipfile").exists():
            return "pipenv install"

        # Rust
        if (worktree_path / "Cargo.toml").exists():
            return "cargo build"

        # Go
        if (worktree_path / "go.mod").exists():
            return "go mod download"

        # Ruby
        if (worktree_path / "Gemfile").exists():
            return "bundle install"

        # .NET
        if any(worktree_path.glob("*.csproj")) or any(worktree_path.glob("*.fsproj")):
            return "dotnet restore"

        # Java/Gradle
        if (worktree_path / "build.gradle").exists() or (
            worktree_path / "build.gradle.kts"
        ).exists():
            if os.name == "nt":
                return "gradlew.bat build"
            else:
                return "./gradlew build"

        # Java/Maven
        if (worktree_path / "pom.xml").exists():
            return "mvn install"

        return None

    @staticmethod
    def run_install(worktree_path: Path, command: str) -> bool:
        """Run package manager install command."""
        try:
            # Handle special cases for Windows
            if os.name == "nt":
                # Use cmd.exe for better compatibility on Windows
                result = subprocess.run(
                    command,
                    cwd=worktree_path,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=300,  # 5 minute timeout
                )
            else:
                # On Unix-like systems, use shell for consistency
                result = subprocess.run(
                    command,
                    cwd=worktree_path,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            return False
        except Exception:
            return False
