"""Tests for shell integration module."""

from pathlib import Path

import pytest

from wtpython.shell import (
    BASH_ZSH_WRAPPER,
    FISH_WRAPPER,
    HOOK_LINE,
    POWERSHELL_WRAPPER,
    SHELL_TEMPLATES,
    SUPPORTED_SHELLS,
    _get_completions,
    get_shell_init,
    install_shell_integration,
    remove_shell_integration,
)


class TestGetShellInit:
    """Test get_shell_init function."""

    def test_returns_bash_wrapper_with_bin_path(self) -> None:
        result = get_shell_init("bash")
        assert "export WT_SHELL_SETUP=1" in result
        assert "wt() {" in result

    def test_returns_zsh_wrapper_with_bin_path(self) -> None:
        result = get_shell_init("zsh")
        assert "export WT_SHELL_SETUP=1" in result
        assert "wt() {" in result

    def test_bash_and_zsh_share_template(self) -> None:
        """Bash and zsh use the same wrapper template (completions may differ)."""
        assert SHELL_TEMPLATES["bash"] == SHELL_TEMPLATES["zsh"]

    def test_embeds_wt_binary_path(self, monkeypatch) -> None:
        monkeypatch.setattr("wtpython.shell.shutil.which", lambda _: "/usr/local/bin/wt")
        result = get_shell_init("zsh")
        assert "/usr/local/bin/wt" in result

    def test_returns_fish_wrapper(self) -> None:
        result = get_shell_init("fish")
        assert "set -gx WT_SHELL_SETUP 1" in result
        assert "function wt" in result

    def test_returns_powershell_wrapper(self) -> None:
        result = get_shell_init("powershell")
        assert '$env:WT_SHELL_SETUP = "1"' in result
        assert "function wt {" in result

    def test_pwsh_alias(self) -> None:
        assert get_shell_init("pwsh") == get_shell_init("powershell")

    def test_case_insensitive(self) -> None:
        assert get_shell_init("ZSH") == get_shell_init("zsh")
        assert get_shell_init("Bash") == get_shell_init("bash")
        assert get_shell_init("FISH") == get_shell_init("fish")

    def test_unsupported_shell_raises(self) -> None:
        with pytest.raises(ValueError, match="Unsupported shell: tcsh"):
            get_shell_init("tcsh")

    def test_unsupported_shell_lists_supported(self) -> None:
        with pytest.raises(ValueError, match="Supported:"):
            get_shell_init("nushell")


class TestWrapperTemplateContent:
    """Test that wrapper templates contain expected shell constructs."""

    def test_bash_zsh_sets_env_var(self) -> None:
        assert "export WT_SHELL_SETUP=1" in BASH_ZSH_WRAPPER

    def test_bash_zsh_defines_function(self) -> None:
        assert "wt() {{" in BASH_ZSH_WRAPPER

    def test_bash_zsh_has_wt_bin_placeholder(self) -> None:
        assert "{wt_bin}" in BASH_ZSH_WRAPPER

    def test_bash_zsh_handles_attach(self) -> None:
        assert "attach|detach)" in BASH_ZSH_WRAPPER

    def test_bash_zsh_handles_new_open(self) -> None:
        assert "--open" in BASH_ZSH_WRAPPER

    def test_bash_zsh_handles_rm(self) -> None:
        assert "rm)" in BASH_ZSH_WRAPPER

    def test_bash_zsh_uses_wt_bin_var(self) -> None:
        assert '"$_wt_bin" "$@"' in BASH_ZSH_WRAPPER

    def test_fish_sets_env_var(self) -> None:
        assert "set -gx WT_SHELL_SETUP 1" in FISH_WRAPPER

    def test_fish_defines_function(self) -> None:
        assert "function wt" in FISH_WRAPPER

    def test_fish_has_wt_bin_placeholder(self) -> None:
        assert "{wt_bin}" in FISH_WRAPPER

    def test_powershell_sets_env_var(self) -> None:
        assert '$env:WT_SHELL_SETUP = "1"' in POWERSHELL_WRAPPER

    def test_powershell_defines_function(self) -> None:
        assert "function wt {{" in POWERSHELL_WRAPPER

    def test_powershell_has_wt_bin_placeholder(self) -> None:
        assert "{wt_bin}" in POWERSHELL_WRAPPER


class TestGetCompletions:
    """Test completion generation."""

    def test_unsupported_shell_returns_empty(self) -> None:
        assert _get_completions("powershell") == ""
        assert _get_completions("pwsh") == ""

    def test_subprocess_error_returns_empty(self, monkeypatch) -> None:
        monkeypatch.setattr(
            "wtpython.shell.subprocess.run",
            lambda *a, **kw: (_ for _ in ()).throw(OSError("not found")),
        )
        assert _get_completions("zsh") == ""


