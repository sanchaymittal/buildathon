"""Tests for Forge's inspect/scaffold tools.

These drive the tool functions directly (they expose ``on_invoke_tool``)
so we can verify deterministic behaviour without any Gemini traffic.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from src.agent.team.context import TeamContext
from src.agent.team.forge import build_forge
from src.gemini_agents import RunContextWrapper


pytestmark = pytest.mark.agent


def _tool(agent, name: str):
    for t in agent.tools:
        if getattr(t, "__name__", "") == name:
            return t
    raise AssertionError(f"Forge has no tool '{name}'")


def _ctx(project_path: str) -> RunContextWrapper[TeamContext]:
    team = TeamContext(
        run_id="run-test",
        task="test",
        project_path=project_path,
        user_id="u",
    )
    return RunContextWrapper(team)


@pytest.mark.asyncio
async def test_inspect_project_reports_missing_scaffold(tmp_path: Path):
    (tmp_path / "requirements.txt").write_text("flask\n")
    (tmp_path / "app.py").write_text("print('hi')\n")

    agent = build_forge(model="test")
    inspect = _tool(agent, "inspect_project")

    report: Any = await inspect.on_invoke_tool(_ctx(str(tmp_path)))

    assert report["detected_stack"] == "python"
    assert report["has_dockerfile"] is False
    assert report["has_compose"] is False
    assert report["entrypoint"] == "app.py"


@pytest.mark.asyncio
async def test_scaffold_project_writes_both_files_on_bare_python_repo(tmp_path: Path):
    (tmp_path / "requirements.txt").write_text("flask\n")
    (tmp_path / "app.py").write_text("print('hi')\n")

    agent = build_forge(model="test")
    scaffold = _tool(agent, "scaffold_project")
    ctx = _ctx(str(tmp_path))

    result: Any = await scaffold.on_invoke_tool(ctx)

    assert result["ok"] is True
    assert result["stack"] == "python"
    assert result["actions"] == {"Dockerfile": "written", "compose.yml": "written"}

    dockerfile = (tmp_path / "Dockerfile").read_text()
    compose = (tmp_path / "compose.yml").read_text()

    assert "FROM python:3.11-slim" in dockerfile
    assert 'CMD ["python", "app.py"]' in dockerfile
    assert "build: ." in compose
    assert '"8000:8000"' in compose

    # Second inspect should now report ready.
    inspect = _tool(agent, "inspect_project")
    report: Any = await inspect.on_invoke_tool(ctx)
    assert report["has_dockerfile"] is True
    assert report["has_compose"] is True

    # Scaffolding note recorded on the team context.
    assert any("scaffolded" in n.lower() for n in ctx.context.notes)


@pytest.mark.asyncio
async def test_scaffold_project_skips_existing_without_overwrite(tmp_path: Path):
    (tmp_path / "requirements.txt").write_text("flask\n")
    (tmp_path / "app.py").write_text("print('hi')\n")
    (tmp_path / "Dockerfile").write_text("FROM user-owned\n")

    agent = build_forge(model="test")
    scaffold = _tool(agent, "scaffold_project")
    ctx = _ctx(str(tmp_path))

    result: Any = await scaffold.on_invoke_tool(ctx)

    # Dockerfile already exists, so it should be absent from actions; only
    # compose.yml is written.
    assert result["ok"] is True
    assert result["actions"] == {"compose.yml": "written"}
    # User's Dockerfile untouched.
    assert (tmp_path / "Dockerfile").read_text() == "FROM user-owned\n"


@pytest.mark.asyncio
async def test_scaffold_project_overwrites_when_requested(tmp_path: Path):
    (tmp_path / "requirements.txt").write_text("flask\n")
    (tmp_path / "app.py").write_text("")
    (tmp_path / "Dockerfile").write_text("FROM user-owned\n")
    (tmp_path / "compose.yml").write_text("services: {}\n")

    agent = build_forge(model="test")
    scaffold = _tool(agent, "scaffold_project")
    ctx = _ctx(str(tmp_path))

    result: Any = await scaffold.on_invoke_tool(ctx, overwrite=True)

    assert result["actions"] == {
        "Dockerfile": "written",
        "compose.yml": "written",
    }
    assert "FROM python:3.11-slim" in (tmp_path / "Dockerfile").read_text()


@pytest.mark.asyncio
async def test_scaffold_project_refuses_unknown_stack(tmp_path: Path):
    # Empty repo - no sentinel files.
    (tmp_path / "README.md").write_text("# hi\n")

    agent = build_forge(model="test")
    scaffold = _tool(agent, "scaffold_project")

    result: Any = await scaffold.on_invoke_tool(_ctx(str(tmp_path)))

    assert result["ok"] is False
    assert result["error"] == "could_not_detect_stack"
    assert (tmp_path / "Dockerfile").exists() is False


@pytest.mark.asyncio
async def test_scaffold_project_accepts_explicit_stack(tmp_path: Path):
    (tmp_path / "README.md").write_text("# hi\n")

    agent = build_forge(model="test")
    scaffold = _tool(agent, "scaffold_project")

    result: Any = await scaffold.on_invoke_tool(_ctx(str(tmp_path)), stack="python")

    assert result["ok"] is True
    assert "FROM python:3.11-slim" in (tmp_path / "Dockerfile").read_text()


@pytest.mark.asyncio
async def test_scaffold_dockerfile_only(tmp_path: Path):
    (tmp_path / "package.json").write_text('{"name": "app", "main": "server.js"}')

    agent = build_forge(model="test")
    scaffold_df = _tool(agent, "scaffold_dockerfile")

    result: Any = await scaffold_df.on_invoke_tool(_ctx(str(tmp_path)))

    assert result["ok"] is True
    assert result["stack"] == "node"
    assert (tmp_path / "Dockerfile").exists()
    assert (tmp_path / "compose.yml").exists() is False


@pytest.mark.asyncio
async def test_scaffold_compose_with_explicit_port(tmp_path: Path):
    (tmp_path / "requirements.txt").write_text("")

    agent = build_forge(model="test")
    scaffold_compose = _tool(agent, "scaffold_compose")

    result: Any = await scaffold_compose.on_invoke_tool(
        _ctx(str(tmp_path)),
        service_name="my-service",
        port=9999,
    )

    assert result["service_name"] == "my-service"
    assert result["port"] == 9999
    compose = (tmp_path / "compose.yml").read_text()
    assert "my-service:" in compose
    assert '"9999:9999"' in compose
