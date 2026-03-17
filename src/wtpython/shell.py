"""Shell integration for wtpython.

Generates shell wrapper functions that enable directory changing
after commands like attach, detach, new --open, and rm.

Usage:
    wt setup zsh       # Install into ~/.zshrc
    wt setup bash      # Install into ~/.bashrc
    eval "$(wt hook zsh)"  # Alternative: manual eval
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

BASH_ZSH_WRAPPER = """\
export WT_SHELL_SETUP=1

wt() {{
    local _wt_bin="{wt_bin}"
    local _wt_tmp
    case "$1" in
        attach|detach)
            _wt_tmp=$("$_wt_bin" "$@")
            [[ -n "$_wt_tmp" && -d "$_wt_tmp" ]] && cd "$_wt_tmp"
            ;;
        new)
            if [[ " $* " =~ " --open " ]]; then
                _wt_tmp=$("$_wt_bin" "$@")
                [[ -n "$_wt_tmp" && -d "$_wt_tmp" ]] && cd "$_wt_tmp"
            else
                "$_wt_bin" "$@"
            fi
            ;;
        rm)
            _wt_tmp=$("$_wt_bin" "$@")
            [[ -n "$_wt_tmp" && -d "$_wt_tmp" ]] && cd "$_wt_tmp"
            ;;
        setup)
            "$_wt_bin" "$@" && source "{rc_file}"
            if [[ " $* " =~ " --remove " ]]; then
                unset WT_SHELL_SETUP
                unfunction wt 2>/dev/null
            fi
            ;;
        *)
            "$_wt_bin" "$@"
            ;;
    esac
}}
"""

FISH_WRAPPER = """\
set -gx WT_SHELL_SETUP 1
set -g _wt_bin "{wt_bin}"

function wt
    switch $argv[1]
        case attach detach
            set -l path ($_wt_bin $argv)
            if test -n "$path" -a -d "$path"
                cd "$path"
            end
        case new
            if contains -- --open $argv
                set -l path ($_wt_bin $argv)
                if test -n "$path" -a -d "$path"
                    cd "$path"
                end
            else
                $_wt_bin $argv
            end
        case rm
            set -l path ($_wt_bin $argv)
            if test -n "$path" -a -d "$path"
                cd "$path"
            end
        case setup
            $_wt_bin $argv; and source {rc_file}
            if contains -- --remove $argv
                set -e WT_SHELL_SETUP
                functions -e wt
            end
        case '*'
            $_wt_bin $argv
    end
end
"""

POWERSHELL_WRAPPER = """\
$env:WT_SHELL_SETUP = "1"
$_wt_bin = "{wt_bin}"

