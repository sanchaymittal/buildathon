"""Tests for the handoff_tool primitive."""

from __future__ import annotations

from typing import Any, List

import pytest

from src.agent.team.context import TeamContext, TeamRunStatus
from src.agent.team.handoff import HandoffResult, handoff_tool
from src.gemini_agents import Agent
from src.gemini_agents.runner import RunResult, ToolCallRecord


pytestmark = pytest.mark.agent


class FakeRunner:
    def __init__(self, output: str = "done"):
        self.calls: List[dict] = []
        self.output = output

    async def run(
        self,
        agent,
        prompt,
        context=None,
        history=None,
        input_guardrails=None,
        output_guardrails=None,
    ):
        self.calls.append(
            {
                "agent": agent.name,
                "prompt": prompt,
                "context_status": context.status.value,
            }
        )
        return RunResult(
            output=self.output,
            tool_calls=[
                ToolCallRecord(name="noop", arguments={}, result=None, duration_ms=1)
            ],
            trace_id="t-1",
            model="gemini-2.5-pro",
            finish_reason="stop",
            iterations=1,
        )


def _peer_factory():
    return Agent(name="FakePeer", instructions="", tools=[])


@pytest.mark.asyncio
async def test_handoff_tool_forwards_task_spec_and_context():
    fake = FakeRunner(output="forge done")
    tool = handoff_tool(
        name="handoff_to_forge",
        description="ask Forge",
        agent_factory=_peer_factory,
        runner_factory=lambda: fake,
    )

    class Ctx:
        context = TeamContext(run_id="r", task="t", project_path="/tmp")

    ctx = Ctx()
    # The decorated tool exposes on_invoke_tool for the runner; call it
    # directly with kwargs.
    result = await tool.on_invoke_tool(ctx, task_spec="Implement feature X")
    assert isinstance(result, HandoffResult)
    assert result.peer == "FakePeer"
    assert result.summary == "forge done"
    assert fake.calls[0]["agent"] == "FakePeer"
    assert "Implement feature X" in fake.calls[0]["prompt"]


@pytest.mark.asyncio
async def test_handoff_skips_when_waiting_for_approval():
    fake = FakeRunner()
    tool = handoff_tool(
        name="handoff_to_forge",
        description="ask Forge",
        agent_factory=_peer_factory,
        runner_factory=lambda: fake,
    )

    class Ctx:
        context = TeamContext(run_id="r", task="t", project_path="/tmp")

    ctx = Ctx()
    ctx.context.set_status(TeamRunStatus.waiting_for_approval, note="block")

    result = await tool.on_invoke_tool(ctx, task_spec="do thing")
    assert result.finish_reason == "paused"
    assert fake.calls == []
