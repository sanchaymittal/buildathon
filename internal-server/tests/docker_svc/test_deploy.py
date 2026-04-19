"""Tests for the legacy DockerDeployService orchestrator (docker-py flow)."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

# The legacy flow depends on the optional ``docker`` (docker-py) package.
# Skip the whole module cleanly when it's not installed so the MVP compose
# tests remain the source of truth.
docker = pytest.importorskip("docker")

from src.docker_svc.deploy import DockerDeployService  # noqa: E402
from src.docker_svc.models import DeployRequest  # noqa: E402


@pytest.fixture
def mock_docker_service():
    service = MagicMock()
    service.build_image.return_value = {"id": "image-id"}
    service._allocate_free_port.return_value = 49152
    container = SimpleNamespace(id="container-id", name="container-name")
    service.run_container.return_value = container
    service.get_logs.return_value = "log line"
    return service


def test_deploy_from_github(tmp_path, mocker, mock_docker_service):
    deploy_service = DockerDeployService(
        docker_service=mock_docker_service, workspace_dir=str(tmp_path)
    )

    mocker.patch.object(deploy_service, "_clone_repository", autospec=True)
    mocker.patch.object(deploy_service, "_check_dockerfile", return_value=True)

    request = DeployRequest(repository="owner/repo", branch="main", container_port=8080)
    result = deploy_service.deploy_from_github(request, github_token="token")

    assert result.repository == "owner/repo"
    assert result.container_port == 8080
    assert result.host_port == 49152
    assert result.url == "http://localhost:49152"
    assert result.status == "running"

    assert deploy_service.get_deployment(result.id).container_id == "container-id"


def test_stop_and_remove_deployment(mock_docker_service, tmp_path, mocker):
    deploy_service = DockerDeployService(
        docker_service=mock_docker_service, workspace_dir=str(tmp_path)
    )
    mocker.patch.object(deploy_service, "_clone_repository", autospec=True)
    mocker.patch.object(deploy_service, "_check_dockerfile", return_value=True)

    request = DeployRequest(repository="owner/repo", branch="main", container_port=80)
    deployment = deploy_service.deploy_from_github(request, github_token=None)

    stopped = deploy_service.stop_deployment(deployment.id)
    assert stopped.status == "stopped"
    mock_docker_service.stop_container.assert_called_once()

    deploy_service.remove_deployment(deployment.id)
    mock_docker_service.remove_container.assert_called_once()
    mock_docker_service.remove_image.assert_called_once()


def test_get_deployment_logs(mock_docker_service, tmp_path, mocker):
    deploy_service = DockerDeployService(
        docker_service=mock_docker_service, workspace_dir=str(tmp_path)
    )
    mocker.patch.object(deploy_service, "_clone_repository", autospec=True)
    mocker.patch.object(deploy_service, "_check_dockerfile", return_value=True)

    request = DeployRequest(repository="owner/repo", branch="main", container_port=80)
    deployment = deploy_service.deploy_from_github(request, github_token=None)

    logs = deploy_service.get_deployment_logs(deployment.id, tail=50)
    assert logs == "log line"
    mock_docker_service.get_logs.assert_called_once_with(
        deployment.container_id, 50, False
    )
