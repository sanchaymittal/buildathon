"""API tests for /agent/* routes."""

from __future__ import annotations

from typing import Any, List

import pytest
from fastapi.testclient import TestClient

from src.agent.audit import AuditLogger
from src.agent.sessions import AgentSessionStore
from src.api.app import app
from src.api.routes.agent import get_store
from src.gemini_agents.runner import RunResult, ToolCallRecord


class FakeRunner:
    def __init__(self) -> None:
        self.calls: List[dict] = []
        self.raise_next: Exception | None = None
        self.next_result: RunResult | None = None

    async def run(
        self,
        agent,
        prompt,
        context=None,
        history=None,
        input_guardrails=None,
        output_guardrails=None,
    ):
        self.calls.append({"prompt": prompt, "agent": agent.name})
        if self.raise_next:
            exc, self.raise_next = self.raise_next, None
            raise exc
        if self.next_result is not None:
            return self.next_result
        if history is not None:
            history.append({"role": "user", "parts": [{"text": prompt}]})
        return RunResult(
            output=f"ack: {prompt}",
            tool_calls=[
                ToolCallRecord(
                    name="deploy_local_project",
                    arguments={"project_path": "/tmp/app"},
                    result={"status": "succeeded"},
                    duration_ms=5,
                )
            ],
            trace_id="trace-1",
            model="gemini-2.5-flash",
            finish_reason="stop",
            iterations=1,
        )


@pytest.fixture
def fake_runner():
    return FakeRunner()


@pytest.fixture
def store(tmp_path, fake_runner):
    audit = AuditLogger(path=str(tmp_path / "agent.log"))
    s = AgentSessionStore(runner=fake_runner, audit_logger=audit)
    app.dependency_overrides[get_store] = lambda: s
    yield s
    app.dependency_overrides.pop(get_store, None)


@pytest.fixture
def client(store):
    return TestClient(app)


class TestAgentRun:
    def test_one_shot_returns_output_and_tool_calls(self, client, fake_runner):
        response = client.post("/agent/run", json={"prompt": "deploy it"})
        assert response.status_code == 200
        body = response.json()
        assert body["output"] == "ack: deploy it"
        assert body["trace_id"] == "trace-1"
        assert body["iterations"] == 1
        assert body["tool_calls"][0]["name"] == "deploy_local_project"
        assert fake_runner.calls[0]["prompt"] == "deploy it"

    def test_one_shot_guardrail_returns_400(self, client, fake_runner):
        from src.gemini_agents.runner import AgentGuardrailError

        fake_runner.raise_next = AgentGuardrailError("blocked by guardrail")
        response = client.post("/agent/run", json={"prompt": "rm -rf /"})
        assert response.status_code == 400
        assert "blocked" in response.json()["detail"]

    def test_one_shot_credential_error_returns_503(self, client, fake_runner):
        from src.core.credentials import CredentialError

        fake_runner.raise_next = CredentialError("no key")
        response = client.post("/agent/run", json={"prompt": "hi"})
        assert response.status_code == 503


class TestAgentSessions:
    def test_create_list_get_close(self, client, store):
        # create
        resp = client.post("/agent/sessions", json={"user_id": "alice"})
        assert resp.status_code == 201
        sid = resp.json()["session_id"]

        # list
        resp = client.get("/agent/sessions")
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["session_id"] == sid

        # get
        resp = client.get(f"/agent/sessions/{sid}")
        assert resp.status_code == 200
        assert resp.json()["user_id"] == "alice"

        # close
        resp = client.delete(f"/agent/sessions/{sid}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "closed"

        # gone
        resp = client.get(f"/agent/sessions/{sid}")
        assert resp.status_code == 404

    def test_session_run(self, client, store, fake_runner):
        resp = client.post("/agent/sessions", json={})
        sid = resp.json()["session_id"]

        resp = client.post(f"/agent/sessions/{sid}/run", json={"prompt": "status?"})
        assert resp.status_code == 200
        assert resp.json()["output"] == "ack: status?"
        # Session turns is updated.
        resp = client.get(f"/agent/sessions/{sid}")
        assert resp.json()["turns"] == 1

    def test_run_missing_session_returns_404(self, client):
        resp = client.post("/agent/sessions/nope/run", json={"prompt": "hi"})
        assert resp.status_code == 404
