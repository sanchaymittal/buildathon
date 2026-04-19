"""Tests for ComposeDeployService (local docker compose MVP flow)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.docker_svc.compose_models import (
    ComposeLogsRequest,
    ComposeTargetRequest,
    DeployLocalRequest,
)
from src.docker_svc.compose_service import (
    ComposeDeployError,
    ComposeDeployService,
)


pytestmark = pytest.mark.docker


@pytest.fixture
def service() -> ComposeDeployService:
    return ComposeDeployService(skip_verification=True)


class TestResolution:
    def test_default_project_name_is_stable(self, service, tmp_project):
        name1 = service._default_project_name(tmp_project)
        name2 = service._default_project_name(tmp_project)
        assert name1 == name2
        assert name1.endswith(tuple("0123456789abcdef"))
        assert "-" in name1

    def test_auto_detects_compose_yml(self, service, tmp_project):
        resolved = service._resolve_compose_file(tmp_project, None)
        assert resolved.name == "compose.yml"

    def test_auto_detects_docker_compose_yml(self, service, tmp_project_docker_compose):
        resolved = service._resolve_compose_file(tmp_project_docker_compose, None)
        assert resolved.name == "docker-compose.yml"

    def test_missing_compose_raises(self, service, tmp_path):
        (tmp_path / "Dockerfile").write_text("FROM scratch\n")
        with pytest.raises(ComposeDeployError) as exc:
            service._resolve_compose_file(tmp_path, None)
        assert "No compose file found" in str(exc.value)

    def test_missing_project_path_raises(self, service, tmp_path):
        with pytest.raises(ComposeDeployError):
            service._resolve_project_path(str(tmp_path / "does-not-exist"))


class TestDeployHappyPath:
    def test_deploy_succeeds_and_returns_services(self, service, tmp_project, mock_run):
        ps_payload = json.dumps(
            [
                {
                    "Service": "web",
                    "ID": "abc123",
                    "Name": "sample-app-web-1",
                    "State": "running",
                    "Status": "Up 2 seconds",
                    "Publishers": [{"TargetPort": 80, "PublishedPort": 8080}],
                }
            ]
        )
        mock_run.route("up", mock_run.cp(stdout="creating services"))
        mock_run.route("ps", mock_run.cp(stdout=ps_payload))

        result = service.deploy(DeployLocalRequest(project_path=str(tmp_project)))

        assert result.status == "succeeded"
        assert result.project_name.startswith(tmp_project.name.lower())
        assert result.compose_file.endswith("compose.yml")
        assert len(result.services) == 1
        assert result.services[0].service == "web"
        assert result.services[0].state == "running"
        assert result.agents_md_excerpt and "sample" in result.agents_md_excerpt.lower()

    def test_up_command_shape(self, service, tmp_project, mock_run):
        mock_run.route("up", mock_run.cp())
        mock_run.route("ps", mock_run.cp(stdout="[]"))
        service.deploy(DeployLocalRequest(project_path=str(tmp_project)))

        up_call = next(c for c in mock_run.calls if "up" in c)
        assert up_call[:2] == ["docker", "compose"]
        assert "-f" in up_call
        assert "-p" in up_call
        assert "-d" in up_call
        assert "--build" in up_call
        assert "--remove-orphans" in up_call

    def test_no_build_flag_respected(self, service, tmp_project, mock_run):
        mock_run.route("up", mock_run.cp())
        mock_run.route("ps", mock_run.cp(stdout="[]"))
        service.deploy(DeployLocalRequest(project_path=str(tmp_project), build=False))

        up_call = next(c for c in mock_run.calls if "up" in c)
        assert "--build" not in up_call

    def test_pull_flag_respected(self, service, tmp_project, mock_run):
        mock_run.route("up", mock_run.cp())
        mock_run.route("ps", mock_run.cp(stdout="[]"))
        service.deploy(DeployLocalRequest(project_path=str(tmp_project), pull=True))

        up_call = next(c for c in mock_run.calls if "up" in c)
        assert "--pull" in up_call


class TestDeployFailureModes:
    def test_up_failure_returns_failed_result(self, service, tmp_project, mock_run):
        mock_run.route(
            "up",
            mock_run.cp(returncode=1, stderr="build failed: invalid FROM"),
        )

        result = service.deploy(DeployLocalRequest(project_path=str(tmp_project)))

        assert result.status == "failed"
        assert result.error and "build failed" in result.error
        assert result.services == []

    def test_missing_compose_raises(self, service, tmp_path, mock_run):
        (tmp_path / "Dockerfile").write_text("FROM scratch\n")
        with pytest.raises(ComposeDeployError):
            service.deploy(DeployLocalRequest(project_path=str(tmp_path)))

    def test_missing_env_file_raises(self, service, tmp_project, mock_run):
        with pytest.raises(ComposeDeployError) as exc:
            service.deploy(
                DeployLocalRequest(project_path=str(tmp_project), env_file=".env")
            )
        assert "env file not found" in str(exc.value)


class TestStatusDownLogs:
    def test_status_parses_newline_delimited_json(self, service, tmp_project, mock_run):
        ndjson = "\n".join(
            json.dumps({"Service": svc, "State": "running"}) for svc in ("web", "db")
        )
        mock_run.route("ps", mock_run.cp(stdout=ndjson))

        statuses = service.status(ComposeTargetRequest(project_path=str(tmp_project)))
        assert [s.service for s in statuses] == ["web", "db"]

    def test_down_issues_expected_command(self, service, tmp_project, mock_run):
        mock_run.route("down", mock_run.cp(stdout="stopping"))
        output = service.down(ComposeTargetRequest(project_path=str(tmp_project)))
        assert "stopping" in output
        down_call = next(c for c in mock_run.calls if "down" in c)
        assert "--remove-orphans" in down_call

    def test_down_failure_raises(self, service, tmp_project, mock_run):
        mock_run.route("down", mock_run.cp(returncode=2, stderr="no such project"))
        with pytest.raises(ComposeDeployError):
            service.down(ComposeTargetRequest(project_path=str(tmp_project)))

    def test_logs_returns_stdout(self, service, tmp_project, mock_run):
        mock_run.route("logs", mock_run.cp(stdout="web-1 | hello world"))
        output = service.logs(
            ComposeLogsRequest(project_path=str(tmp_project), service="web", tail=10)
        )
        assert "hello world" in output
        logs_call = next(c for c in mock_run.calls if "logs" in c)
        assert "--tail" in logs_call
        assert "10" in logs_call
        assert "web" in logs_call


class TestPing:
    def test_ping_raises_when_docker_missing(self, mocker):
        mocker.patch(
            "src.docker_svc.compose_service.subprocess.run",
            side_effect=FileNotFoundError(),
        )
        with pytest.raises(Exception) as exc:
            ComposeDeployService(skip_verification=False)
        assert "docker" in str(exc.value).lower()

    def test_ping_raises_on_nonzero_exit(self, mocker):
        import subprocess as sp

        mocker.patch(
            "src.docker_svc.compose_service.subprocess.run",
            return_value=sp.CompletedProcess(
                args=["docker", "version"],
                returncode=1,
                stdout="",
                stderr="not running",
            ),
        )
        with pytest.raises(Exception) as exc:
            ComposeDeployService(skip_verification=False)
        assert "not reachable" in str(exc.value).lower()
