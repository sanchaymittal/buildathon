"""
Deployment Routes - FastAPI endpoints for deployments.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status

from ...docker_svc import DockerDeployService, DeployRequest, Deployment
from ...docker_svc.base import DockerServiceError
from ...core.credentials import get_credential_manager
from ..dependencies import get_deploy_service

router = APIRouter(prefix="/deployments", tags=["deployments"])


def _get_github_token() -> Optional[str]:
    """Get GitHub token if available."""
    try:
        cred_manager = get_credential_manager()
        creds = cred_manager.get_github_credentials()
        return creds.token
    except Exception:
        return None


@router.post("", response_model=Deployment, status_code=status.HTTP_201_CREATED)
def create_deployment(
    request: DeployRequest,
    deploy_service: DockerDeployService = Depends(get_deploy_service),
    github_token: Optional[str] = Depends(_get_github_token),
) -> Deployment:
    """Deploy a GitHub repository to Docker."""
    try:
        deployment = deploy_service.deploy_from_github(request, github_token)
        return deployment
    except DockerServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("", response_model=List[Deployment])
def list_deployments(
    deploy_service: DockerDeployService = Depends(get_deploy_service),
) -> List[Deployment]:
    """List all deployments."""
    return deploy_service.list_deployments()


@router.get("/{deploy_id}", response_model=Deployment)
def get_deployment(
    deploy_id: str,
    deploy_service: DockerDeployService = Depends(get_deploy_service),
) -> Deployment:
    """Get deployment details."""
    try:
        return deploy_service.get_deployment(deploy_id)
    except DockerServiceError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/{deploy_id}/logs")
def get_deployment_logs(
    deploy_id: str,
    tail: int = 100,
    deploy_service: DockerDeployService = Depends(get_deploy_service),
) -> dict:
    """Get deployment logs."""
    try:
        logs = deploy_service.get_deployment_logs(deploy_id, tail)
        return {"deploy_id": deploy_id, "logs": logs}
    except DockerServiceError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/{deploy_id}/stop", response_model=Deployment)
def stop_deployment(
    deploy_id: str,
    deploy_service: DockerDeployService = Depends(get_deploy_service),
) -> Deployment:
    """Stop a deployment."""
    try:
        return deploy_service.stop_deployment(deploy_id)
    except DockerServiceError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/{deploy_id}/start", response_model=Deployment)
def start_deployment(
    deploy_id: str,
    deploy_service: DockerDeployService = Depends(get_deploy_service),
) -> Deployment:
    """Start a stopped deployment."""
    try:
        return deploy_service.start_deployment(deploy_id)
    except DockerServiceError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/{deploy_id}/restart", response_model=Deployment)
def restart_deployment(
    deploy_id: str,
    deploy_service: DockerDeployService = Depends(get_deploy_service),
) -> Deployment:
    """Restart a deployment."""
    try:
        return deploy_service.restart_deployment(deploy_id)
    except DockerServiceError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete("/{deploy_id}")
def remove_deployment(
    deploy_id: str,
    deploy_service: DockerDeployService = Depends(get_deploy_service),
) -> dict:
    """Remove a deployment."""
    try:
        result = deploy_service.remove_deployment(deploy_id)
        return result
    except DockerServiceError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/{deploy_id}/redeploy", response_model=Deployment)
def redeploy(
    deploy_id: str,
    deploy_service: DockerDeployService = Depends(get_deploy_service),
    github_token: Optional[str] = Depends(_get_github_token),
) -> Deployment:
    """Redeploy a repository."""
    try:
        return deploy_service.redeploy(deploy_id, github_token)
    except DockerServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))