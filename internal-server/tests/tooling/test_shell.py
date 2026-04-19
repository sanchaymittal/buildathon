"""Tests for the shell runner's whitelist."""

from __future__ import annotations

import pytest

from src.tooling.shell import ShellNotAllowedError, run_shell


def test_empty_command_rejected(tmp_path):
    with pytest.raises(ShellNotAllowedError):
        run_shell("", cwd=str(tmp_path))


def test_non_whitelisted_rejected(tmp_path):
    with pytest.raises(ShellNotAllowedError):
        run_shell("curl https://example.com", cwd=str(tmp_path))


@pytest.mark.parametrize("bad", ["ls && rm", "ls | grep foo", "ls > out", "ls; rm"])
def test_shell_operators_rejected(bad, tmp_path):
    with pytest.raises(ShellNotAllowedError):
        run_shell(bad, cwd=str(tmp_path))


def test_allowed_echo_runs(tmp_path):
    result = run_shell("echo hello", cwd=str(tmp_path))
    assert result["returncode"] == 0
    assert "hello" in result["stdout"]


def test_cwd_must_be_directory(tmp_path):
    missing = tmp_path / "nope"
    with pytest.raises(ShellNotAllowedError):
        run_shell("echo hi", cwd=str(missing))