function wt {{
    $cmd = $args[0]
    $rest = $args[1..($args.Length - 1)]
    switch ($cmd) {{
        {{ $_ -in "attach", "detach" }} {{
            $path = & $_wt_bin $args
            if ($path -and (Test-Path $path)) {{ Set-Location $path }}
        }}
        "new" {{
            if ($rest -contains "--open") {{
                $path = & $_wt_bin $args
                if ($path -and (Test-Path $path)) {{ Set-Location $path }}
            }} else {{
                & $_wt_bin $args
            }}
        }}
        "rm" {{
            $path = & $_wt_bin $args
            if ($path -and (Test-Path $path)) {{ Set-Location $path }}
        }}
        "setup" {{
            & $_wt_bin $args
            if ($?) {{ . $PROFILE }}
            if ($rest -contains "--remove") {{
                Remove-Item Env:WT_SHELL_SETUP -ErrorAction SilentlyContinue
                Remove-Item Function:wt -ErrorAction SilentlyContinue
            }}
        }}
        default {{
            & $_wt_bin $args
        }}
    }}
}}
"""

SHELL_TEMPLATES: dict[str, str] = {
    "bash": BASH_ZSH_WRAPPER,
    "zsh": BASH_ZSH_WRAPPER,
    "fish": FISH_WRAPPER,
    "powershell": POWERSHELL_WRAPPER,
    "pwsh": POWERSHELL_WRAPPER,
}

SUPPORTED_SHELLS: set[str] = set(SHELL_TEMPLATES)

HOOK_LINE: dict[str, str] = {
    "bash": 'eval "$(wt hook bash)"',
    "zsh": 'eval "$(wt hook zsh)"',
    "fish": "wt hook fish | source",
    "powershell": "wt hook powershell | Invoke-Expression",
    "pwsh": "wt hook pwsh | Invoke-Expression",
}

RC_FILE: dict[str, Path] = {
    "bash": Path.home() / ".bashrc",
    "zsh": Path.home() / ".zshrc",
    "fish": Path.home() / ".config" / "fish" / "config.fish",
    "powershell": Path.home() / ".config" / "powershell" / "Microsoft.PowerShell_profile.ps1",
    "pwsh": Path.home() / ".config" / "powershell" / "Microsoft.PowerShell_profile.ps1",
}

COMPLETION_ENV_VARS: dict[str, str] = {
    "bash": "bash_source",
    "zsh": "zsh_source",
    "fish": "fish_source",
}


def _find_wt_bin() -> str:
    """Find the wt binary path."""
    wt_path = shutil.which("wt")
    if wt_path:
        return wt_path
    # Fallback: derive from current Python's bin directory
    return str(Path(sys.executable).parent / "wt")


def _get_completions(shell: str) -> str:
    """Generate Click shell completions by invoking wt with the completion env var."""
    env_value = COMPLETION_ENV_VARS.get(shell)
    if not env_value:
        return ""

    env = {**os.environ, "_WT_COMPLETE": env_value}
    wt_path = _find_wt_bin()
    try:
        result = subprocess.run(
            [wt_path],
            env=env,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0 and result.stdout.strip():
            return "\n" + result.stdout
    except OSError:
        pass
    return ""


def get_shell_init(shell: str) -> str:
    """Get shell wrapper function and completions for the given shell.

    Args:
        shell: Shell name (bash, zsh, fish, powershell, pwsh).

    Returns:
        Shell function code to be eval'd.

    Raises:
        ValueError: If shell is not supported.
    """
    shell = shell.lower()
    if shell not in SHELL_TEMPLATES:
        supported = ", ".join(sorted(SUPPORTED_SHELLS))
        msg = f"Unsupported shell: {shell}. Supported: {supported}"
        raise ValueError(msg)

    wt_bin = _find_wt_bin()
    rc_file = RC_FILE[shell]
    wrapper = SHELL_TEMPLATES[shell].format(wt_bin=wt_bin, rc_file=rc_file)
    return wrapper + _get_completions(shell)


def install_shell_integration(shell: str) -> tuple[Path, bool]:
    """Install shell integration into the user's shell config file.

    Appends the hook eval line to the shell's rc file if not already present.

    Args:
        shell: Shell name (bash, zsh, fish, powershell, pwsh).

    Returns:
        Tuple of (rc_file_path, was_installed). was_installed is False if already present.

    Raises:
        ValueError: If shell is not supported.
    """
    shell = shell.lower()
    if shell not in SHELL_TEMPLATES:
        supported = ", ".join(sorted(SUPPORTED_SHELLS))
        msg = f"Unsupported shell: {shell}. Supported: {supported}"
        raise ValueError(msg)

    rc_file = RC_FILE[shell]
    hook_line = HOOK_LINE[shell]

    # Check if already installed
    if rc_file.exists():
        content = rc_file.read_text()
        if hook_line in content:
            return rc_file, False

    # Ensure parent directory exists
    rc_file.parent.mkdir(parents=True, exist_ok=True)

    # Append hook line
    with rc_file.open("a") as f:
        f.write(f"\n# wt - Git Worktree Manager\n{hook_line}\n")

    return rc_file, True


def remove_shell_integration(shell: str) -> tuple[Path, bool]:
    """Remove shell integration from the user's shell config file.

    Args:
        shell: Shell name (bash, zsh, fish, powershell, pwsh).

    Returns:
        Tuple of (rc_file_path, was_removed). was_removed is False if not installed.

    Raises:
        ValueError: If shell is not supported.
    """
    shell = shell.lower()
    if shell not in SHELL_TEMPLATES:
        supported = ", ".join(sorted(SUPPORTED_SHELLS))
        msg = f"Unsupported shell: {shell}. Supported: {supported}"
        raise ValueError(msg)

    rc_file = RC_FILE[shell]
    hook_line = HOOK_LINE[shell]

    if not rc_file.exists():
        return rc_file, False

    content = rc_file.read_text()
    if hook_line not in content:
        return rc_file, False

    # Remove the comment + hook line block
    lines = content.splitlines(keepends=True)
    new_lines = []
    skip_next = False
    for line in lines:
        if line.strip() == "# wt - Git Worktree Manager":
            skip_next = True
            continue
        if skip_next and hook_line in line:
            skip_next = False
            continue
        skip_next = False
        new_lines.append(line)

    # Remove trailing blank lines left behind
    while new_lines and new_lines[-1].strip() == "":
        new_lines.pop()
    if new_lines:
        new_lines[-1] = new_lines[-1].rstrip("\n") + "\n"

    rc_file.write_text("".join(new_lines))
    return rc_file, True
