"""
Container Routes - FastAPI endpoints for container management.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query

from ...docker_svc import DockerService
from ...docker_svc.base import DockerServiceError
from ..dependencies import get_docker_service

router = APIRouter(prefix="/containers", tags=["containers"])


@router.get("", response_model=List[Dict[str, Any]])
def list_containers(
    all: bool = Query(False, description="Show all containers"),
    label_filter: Optional[str] = Query(None, description="Filter by label (key=value)"),
    docker_service: DockerService = Depends(get_docker_service),
) -> List[Dict[str, Any]]:
    """List containers."""
    labels = None
    if label_filter:
        key, value = label_filter.split("=", 1)
        labels = {key: value}

    return docker_service.list_containers(all=all, label_filter=labels)


@router.get("/{container_id}", response_model=Dict[str, Any])
def get_container(
    container_id: str,
    docker_service: DockerService = Depends(get_docker_service),
) -> Dict[str, Any]:
    """Get container details."""
    try:
        return docker_service.get_container(container_id)
    except DockerServiceError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/{container_id}/logs")
def get_container_logs(
    container_id: str,
    tail: int = Query(100, description="Number of lines"),
    timestamps: bool = Query(False, description="Include timestamps"),
    docker_service: DockerService = Depends(get_docker_service),
) -> dict:
    """Get container logs."""
    try:
        logs = docker_service.get_logs(container_id, tail, timestamps)
        return {"container_id": container_id, "logs": logs}
    except DockerServiceError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/{container_id}/stop")
def stop_container(
    container_id: str,
    force: bool = Query(False, description="Force stop"),
    docker_service: DockerService = Depends(get_docker_service),
) -> dict:
    """Stop a container."""
    try:
        docker_service.stop_container(container_id, force)
        return {"status": "stopped", "container_id": container_id}
    except DockerServiceError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/{container_id}/start")
def start_container(
    container_id: str,
    docker_service: DockerService = Depends(get_docker_service),
) -> dict:
    """Start a container."""
    try:
        docker_service.start_container(container_id)
        return {"status": "started", "container_id": container_id}
    except DockerServiceError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/{container_id}/restart")
def restart_container(
    container_id: str,
    docker_service: DockerService = Depends(get_docker_service),
) -> dict:
    """Restart a container."""
    try:
        docker_service.restart_container(container_id)
        return {"status": "restarted", "container_id": container_id}
    except DockerServiceError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete("/{container_id}")
def remove_container(
    container_id: str,
    force: bool = Query(False, description="Force remove"),
    docker_service: DockerService = Depends(get_docker_service),
) -> dict:
    """Remove a container."""
    try:
        docker_service.remove_container(container_id, force)
        return {"status": "removed", "container_id": container_id}
    except DockerServiceError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))