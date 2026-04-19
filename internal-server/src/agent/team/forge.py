"""Forge - staff engineer.

Writes the diff. Owns the branch. Runs tests. Stays inside the project
sandbox enforced by the filesystem helpers.
"""

from __future__ import annotations

from typing import Any, List, Optional

from ...gemini_agents import Agent, function_tool, RunContextWrapper
from ...tooling import fs as fs_tools
from ...tooling import git_tools
from ...tooling import testing as testing_tools
from ...tooling.shell import ShellNotAllowedError, run_shell as shell_run
from .context import TeamContext, TeamRunStatus

FORGE_SYSTEM_PROMPT = """\
You are Forge, the staff engineer on the DevOps team.

You own the implementation: plan the change, apply a minimal diff, add or
update tests, run the test suite, and push the branch. You never touch
paths outside the project root that is passed to you via the shared
TeamContext. You never run destructive shell commands.

Workflow (default):
  1. read_file / list_files to orient yourself.
  2. apply_patch (preferred) or write_file to edit.
  3. run_pytest to verify.
  4. create_branch + commit_all + push_branch.
  5. Record the final commit_sha via record_commit.

Keep changes minimal and well-documented. Return a concise summary with
the commit sha, changed files, and test outcome.
"""


def _ensure_project_path(ctx: RunContextWrapper[TeamContext]) -> str:
    team = ctx.context
    if team is None or not team.project_path:
        raise RuntimeError("Forge requires TeamContext.project_path to be set")
    return team.project_path


def _read_file_tool():
    @function_tool()
    async def read_file(
        ctx: RunContextWrapper[TeamContext], path: str, max_bytes: int = 200000
    ) -> dict:
        """Read a file inside the project root."""
        root = _ensure_project_path(ctx)
        content = fs_tools.read_file(root, path, max_bytes=max_bytes)
        return {"path": path, "content": content}

    return read_file


def _write_file_tool():
    @function_tool()
    async def write_file(
        ctx: RunContextWrapper[TeamContext], path: str, content: str
    ) -> dict:
        """Create or overwrite a file inside the project root."""
        root = _ensure_project_path(ctx)
        return fs_tools.write_file(root, path, content)

    return write_file


def _list_files_tool():
    @function_tool()
    async def list_files(
        ctx: RunContextWrapper[TeamContext], directory: str = "."
    ) -> dict:
        root = _ensure_project_path(ctx)
        return {"entries": fs_tools.list_files(root, directory)}

    return list_files


def _apply_patch_tool():
    @function_tool()
    async def apply_patch(
        ctx: RunContextWrapper[TeamContext], unified_diff: str
    ) -> dict:
        """Apply a unified-diff patch via ``git apply``."""
        root = _ensure_project_path(ctx)
        return fs_tools.apply_patch(root, unified_diff)

    return apply_patch


def _run_shell_tool():
    @function_tool()
    async def run_shell(
        ctx: RunContextWrapper[TeamContext], command: str, timeout_s: int = 120
    ) -> dict:
        """Run a whitelisted shell command inside the project root."""
        root = _ensure_project_path(ctx)
        try:
            return shell_run(command, cwd=root, timeout_s=timeout_s)
        except ShellNotAllowedError as exc:
            return {"ok": False, "error": str(exc), "command": command}

    return run_shell


def _run_tests_tool():
    @function_tool()
    async def run_pytest(
        ctx: RunContextWrapper[TeamContext], pattern: Optional[str] = None
    ) -> dict:
        root = _ensure_project_path(ctx)
        return testing_tools.run_pytest(cwd=root, pattern=pattern)

    return run_pytest


def _create_branch_tool():
    @function_tool()
    async def create_branch(ctx: RunContextWrapper[TeamContext], name: str) -> dict:
        root = _ensure_project_path(ctx)
        result = git_tools.create_branch(root, name)
        ctx.context.branch = name
        return result

    return create_branch


def _commit_all_tool():
    @function_tool()
    async def commit_all(ctx: RunContextWrapper[TeamContext], message: str) -> dict:
        root = _ensure_project_path(ctx)
        result = git_tools.commit_all(root, message)
        if result.get("committed") and result.get("sha"):
            ctx.context.commit_sha = result["sha"]
        return result

    return commit_all


def _push_branch_tool():
    @function_tool()
    async def push_branch(
        ctx: RunContextWrapper[TeamContext],
        branch: Optional[str] = None,
        remote: str = "origin",
    ) -> dict:
        root = _ensure_project_path(ctx)
        return git_tools.push_branch(root, branch=branch, remote=remote)

    return push_branch


def _record_commit_tool():
    @function_tool()
    async def record_commit(
        ctx: RunContextWrapper[TeamContext], sha: str, branch: Optional[str] = None
    ) -> dict:
        """Record the final commit sha and branch on the team context."""
        ctx.context.commit_sha = sha
        if branch:
            ctx.context.branch = branch
        if ctx.context.status == TeamRunStatus.planning:
            ctx.context.set_status(
                TeamRunStatus.engineering, note=f"Forge recorded commit {sha[:12]}"
            )
        return {"commit_sha": sha, "branch": branch}

    return record_commit


def build_forge(*, model: str = "gemini-2.5-pro") -> Agent:
    tools: List[Any] = [
        _read_file_tool(),
        _write_file_tool(),
        _list_files_tool(),
        _apply_patch_tool(),
        _run_shell_tool(),
        _run_tests_tool(),
        _create_branch_tool(),
        _commit_all_tool(),
        _push_branch_tool(),
        _record_commit_tool(),
    ]
    return Agent(
        name="Forge",
        instructions=FORGE_SYSTEM_PROMPT,
        tools=tools,
        model=model,
    )
