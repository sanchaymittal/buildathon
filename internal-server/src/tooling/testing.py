"""Test runners for Forge."""

from __future__ import annotations

from typing import Optional

from .shell import run_shell


def run_pytest(cwd: str, pattern: Optional[str] = None, timeout_s: int = 300) -> dict:
    """Run pytest with an optional keyword expression."""
    cmd = "pytest -q --no-header"
    if pattern:
        # -k takes a keyword expression, still inside the shell whitelist.
        cmd = f"{cmd} -k {pattern}"
    result = run_shell(cmd, cwd=cwd, timeout_s=timeout_s)
    return {
        "command": cmd,
        "returncode": result.get("returncode"),
        "timeout": result.get("timeout"),
        "stdout": result.get("stdout", ""),
        "stderr": result.get("stderr", ""),
        "passed": result.get("returncode") == 0 and not result.get("timeout"),
    }
