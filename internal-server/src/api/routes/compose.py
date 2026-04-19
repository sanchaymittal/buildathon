"""
Compose Routes - FastAPI endpoints for local Docker Compose deployments.

The MVP flow: given a local repo path that contains a Dockerfile, a compose
file, and optionally an ``AGENTS.md``, bring the stack up on the host Docker
daemon. No auth, no GitHub token, no registry push.

Endpoints use POST everywhere (even for read-only ``status``/``logs``) because
the request body carries a filesystem path that should not live in a query
string.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from ...docker_svc.base import DockerDaemonError, DockerServiceError
from ...docker_svc.compose_models import (
    ComposeLogsRequest,
    ComposeServiceStatus,
    ComposeTargetRequest,
    DeployLocalRequest,
    DeployLocalResult,
)
from ...docker_svc.compose_service import ComposeDeployError, ComposeDeployService
from ..dependencies import get_compose_service

router = APIRouter(prefix="/compose", tags=["compose"])


def _handle_compose_error(exc: Exception) -> HTTPException:
    if isinstance(exc, DockerDaemonError):
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        )
    if isinstance(exc, ComposeDeployError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    if isinstance(exc, DockerServiceError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
    )


@router.get("/ping")
def ping(
    service: ComposeDeployService = Depends(get_compose_service),
) -> dict:
    """Verify the local Docker daemon is reachable."""
    try:
        service.ping()
        return {"status": "ok"}
    except DockerServiceError as exc:
        raise _handle_compose_error(exc)


@router.post("/up", response_model=DeployLocalResult)
def compose_up(
    request: DeployLocalRequest,
    service: ComposeDeployService = Depends(get_compose_service),
) -> DeployLocalResult:
    """
    Deploy a local project via ``docker compose up -d``.

    A compose-level failure (non-zero ``up`` exit) is returned as a 200 with
    ``status="failed"`` so the caller can inspect the error details. Missing
    files or unreachable daemon produce 4xx/5xx.
    """
    try:
        return service.deploy(request)
    except DockerServiceError as exc:
        raise _handle_compose_error(exc)


@router.post("/down")
def compose_down(
    request: ComposeTargetRequest,
    service: ComposeDeployService = Depends(get_compose_service),
) -> dict:
    """Bring down a local compose project."""
    try:
        output = service.down(request)
        return {"output": output}
    except DockerServiceError as exc:
        raise _handle_compose_error(exc)


@router.post("/status", response_model=List[ComposeServiceStatus])
def compose_status(
    request: ComposeTargetRequest,
    service: ComposeDeployService = Depends(get_compose_service),
) -> List[ComposeServiceStatus]:
    """Return the status of each service in a local compose project."""
    try:
        return service.status(request)
    except DockerServiceError as exc:
        raise _handle_compose_error(exc)


@router.post("/logs")
def compose_logs(
    request: ComposeLogsRequest,
    service: ComposeDeployService = Depends(get_compose_service),
) -> dict:
    """Return recent logs for a local compose project."""
    try:
        logs = service.logs(request)
        return {"logs": logs}
    except DockerServiceError as exc:
        raise _handle_compose_error(exc)
