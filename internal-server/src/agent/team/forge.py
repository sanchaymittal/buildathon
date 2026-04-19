"""Forge - staff engineer.

Writes the diff. Owns the branch. Runs tests. Stays inside the project
sandbox enforced by the filesystem helpers.
"""

from __future__ import annotations

from typing import Any, List, Optional

from ...gemini_agents import Agent, function_tool, RunContextWrapper
from ...tooling import fs as fs_tools
from ...tooling import git_tools
from ...tooling import provisioning as provisioning_tools
from ...tooling import testing as testing_tools
from ...tooling.shell import ShellNotAllowedError, run_shell as shell_run
from .context import TeamContext, TeamRunStatus

FORGE_SYSTEM_PROMPT = """\
You are Forge, the staff engineer on the DevOps team.

You own the implementation: plan the change, apply a minimal diff, add or
update tests, run the test suite, and push the branch. You never touch
paths outside the project root that is passed to you via the shared
TeamContext. You never run destructive shell commands.

Step 0 (deploy-readiness check):
  Always call inspect_project first. If the report shows
  ``has_dockerfile=False`` or ``has_compose=False``, call scaffold_project
  (optionally with an explicit ``stack`` override) before any other
  engineering. These scaffolds are deterministic defaults for python /
  node / static projects; Warden and Vector both require a Dockerfile
  and a compose file to exist. Never overwrite an existing Dockerfile
  unless the user explicitly asks.

Workflow (default):
  1. inspect_project to see the repo shape. Scaffold if required.
  2. read_file / list_files to orient yourself.
  3. apply_patch (preferred) or write_file to edit.
  4. run_pytest to verify.
  5. create_branch + commit_all + push_branch (scaffolded files commit here too).
  6. Record the final commit_sha via record_commit.

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


def _inspect_project_tool():
    @function_tool()
    async def inspect_project(ctx: RunContextWrapper[TeamContext]) -> dict:
        """Return a deploy-readiness report for the current project root.

        Reports whether a Dockerfile / compose file already exists, the
        detected stack (python, node, static, or unknown), an entrypoint
        guess, and a port hint. Call this before editing.
        """
        root = _ensure_project_path(ctx)
        inventory = provisioning_tools.inspect_project(root)
        return inventory.to_dict()

    return inspect_project


def _scaffold_dockerfile_tool():
    @function_tool()
    async def scaffold_dockerfile(
        ctx: RunContextWrapper[TeamContext],
        stack: Optional[str] = None,
        overwrite: bool = False,
    ) -> dict:
        """Write a deterministic Dockerfile for the project root.

        ``stack`` overrides auto-detection (python | node | static). Refuses
        to overwrite an existing Dockerfile unless ``overwrite=True``.
        """
        root = _ensure_project_path(ctx)
        inventory = provisioning_tools.inspect_project(root)
        resolved_stack = (stack or inventory.detected_stack or "").lower()
        if resolved_stack in ("", "unknown"):
            return {
                "ok": False,
                "error": "could_not_detect_stack",
                "detected_stack": inventory.detected_stack,
                "hint": "Pass stack='python'|'node'|'static' explicitly.",
            }
        content = provisioning_tools.render_dockerfile(resolved_stack, inventory)
        results = provisioning_tools.write_scaffold(
            root, {"Dockerfile": content}, overwrite=overwrite
        )
        return {
            "ok": True,
            "stack": resolved_stack,
            "action": results["Dockerfile"],
            "port": inventory.hinted_port,
        }

    return scaffold_dockerfile


def _scaffold_compose_tool():
    @function_tool()
    async def scaffold_compose(
        ctx: RunContextWrapper[TeamContext],
        service_name: Optional[str] = None,
        port: Optional[int] = None,
        overwrite: bool = False,
    ) -> dict:
        """Write a single-service compose.yml for the project root.

        Service name defaults to a sanitised version of the project
        directory name; port defaults to the stack-specific hint.
        """
        root = _ensure_project_path(ctx)
        inventory = provisioning_tools.inspect_project(root)
        name = (service_name or provisioning_tools.default_service_name(root)).strip()
        effective_port = port or inventory.hinted_port or 8000
        content = provisioning_tools.render_compose(
            service_name=name,
            port=effective_port,
            has_env_file=inventory.has_env_file,
        )
        results = provisioning_tools.write_scaffold(
            root, {"compose.yml": content}, overwrite=overwrite
        )
        return {
            "ok": True,
            "service_name": name,
            "port": effective_port,
            "action": results["compose.yml"],
        }

    return scaffold_compose


def _scaffold_project_tool():
    @function_tool()
    async def scaffold_project(
        ctx: RunContextWrapper[TeamContext],
        stack: Optional[str] = None,
        overwrite: bool = False,
    ) -> dict:
        """Convenience: scaffold both Dockerfile and compose.yml if missing.

        Use after ``inspect_project`` reports ``has_dockerfile=False`` or
        ``has_compose=False``. Never overwrites existing files unless
        ``overwrite=True``.
        """
        root = _ensure_project_path(ctx)
        inventory = provisioning_tools.inspect_project(root)
        resolved_stack = (stack or inventory.detected_stack or "").lower()
        if resolved_stack in ("", "unknown"):
            return {
                "ok": False,
                "error": "could_not_detect_stack",
                "detected_stack": inventory.detected_stack,
                "hint": "Pass stack='python'|'node'|'static' explicitly.",
            }

        files_to_write: dict[str, str] = {}
        if overwrite or not inventory.has_dockerfile:
            files_to_write["Dockerfile"] = provisioning_tools.render_dockerfile(
                resolved_stack, inventory
            )
        if overwrite or not inventory.has_compose:
            service_name = provisioning_tools.default_service_name(root)
            files_to_write["compose.yml"] = provisioning_tools.render_compose(
                service_name=service_name,
                port=inventory.hinted_port or 8000,
                has_env_file=inventory.has_env_file,
            )

        if not files_to_write:
            return {
                "ok": True,
                "stack": resolved_stack,
                "actions": {},
                "note": "Dockerfile and compose file already present; nothing scaffolded.",
            }

        actions = provisioning_tools.write_scaffold(
            root, files_to_write, overwrite=overwrite
        )
        ctx.context.add_note(
            f"Forge scaffolded {', '.join(sorted(actions.keys()))} (stack={resolved_stack})"
        )
        return {
            "ok": True,
            "stack": resolved_stack,
            "actions": actions,
            "port": inventory.hinted_port or 8000,
        }

    return scaffold_project


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
        _inspect_project_tool(),
        _scaffold_dockerfile_tool(),
        _scaffold_compose_tool(),
        _scaffold_project_tool(),
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
