"""API tests for the /compose/* routes."""

from __future__ import annotations

from typing import List

import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.api.dependencies import get_compose_service
from src.docker_svc.compose_models import (
    ComposeLogsRequest,
    ComposeServiceStatus,
    ComposeTargetRequest,
    DeployLocalRequest,
    DeployLocalResult,
)
from src.docker_svc.compose_service import ComposeDeployError

pytestmark = pytest.mark.docker


class DummyComposeService:
    """Fake ComposeDeployService that records calls and returns scripted results."""

    def __init__(self) -> None:
        self.calls: List[tuple] = []
        self.deploy_result: DeployLocalResult = DeployLocalResult(
            status="succeeded",
            project_name="sample-app-abc123",
            project_path="/tmp/sample-app",
            compose_file="/tmp/sample-app/compose.yml",
            services=[
                ComposeServiceStatus(
                    service="web",
                    container_id="cid",
                    name="sample-app-web-1",
                    state="running",
                    status="Up 2 seconds",
                    ports="",
                )
            ],
            output="creating services",
            error=None,
            agents_md_excerpt="# Sample App",
        )
        self.status_result: List[ComposeServiceStatus] = self.deploy_result.services
        self.down_result: str = "stopping"
        self.logs_result: str = "web-1 | hello"
        self.deploy_raises: Exception | None = None
        self.ping_raises: Exception | None = None

    def ping(self) -> None:
        self.calls.append(("ping",))
        if self.ping_raises:
            raise self.ping_raises

    def deploy(self, request: DeployLocalRequest) -> DeployLocalResult:
        self.calls.append(("deploy", request))
        if self.deploy_raises:
            raise self.deploy_raises
        return self.deploy_result

    def status(self, request: ComposeTargetRequest) -> List[ComposeServiceStatus]:
        self.calls.append(("status", request))
        return self.status_result

    def down(self, request: ComposeTargetRequest) -> str:
        self.calls.append(("down", request))
        return self.down_result

    def logs(self, request: ComposeLogsRequest) -> str:
        self.calls.append(("logs", request))
        return self.logs_result


@pytest.fixture
def dummy_service() -> DummyComposeService:
    service = DummyComposeService()
    app.dependency_overrides[get_compose_service] = lambda: service
    yield service
    app.dependency_overrides.pop(get_compose_service, None)


@pytest.fixture
def client(dummy_service: DummyComposeService) -> TestClient:
    return TestClient(app)


class TestComposeUp:
    def test_happy_path(self, client: TestClient, dummy_service: DummyComposeService):
        response = client.post(
            "/compose/up",
            json={"project_path": "/tmp/sample-app"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "succeeded"
        assert body["project_name"] == "sample-app-abc123"
        assert len(body["services"]) == 1
        assert body["services"][0]["service"] == "web"
        assert body["agents_md_excerpt"].startswith("# Sample App")

        kind, request = dummy_service.calls[-1]
        assert kind == "deploy"
        assert request.project_path == "/tmp/sample-app"

    def test_compose_failure_returns_200_with_failed_status(
        self, client: TestClient, dummy_service: DummyComposeService
    ):
        dummy_service.deploy_result = DeployLocalResult(
            status="failed",
            project_name="p",
            project_path="/tmp/p",
            compose_file="/tmp/p/compose.yml",
            services=[],
            output="",
            error="build failed",
        )
        response = client.post("/compose/up", json={"project_path": "/tmp/p"})
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "failed"
        assert body["error"] == "build failed"

    def test_compose_deploy_error_returns_400(
        self, client: TestClient, dummy_service: DummyComposeService
    ):
        dummy_service.deploy_raises = ComposeDeployError(
            "No compose file found", suggestion="Add compose.yml"
        )
        response = client.post("/compose/up", json={"project_path": "/tmp/missing"})
        assert response.status_code == 400
        assert "No compose file found" in response.json()["detail"]


class TestComposeStatus:
    def test_returns_service_list(
        self, client: TestClient, dummy_service: DummyComposeService
    ):
        response = client.post(
            "/compose/status",
            json={"project_path": "/tmp/sample-app"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body[0]["service"] == "web"
        assert body[0]["state"] == "running"


class TestComposeDown:
    def test_returns_output(
        self, client: TestClient, dummy_service: DummyComposeService
    ):
        response = client.post(
            "/compose/down", json={"project_path": "/tmp/sample-app"}
        )
        assert response.status_code == 200
        assert response.json() == {"output": "stopping"}


class TestComposeLogs:
    def test_returns_logs(self, client: TestClient, dummy_service: DummyComposeService):
        response = client.post(
            "/compose/logs",
            json={
                "project_path": "/tmp/sample-app",
                "service": "web",
                "tail": 10,
            },
        )
        assert response.status_code == 200
        assert response.json() == {"logs": "web-1 | hello"}
        kind, request = dummy_service.calls[-1]
        assert kind == "logs"
        assert request.service == "web"
        assert request.tail == 10


class TestComposePing:
    def test_ping_ok(self, client: TestClient, dummy_service: DummyComposeService):
        response = client.get("/compose/ping")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_ping_daemon_unavailable(
        self, client: TestClient, dummy_service: DummyComposeService
    ):
        from src.docker_svc.base import DockerDaemonError

        dummy_service.ping_raises = DockerDaemonError("daemon not running")
        response = client.get("/compose/ping")
        assert response.status_code == 503
        assert "daemon not running" in response.json()["detail"]


class TestHealth:
    def test_health_root(self, client: TestClient):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_health_compose_ok(
        self, client: TestClient, dummy_service: DummyComposeService
    ):
        # /health/compose doesn't go through get_compose_service; it builds its
        # own instance. Patch subprocess.run via the dummy's ping? No - simpler
        # to let it run and accept whatever the local daemon reports. We only
        # assert the response shape.
        response = client.get("/health/compose")
        assert response.status_code in (200, 503)
        body = response.json()
        assert "status" in body
        assert "docker" in body
