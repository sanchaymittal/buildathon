"""Shared fixtures for ComposeDeployService tests."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Callable, List

import pytest


DOCKERFILE_STUB = """\
FROM python:3.12-slim
CMD [\"python\", \"-c\", \"print('hello')\"]
"""

COMPOSE_STUB = """\
services:
  web:
    build: .
    ports:
      - "8080:80"
"""

AGENTS_MD_STUB = """\
# Sample App

This is a sample hackathon project. The agent should deploy it on the local
Docker daemon.

- service: web
- port: 8080
- env: API_KEY
"""


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """Create a temp dir with Dockerfile, compose.yml, and AGENTS.md."""
    (tmp_path / "Dockerfile").write_text(DOCKERFILE_STUB, encoding="utf-8")
    (tmp_path / "compose.yml").write_text(COMPOSE_STUB, encoding="utf-8")
    (tmp_path / "AGENTS.md").write_text(AGENTS_MD_STUB, encoding="utf-8")
    return tmp_path


@pytest.fixture
def tmp_project_docker_compose(tmp_path: Path) -> Path:
    """Temp dir using the legacy 'docker-compose.yml' filename."""
    (tmp_path / "Dockerfile").write_text(DOCKERFILE_STUB, encoding="utf-8")
    (tmp_path / "docker-compose.yml").write_text(COMPOSE_STUB, encoding="utf-8")
    return tmp_path


def _cp(
    returncode: int = 0, stdout: str = "", stderr: str = ""
) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(
        args=["docker", "compose"], returncode=returncode, stdout=stdout, stderr=stderr
    )


@pytest.fixture
def mock_run(mocker):
    """
    Patch ``subprocess.run`` inside compose_service with a router.

    Usage::

        def test_something(mock_run):
            mock_run.route("ping", cp(stdout="24.0.0"))
            mock_run.route("up", cp(stdout="creating..."))
            mock_run.route("ps", cp(stdout='[{"Service": "web", "State": "running"}]'))
    """

    calls: List[List[str]] = []
    routes: List[tuple] = []  # (matcher, CompletedProcess)

    def run_side_effect(cmd, **kwargs):
        calls.append(list(cmd))
        for matcher, cp in routes:
            if matcher(cmd):
                # Preserve the actual args so assertions on the command work.
                return subprocess.CompletedProcess(
                    args=list(cmd),
                    returncode=cp.returncode,
                    stdout=cp.stdout,
                    stderr=cp.stderr,
                )
        # Default: successful empty run.
        return subprocess.CompletedProcess(
            args=list(cmd), returncode=0, stdout="", stderr=""
        )

    patched = mocker.patch(
        "src.docker_svc.compose_service.subprocess.run",
        side_effect=run_side_effect,
    )

    def _match_compose_subcmd(sub: str) -> Callable[[List[str]], bool]:
        def _matcher(cmd: List[str]) -> bool:
            if cmd[:2] != ["docker", "compose"]:
                return False
            return sub in cmd

        return _matcher

    def _match_ping() -> Callable[[List[str]], bool]:
        def _matcher(cmd: List[str]) -> bool:
            return cmd[:2] == ["docker", "version"]

        return _matcher

    def route(key: str, cp: subprocess.CompletedProcess) -> None:
        if key == "ping":
            routes.append((_match_ping(), cp))
        else:
            routes.append((_match_compose_subcmd(key), cp))

    helper = type(
        "MockRun",
        (),
        {
            "calls": calls,
            "route": staticmethod(route),
            "cp": staticmethod(_cp),
            "patched": patched,
        },
    )
    return helper
