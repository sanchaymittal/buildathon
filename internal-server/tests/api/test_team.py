"""API tests for /team/* routes.

We inject a minimal ``TeamExecutor`` via dependency_overrides so tests
don't touch the real runner / Docker / Gemini.
"""

from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient

from src.agent.team import TeamRunStore
from src.agent.team.context import TeamRunStatus
from src.agent.team.runs import TeamRun
from src.api.app import app
from src.api.routes.team import get_executor, get_store


class FakeExecutor:
    """Fake executor that runs synchronously and records calls."""

    def __init__(self, script=None):
        self.drive_calls = []
        self.resume_calls = []
        self.script = script or (lambda run: None)

    async def drive(self, run: TeamRun):
        self.drive_calls.append(run.run_id)
        self.script(run)

    async def resume(self, run: TeamRun):
        self.resume_calls.append(run.run_id)


@pytest.fixture
def store():
    s = TeamRunStore()
    app.dependency_overrides[get_store] = lambda: s
    yield s
    app.dependency_overrides.pop(get_store, None)


@pytest.fixture
def executor():
    ex = FakeExecutor()
    app.dependency_overrides[get_executor] = lambda: ex
    yield ex
    app.dependency_overrides.pop(get_executor, None)


@pytest.fixture
def client(store, executor):
    return TestClient(app)


def test_create_run_returns_202(client, executor, store):
    response = client.post(
        "/team/runs",
        json={"task": "Deploy sample-app", "project_path": "/tmp/app"},
    )
    assert response.status_code == 202
    body = response.json()
    assert body["task"] == "Deploy sample-app"
    assert body["status"] == "planning"
    # Wait briefly for the background task to flush.
    import time

    time.sleep(0.05)
    assert executor.drive_calls == [body["run_id"]]


def test_list_and_get_run(client, store):
    run = store.create(task="t", project_path="/tmp/p")
    resp = client.get("/team/runs")
    assert resp.status_code == 200
    assert any(r["run_id"] == run.run_id for r in resp.json())

    resp = client.get(f"/team/runs/{run.run_id}")
    assert resp.status_code == 200
    assert resp.json()["task"] == "t"


def test_get_missing_run_404(client):
    resp = client.get("/team/runs/does-not-exist")
    assert resp.status_code == 404


def test_events_returns_created_event(client, store):
    run = store.create(task="t", project_path="/tmp/p")
    resp = client.get(f"/team/runs/{run.run_id}/events")
    assert resp.status_code == 200
    events = resp.json()
    assert any(e["event"] == "team_run_created" for e in events)


def test_approve_resumes_waiting_run(client, store, executor):
    run = store.create(task="t", project_path="/tmp/p")
    run.context.blocking_reason = "scan high"
    run.context.set_status(TeamRunStatus.waiting_for_approval, note="pause")

    resp = client.post(
        f"/team/runs/{run.run_id}/approve",
        json={"gate": "pre_deploy"},
    )
    assert resp.status_code == 200
    # Status flips to deploying once approval lands.
    assert resp.json()["status"] == TeamRunStatus.deploying.value
    # executor.resume is scheduled on the loop; allow it a moment.
    import time

    time.sleep(0.05)
    assert executor.resume_calls == [run.run_id]


def test_approve_not_waiting_returns_409(client, store):
    run = store.create(task="t", project_path="/tmp/p")
    # status stays at planning
    resp = client.post(
        f"/team/runs/{run.run_id}/approve",
        json={"gate": "pre_deploy"},
    )
    assert resp.status_code == 409


def test_reject_marks_run_failed(client, store):
    run = store.create(task="t", project_path="/tmp/p")
    run.context.set_status(TeamRunStatus.waiting_for_approval, note="pause")
    resp = client.post(
        f"/team/runs/{run.run_id}/reject",
        json={"gate": "pre_deploy", "reason": "bad diff"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == TeamRunStatus.failed.value
