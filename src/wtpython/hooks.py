"""Hook execution with cross-platform support."""

import os
import subprocess
from pathlib import Path

from .exceptions import HookExecutionError
from .output import log_info


class HookExecutor:
    """Execute hooks with cross-platform support."""

    @staticmethod
    def run_hook(
        hook_file: Path | None,
        worktree_path: Path,
        branch: str,
        hook_name: str,
    ) -> bool:
        """Run a hook script if it exists and is executable."""
        if not hook_file or not hook_file.exists():
            return True

        # Check if file is executable (on Unix-like systems)
        if os.name != "nt" and not os.access(hook_file, os.X_OK):
            return True

        log_info(f"Running {hook_name} hook...", stderr=True)

        try:
            # On Windows, use the appropriate shell
            if os.name == "nt":
                # Try to detect the script type
                first_line = (
                    hook_file.read_text().splitlines()[0] if hook_file.stat().st_size > 0 else ""
                )

                if hook_file.suffix == ".ps1" or "powershell" in first_line.lower():
                    # PowerShell script
                    cmd = ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(hook_file)]
                elif hook_file.suffix == ".bat" or hook_file.suffix == ".cmd":
                    # Batch script
                    cmd = ["cmd", "/c", str(hook_file)]
                else:
                    # Try bash if available (Git Bash, WSL, etc.)
                    cmd = ["bash", str(hook_file)]
            else:
                # On Unix-like systems, execute directly
                cmd = [str(hook_file)]

            # Add arguments
            cmd.extend([str(worktree_path), branch])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,  # 1 minute timeout
            )

            if result.returncode != 0:
                raise HookExecutionError(
                    f"{hook_name} hook failed with exit code {result.returncode}: {result.stderr}"
                )

            return True

        except subprocess.TimeoutExpired:
            raise HookExecutionError(f"{hook_name} hook timed out") from None
        except FileNotFoundError as e:
            # If bash is not found on Windows, skip the hook
            if os.name == "nt" and "bash" in str(e):
                log_info(f"Skipping {hook_name} hook (bash not available on Windows)", stderr=True)
                return True
            raise HookExecutionError(f"Failed to execute {hook_name} hook: {e}") from e
        except Exception as e:
            raise HookExecutionError(f"Failed to execute {hook_name} hook: {e}") from e
