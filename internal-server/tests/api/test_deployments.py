"""API tests for deployment routes."""

from fastapi.testclient import TestClient
from types import SimpleNamespace

from src.api.app import app
from src.api.dependencies import get_deploy_service


class DummyDeployService:
    def __init__(self):
        self.created = []

    def deploy_from_github(self, request, token):
        deployment = SimpleNamespace(
            id="abc123",
            repository=request.repository,
            branch=request.branch,
            image="image:tag",
            container_id="container-id",
            container_name="container-name",
            host_port=8080,
            container_port=request.container_port,
            url="http://localhost:8080",
            status="running",
            env=request.env,
            labels={}
        )
        self.created.append(deployment)
        return deployment

    def list_deployments(self):
        return [self.created[-1]] if self.created else []

    def get_deployment(self, deploy_id):
        return self.created[-1]

    def get_deployment_logs(self, deploy_id, tail):
        return "logs"

    def stop_deployment(self, deploy_id):
        deployment = self.created[-1]
        deployment.status = "stopped"
        return deployment

    def start_deployment(self, deploy_id):
        deployment = self.created[-1]
        deployment.status = "running"
        return deployment

    def restart_deployment(self, deploy_id):
        return self.created[-1]

    def remove_deployment(self, deploy_id):
        return {"status": "removed", "deployment_id": deploy_id}

    def redeploy(self, deploy_id, token):
        return self.created[-1]


dummy_service = DummyDeployService()


app.dependency_overrides[get_deploy_service] = lambda: dummy_service


client = TestClient(app)


def test_create_deployment():
    response = client.post(
        "/deployments",
        json={"repository": "owner/repo", "branch": "main", "container_port": 8000}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["repository"] == "owner/repo"
    assert data["url"] == "http://localhost:8080"


def test_list_deployments():
    response = client.get("/deployments")
    assert response.status_code == 200
    data = response.json()
    if data:
        assert data[0]["url"] == "http://localhost:8080"


def test_get_logs():
    response = client.get("/deployments/abc123/logs")
    assert response.status_code == 200
    assert response.json()["logs"] == "logs"
