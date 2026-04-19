"""Blue/green rollout helper tests."""

from __future__ import annotations

import subprocess

import pytest

from src.docker_svc.compose_service import ComposeDeployService
from src.tooling import rollout


def _cp(stdout: str = "", stderr: str = "", rc: int = 0) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(
        args=[], returncode=rc, stdout=stdout, stderr=stderr
    )


def test_project_name_includes_color(tmp_path):
    base = rollout.project_base(str(tmp_path))
    assert rollout.project_name_for(str(tmp_path), "blue") == f"{base}-blue"
    assert rollout.project_name_for(str(tmp_path), "green") == f"{base}-green"


def test_deploy_candidate_uses_colored_project_name(tmp_path, mocker):
    (tmp_path / "Dockerfile").write_text("FROM python:3.12-slim\n")
    (tmp_path / "compose.yml").write_text("services:\n  web:\n    build: .\n")

    captured = []

    def _run(cmd, *args, **kwargs):
        captured.append(list(cmd))
        if "ps" in cmd:
            return _cp(stdout="[]")
        return _cp()

    mocker.patch("src.docker_svc.compose_service.subprocess.run", side_effect=_run)

    service = ComposeDeployService(skip_verification=True)
    result = rollout.deploy_candidate(
        service, project_path=str(tmp_path), color="green"
    )
    assert result.status == "succeeded"
    up_cmd = next(c for c in captured if "up" in c)
    name = rollout.project_name_for(str(tmp_path), "green")
    assert name in up_cmd