class TestInstallShellIntegration:
    """Test install_shell_integration function."""

    def test_installs_hook_line_to_rc_file(self, tmp_path, monkeypatch) -> None:
        rc_file = tmp_path / ".zshrc"
        monkeypatch.setitem(
            __import__("wtpython.shell", fromlist=["RC_FILE"]).RC_FILE,
            "zsh",
            rc_file,
        )
        path, was_installed = install_shell_integration("zsh")
        assert was_installed is True
        assert path == rc_file
        content = rc_file.read_text()
        assert HOOK_LINE["zsh"] in content
        assert "# wt - Git Worktree Manager" in content

    def test_idempotent_does_not_duplicate(self, tmp_path, monkeypatch) -> None:
        rc_file = tmp_path / ".zshrc"
        monkeypatch.setitem(
            __import__("wtpython.shell", fromlist=["RC_FILE"]).RC_FILE,
            "zsh",
            rc_file,
        )
        install_shell_integration("zsh")
        path, was_installed = install_shell_integration("zsh")
        assert was_installed is False
        content = rc_file.read_text()
        assert content.count(HOOK_LINE["zsh"]) == 1

    def test_appends_to_existing_rc_file(self, tmp_path, monkeypatch) -> None:
        rc_file = tmp_path / ".bashrc"
        rc_file.write_text("# existing config\nexport FOO=bar\n")
        monkeypatch.setitem(
            __import__("wtpython.shell", fromlist=["RC_FILE"]).RC_FILE,
            "bash",
            rc_file,
        )
        install_shell_integration("bash")
        content = rc_file.read_text()
        assert content.startswith("# existing config\n")
        assert HOOK_LINE["bash"] in content

    def test_creates_parent_directories(self, tmp_path, monkeypatch) -> None:
        rc_file = tmp_path / "deep" / "nested" / "config.fish"
        monkeypatch.setitem(
            __import__("wtpython.shell", fromlist=["RC_FILE"]).RC_FILE,
            "fish",
            rc_file,
        )
        path, was_installed = install_shell_integration("fish")
        assert was_installed is True
        assert rc_file.exists()

    def test_unsupported_shell_raises(self) -> None:
        with pytest.raises(ValueError, match="Unsupported shell"):
            install_shell_integration("tcsh")

    def test_all_shells_have_hook_lines(self) -> None:
        for shell in SUPPORTED_SHELLS:
            assert shell in HOOK_LINE, f"Missing HOOK_LINE for {shell}"


class TestRemoveShellIntegration:
    """Test remove_shell_integration function."""

    def _setup_rc(self, tmp_path, monkeypatch, shell="zsh", ext=".zshrc"):
        rc_file = tmp_path / ext
        monkeypatch.setitem(
            __import__("wtpython.shell", fromlist=["RC_FILE"]).RC_FILE,
            shell,
            rc_file,
        )
        return rc_file

    def test_removes_hook_line(self, tmp_path, monkeypatch) -> None:
        rc_file = self._setup_rc(tmp_path, monkeypatch)
        install_shell_integration("zsh")
        assert HOOK_LINE["zsh"] in rc_file.read_text()

        path, was_removed = remove_shell_integration("zsh")
        assert was_removed is True
        assert path == rc_file
        content = rc_file.read_text()
        assert HOOK_LINE["zsh"] not in content
        assert "# wt - Git Worktree Manager" not in content

    def test_preserves_other_content(self, tmp_path, monkeypatch) -> None:
        rc_file = self._setup_rc(tmp_path, monkeypatch, "bash", ".bashrc")
        rc_file.write_text("# my config\nexport FOO=bar\n")
        install_shell_integration("bash")

        remove_shell_integration("bash")
        content = rc_file.read_text()
        assert "export FOO=bar" in content
        assert HOOK_LINE["bash"] not in content

    def test_not_installed_returns_false(self, tmp_path, monkeypatch) -> None:
        rc_file = self._setup_rc(tmp_path, monkeypatch)
        rc_file.write_text("# empty config\n")
        path, was_removed = remove_shell_integration("zsh")
        assert was_removed is False

    def test_no_rc_file_returns_false(self, tmp_path, monkeypatch) -> None:
        self._setup_rc(tmp_path, monkeypatch)
        path, was_removed = remove_shell_integration("zsh")
        assert was_removed is False

    def test_unsupported_shell_raises(self) -> None:
        with pytest.raises(ValueError, match="Unsupported shell"):
            remove_shell_integration("tcsh")

    def test_idempotent(self, tmp_path, monkeypatch) -> None:
        rc_file = self._setup_rc(tmp_path, monkeypatch)
        install_shell_integration("zsh")
        remove_shell_integration("zsh")
        _, was_removed = remove_shell_integration("zsh")
        assert was_removed is False


class TestSupportedShells:
    """Test SUPPORTED_SHELLS mapping."""

    def test_all_expected_shells_present(self) -> None:
        expected = {"bash", "zsh", "fish", "powershell", "pwsh"}
        assert SUPPORTED_SHELLS == expected
