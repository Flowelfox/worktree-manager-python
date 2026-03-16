"""Tests for CLI setup/hook commands and auto shell setup."""

from click.testing import CliRunner

from wtpython.cli import _auto_shell_setup, _detect_shell, cli


class TestSetupCommand:
    """Test the `wt setup` CLI command."""

    def test_setup_zsh_installs(self, tmp_path, monkeypatch) -> None:
        rc_file = tmp_path / ".zshrc"
        monkeypatch.setitem(
            __import__("wtpython.shell", fromlist=["RC_FILE"]).RC_FILE, "zsh", rc_file
        )
        runner = CliRunner()
        result = runner.invoke(cli, ["setup", "zsh"])
        assert result.exit_code == 0
        assert "Added shell integration" in result.output
        assert rc_file.exists()

    def test_setup_already_installed(self, tmp_path, monkeypatch) -> None:
        rc_file = tmp_path / ".zshrc"
        monkeypatch.setitem(
            __import__("wtpython.shell", fromlist=["RC_FILE"]).RC_FILE, "zsh", rc_file
        )
        runner = CliRunner()
        runner.invoke(cli, ["setup", "zsh"])
        result = runner.invoke(cli, ["setup", "zsh"])
        assert result.exit_code == 0
        assert "already installed" in result.output

    def test_setup_shows_source_hint(self, tmp_path, monkeypatch) -> None:
        rc_file = tmp_path / ".zshrc"
        monkeypatch.setitem(
            __import__("wtpython.shell", fromlist=["RC_FILE"]).RC_FILE, "zsh", rc_file
        )
        runner = CliRunner()
        result = runner.invoke(cli, ["setup", "zsh"])
        assert "source" in result.output or "restart" in result.output

    def test_setup_invalid_shell(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["setup", "tcsh"])
        assert result.exit_code != 0

    def test_setup_no_argument(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["setup"])
        assert result.exit_code != 0

    def test_setup_remove(self, tmp_path, monkeypatch) -> None:
        rc_file = tmp_path / ".zshrc"
        monkeypatch.setitem(
            __import__("wtpython.shell", fromlist=["RC_FILE"]).RC_FILE, "zsh", rc_file
        )
        runner = CliRunner()
        runner.invoke(cli, ["setup", "zsh"])
        result = runner.invoke(cli, ["setup", "zsh", "--remove"])
        assert result.exit_code == 0
        assert "Removed shell integration" in result.output

    def test_setup_remove_not_installed(self, tmp_path, monkeypatch) -> None:
        rc_file = tmp_path / ".zshrc"
        rc_file.write_text("# empty\n")
        monkeypatch.setitem(
            __import__("wtpython.shell", fromlist=["RC_FILE"]).RC_FILE, "zsh", rc_file
        )
        runner = CliRunner()
        result = runner.invoke(cli, ["setup", "zsh", "--remove"])
        assert result.exit_code == 0
        assert "not found" in result.output


class TestHookCommand:
    """Test the `wt hook` CLI command."""

    def test_hook_zsh(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["hook", "zsh"])
        assert result.exit_code == 0
        assert "wt()" in result.output
        assert "export WT_SHELL_SETUP=1" in result.output

    def test_hook_bash(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["hook", "bash"])
        assert result.exit_code == 0
        assert "wt()" in result.output

    def test_hook_fish(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["hook", "fish"])
        assert result.exit_code == 0
        assert "function wt" in result.output
        assert "set -gx WT_SHELL_SETUP 1" in result.output

    def test_hook_powershell(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["hook", "powershell"])
        assert result.exit_code == 0
        assert "function wt {" in result.output

    def test_hook_invalid_shell(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["hook", "tcsh"])
        assert result.exit_code != 0

    def test_hook_case_insensitive(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["hook", "ZSH"])
        assert result.exit_code == 0
        assert "wt()" in result.output


class TestDetectShell:
    """Test shell detection from environment."""

    def test_detects_zsh(self, monkeypatch) -> None:
        monkeypatch.setenv("SHELL", "/bin/zsh")
        assert _detect_shell() == "zsh"

    def test_detects_bash(self, monkeypatch) -> None:
        monkeypatch.setenv("SHELL", "/usr/bin/bash")
        assert _detect_shell() == "bash"

    def test_detects_fish(self, monkeypatch) -> None:
        monkeypatch.setenv("SHELL", "/usr/local/bin/fish")
        assert _detect_shell() == "fish"

    def test_no_shell_env(self, monkeypatch) -> None:
        monkeypatch.delenv("SHELL", raising=False)
        assert _detect_shell() is None

    def test_empty_shell_env(self, monkeypatch) -> None:
        monkeypatch.setenv("SHELL", "")
        assert _detect_shell() is None


class TestAutoShellSetup:
    """Test automatic shell setup on first run."""

    def test_skips_when_wt_shell_setup_set(self, monkeypatch, capsys) -> None:
        monkeypatch.setenv("WT_SHELL_SETUP", "1")
        monkeypatch.setenv("SHELL", "/bin/zsh")
        _auto_shell_setup()
        captured = capsys.readouterr()
        assert captured.err == ""

    def test_installs_on_first_run(self, tmp_path, monkeypatch, capsys) -> None:
        rc_file = tmp_path / ".zshrc"
        monkeypatch.delenv("WT_SHELL_SETUP", raising=False)
        monkeypatch.setenv("SHELL", "/bin/zsh")
        monkeypatch.setitem(
            __import__("wtpython.shell", fromlist=["RC_FILE"]).RC_FILE, "zsh", rc_file
        )
        _auto_shell_setup()
        captured = capsys.readouterr()
        assert "initial setup" in captured.err
        assert "Shell integration added" in captured.err
        assert rc_file.exists()

    def test_skips_unsupported_shell(self, monkeypatch, capsys) -> None:
        monkeypatch.delenv("WT_SHELL_SETUP", raising=False)
        monkeypatch.setenv("SHELL", "/bin/tcsh")
        _auto_shell_setup()
        captured = capsys.readouterr()
        assert captured.err == ""

    def test_skips_when_shell_unset(self, monkeypatch, capsys) -> None:
        monkeypatch.delenv("WT_SHELL_SETUP", raising=False)
        monkeypatch.delenv("SHELL", raising=False)
        _auto_shell_setup()
        captured = capsys.readouterr()
        assert captured.err == ""
