"""Git plumbing for Forge and Axiom.

Each function is a thin wrapper around ``git`` via :func:`run_shell`. All
paths must already be inside the project root; no cross-root mutation.
"""

from __future__ import annotations

from typing import Optional

from .shell import ShellResult, run_shell


class GitError(RuntimeError):
    pass


def _git(args: str, cwd: str, timeout_s: int = 60) -> ShellResult:
    result = run_shell(f"git {args}", cwd=cwd, timeout_s=timeout_s)
    if result.get("returncode") not in (0, None):
        raise GitError(
            f"git {args} failed (rc={result.get('returncode')}): "
            f"{(result.get('stderr') or '').strip()}"
        )
    return result


def create_branch(cwd: str, name: str) -> dict:
    """Create-or-checkout a branch."""
    # git checkout -B idempotently points the branch at HEAD.
    result = _git(f"checkout -B {name}", cwd=cwd)
    return {"branch": name, "stdout": result["stdout"], "stderr": result["stderr"]}


def current_branch(cwd: str) -> str:
    result = _git("rev-parse --abbrev-ref HEAD", cwd=cwd)
    return (result["stdout"] or "").strip()


def status(cwd: str) -> str:
    result = _git("status --short --branch", cwd=cwd)
    return result["stdout"] or ""


def commit_all(cwd: str, message: str) -> dict:
    # Stage everything, commit; if there's nothing staged git commit returns
    # non-zero and we surface that as a no-op.
    _git("add -A", cwd=cwd)
    staged = run_shell("git diff --cached --name-only", cwd=cwd)
    changed_files = [
        line.strip()
        for line in (staged.get("stdout") or "").splitlines()
        if line.strip()
    ]
    if not changed_files:
        return {"committed": False, "reason": "no changes staged"}
    result = _git(f"commit -m {_quote(message)}", cwd=cwd)
    sha_result = _git("rev-parse HEAD", cwd=cwd)
    return {
        "committed": True,
        "files": changed_files,
        "sha": (sha_result["stdout"] or "").strip(),
        "stdout": result["stdout"],
    }


def rev_parse_head(cwd: str) -> Optional[str]:
    try:
        result = _git("rev-parse HEAD", cwd=cwd)
    except GitError:
        return None
    return (result["stdout"] or "").strip() or None


def push_branch(cwd: str, branch: Optional[str] = None, remote: str = "origin") -> dict:
    """Push ``branch`` (or current) to ``remote``.

    If the remote isn't configured this is a no-op that logs why.
    """
    target = branch or current_branch(cwd)
    remotes = run_shell("git remote", cwd=cwd).get("stdout") or ""
    if remote not in remotes.split():
        return {
            "pushed": False,
            "reason": f"remote '{remote}' not configured; skipping push",
            "branch": target,
        }
    result = _git(f"push -u {remote} {target}", cwd=cwd, timeout_s=90)
    return {
        "pushed": True,
        "branch": target,
        "remote": remote,
        "stdout": result["stdout"],
        "stderr": result["stderr"],
    }


def _quote(value: str) -> str:
    # The value goes into a command string; shlex.quote keeps spaces / $ safe.
    import shlex

    return shlex.quote(value)
