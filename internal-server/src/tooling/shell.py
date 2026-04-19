"""Whitelisted shell execution for agent tools.

Agents run arbitrary commands under human accounts; a command whitelist
prevents the model from executing destructive host-level operations.
"""

from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path
from typing import List, Optional

DEFAULT_ALLOWED_BINARIES = frozenset(
    {
        "git",
        "python",
        "python3",
        "pytest",
        "ruff",
        "pip",
        "pip3",
        "ls",
        "cat",
        "echo",
        "docker",
        "semgrep",
        "trivy",
        "gitleaks",
    }
)


class ShellNotAllowedError(RuntimeError):
    """Raised when a command is not in the allow-list."""


class ShellResult(dict):
    """Convenience dict so the result serialises cleanly into tool output."""


def run_shell(
    command: str,
    cwd: str,
    *,
    timeout_s: int = 120,
    allowed_binaries: Optional[frozenset] = None,
    env: Optional[dict] = None,
) -> ShellResult:
    """Run ``command`` inside ``cwd`` with a binary allow-list.

    The first token must be a bare binary name present in
    ``allowed_binaries`` (default :data:`DEFAULT_ALLOWED_BINARIES`). No
    shell interpolation is performed; ``&&``, ``|``, ``;`` etc. are
    rejected outright.
    """
    if not command.strip():
        raise ShellNotAllowedError("Empty command")
    for forbidden in ("&&", "||", "|", ";", "`", "$(", ">", "<"):
        if forbidden in command:
            raise ShellNotAllowedError(
                f"Shell operator '{forbidden}' is not allowed in run_shell"
            )

    tokens = shlex.split(command)
    if not tokens:
        raise ShellNotAllowedError("Command parsed to no tokens")
    binary = os.path.basename(tokens[0])
    allow = allowed_binaries or DEFAULT_ALLOWED_BINARIES
    if binary not in allow:
        raise ShellNotAllowedError(
            f"Binary '{binary}' is not in the allow-list ({sorted(allow)})"
        )

    cwd_path = Path(cwd).expanduser().resolve()
    if not cwd_path.is_dir():
        raise ShellNotAllowedError(f"cwd is not a directory: {cwd}")

    merged_env = os.environ.copy()
    if env:
        merged_env.update({str(k): str(v) for k, v in env.items()})

    try:
        result = subprocess.run(
            tokens,
            cwd=str(cwd_path),
            env=merged_env,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return ShellResult(
            {
                "command": command,
                "cwd": str(cwd_path),
                "returncode": None,
                "timeout": True,
                "stdout": exc.stdout or "",
                "stderr": exc.stderr or "",
            }
        )

    return ShellResult(
        {
            "command": command,
            "cwd": str(cwd_path),
            "returncode": result.returncode,
            "timeout": False,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    )


def which(binary: str) -> Optional[str]:
    """Return the resolved path to ``binary`` or ``None`` if missing."""
    from shutil import which as _which

    return _which(binary)
