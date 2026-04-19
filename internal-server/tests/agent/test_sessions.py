"""Tests for AgentSessionStore using a fake runner."""

from __future__ import annotations

import asyncio
from typing import Any, List, Optional

import pytest

from src.agent.sessions import AgentSessionStore
from src.agent.audit import AuditLogger
from src.gemini_agents.runner import RunResult


class FakeRunner:
    def __init__(self):
        self.calls: List[dict] = []

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
            {"agent": agent.name, "prompt": prompt, "history_len": len(history or [])}
        )
        if history is not None:
            history.append({"role": "user", "parts": [{"text": prompt}]})
            history.append({"role": "model", "parts": [{"text": "ack"}]})
        return RunResult(
            output=f"ack: {prompt}",
            tool_calls=[],
            trace_id="t-1",
            model="gemini-2.5-flash",
            finish_reason="stop",
            iterations=0,
        )


@pytest.fixture
def store(tmp_path):
    audit = AuditLogger(path=str(tmp_path / "agent.log"))
    return AgentSessionStore(runner=FakeRunner(), audit_logger=audit)


class TestSpawnAndList:
    def test_spawn_creates_session(self, store):
        session = store.spawn(user_id="alice")
        assert session.session_id
        assert session.context.user_id == "alice"
        assert session.run_count == 0
        assert len(store.list()) == 1

    def test_close_drops_session(self, store):
        session = store.spawn()
        assert store.close(session.session_id) is True
        assert store.list() == []
        assert store.close(session.session_id) is False


class TestRun:
    @pytest.mark.asyncio
    async def test_run_updates_history_and_count(self, store):
        session = store.spawn()
        result = await store.run(session.session_id, "hello")
        assert result.output == "ack: hello"
        assert session.run_count == 1
        assert len(session.history) == 2  # user + model turn

    @pytest.mark.asyncio
    async def test_run_unknown_session_raises(self, store):
        with pytest.raises(KeyError):
            await store.run("missing-session", "hi")

    @pytest.mark.asyncio
    async def test_one_shot_does_not_persist(self, store):
        await store.one_shot("hello", user_id="bob")
        assert store.list() == []

    @pytest.mark.asyncio
    async def test_concurrent_runs_on_same_session_serialize(self, store):
        session = store.spawn()

        async def go(i: int):
            return await store.run(session.session_id, f"prompt-{i}")

        results = await asyncio.gather(*(go(i) for i in range(5)))
        assert len(results) == 5
        assert session.run_count == 5
