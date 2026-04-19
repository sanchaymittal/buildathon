"""
Docker Tools Module - Provides function tools for Docker operations with OpenAI Agents SDK.

This module implements function tools for deploying repositories, managing containers,
and orchestration, designed to be used with the OpenAI Agents SDK.
"""

import logging
from typing import Dict, List, Any, Optional

from agents import function_tool, RunContextWrapper

from .deploy import DockerDeployService
from .models import (
    ContainerAction,
    ContainerFilter,
    ContainerLogRequest,
    ContainerStatus,
    DeployRequest,
    Deployment,
)
from .service import DockerService
from ..core.context import DevOpsContext
from ..core.credentials import get_credential_manager

logger = logging.getLogger(__name__)


def _get_deploy_service() -> DockerDeployService:
    """Get or create the DockerDeployService instance."""
    return DockerDeployService()


def _get_docker_service() -> DockerService:
    """Get or create the DockerService instance."""
    return DockerService()


@function_tool()
async def deploy_repository(
    ctx: RunContextWrapper[DevOpsContext],
    request: DeployRequest,
) -> Deployment:
    """
    Deploy a GitHub repository to Docker.

    Args:
        ctx: Run context containing DevOpsContext
        request: Deployment request with repository, branch, and configuration

    Returns:
        Deployment object with container info and URL
    """
    logger.info(f"Deploying repository: {request.repository} (branch: {request.branch})")

    cred_manager = get_credential_manager()
    try:
        github_creds = cred_manager.get_github_credentials()
        github_token = github_creds.token
    except Exception:
        github_token = None

    deploy_service = _get_deploy_service()
    deployment = deploy_service.deploy_from_github(request, github_token)

    logger.info(f"Deployed {request.repository} at {deployment.url}")
    return deployment


@function_tool()
async def list_deployments(
    ctx: RunContextWrapper[DevOpsContext],
) -> List[Deployment]:
    """
    List all deployments.

    Args:
        ctx: Run context containing DevOpsContext

    Returns:
        List of Deployment objects
    """
    logger.info("Listing deployments")

    deploy_service = _get_deploy_service()
    return deploy_service.list_deployments()


@function_tool()
async def get_deployment(
    ctx: RunContextWrapper[DevOpsContext],
    deploy_id: str,
) -> Deployment:
    """
    Get deployment details.

    Args:
        ctx: Run context containing DevOpsContext
        deploy_id: Deployment ID

    Returns:
        Deployment object
    """
    logger.info(f"Getting deployment: {deploy_id}")

    deploy_service = _get_deploy_service()
    return deploy_service.get_deployment(deploy_id)


@function_tool()
async def stop_deployment(
    ctx: RunContextWrapper[DevOpsContext],
    deploy_id: str,
) -> Deployment:
    """
    Stop a running deployment.

    Args:
        ctx: Run context containing DevOpsContext
        deploy_id: Deployment ID

    Returns:
        Updated Deployment object
    """
    logger.info(f"Stopping deployment: {deploy_id}")

    deploy_service = _get_deploy_service()
    return deploy_service.stop_deployment(deploy_id)


@function_tool()
async def start_deployment(
    ctx: RunContextWrapper[DevOpsContext],
    deploy_id: str,
) -> Deployment:
    """
    Start a stopped deployment.

    Args:
        ctx: Run context containing DevOpsContext
        deploy_id: Deployment ID

    Returns:
        Updated Deployment object
    """
    logger.info(f"Starting deployment: {deploy_id}")

    deploy_service = _get_deploy_service()
    return deploy_service.start_deployment(deploy_id)


@function_tool()
async def restart_deployment(
    ctx: RunContextWrapper[DevOpsContext],
    deploy_id: str,
) -> Deployment:
    """
    Restart a deployment.

    Args:
        ctx: Run context containing DevOpsContext
        deploy_id: Deployment ID

    Returns:
        Updated Deployment object
    """
    logger.info(f"Restarting deployment: {deploy_id}")

    deploy_service = _get_deploy_service()
    return deploy_service.restart_deployment(deploy_id)


@function_tool()
async def remove_deployment(
    ctx: RunContextWrapper[DevOpsContext],
    deploy_id: str,
) -> Dict[str, Any]:
    """
    Remove a deployment.

    Args:
        ctx: Run context containing DevOpsContext
        deploy_id: Deployment ID

    Returns:
        Result with status
    """
    logger.info(f"Removing deployment: {deploy_id}")

    deploy_service = _get_deploy_service()
    return deploy_service.remove_deployment(deploy_id)


@function_tool()
async def get_deployment_logs(
    ctx: RunContextWrapper[DevOpsContext],
    deploy_id: str,
    tail: int = 100,
) -> str:
    """
    Get deployment logs.

    Args:
        ctx: Run context containing DevOpsContext
        deploy_id: Deployment ID
        tail: Number of log lines to return

    Returns:
        Log string
    """
    logger.info(f"Getting logs for deployment: {deploy_id}")

    deploy_service = _get_deploy_service()
    return deploy_service.get_deployment_logs(deploy_id, tail)


@function_tool()
async def list_containers(
    ctx: RunContextWrapper[DevOpsContext],
    filter: ContainerFilter,
) -> List[Dict[str, Any]]:
    """
    List Docker containers.

    Args:
        ctx: Run context containing DevOpsContext
        filter: Filter parameters

    Returns:
        List of container info dictionaries
    """
    logger.info("Listing containers")

    docker_service = _get_docker_service()
    return docker_service.list_containers(
        all=filter.all,
        label_filter=filter.label_filter,
    )


@function_tool()
async def get_container(
    ctx: RunContextWrapper[DevOpsContext],
    container_id: str,
) -> Dict[str, Any]:
    """
    Get container details.

    Args:
        ctx: Run context containing DevOpsContext
        container_id: Container ID or name

    Returns:
        Container info dictionary
    """
    logger.info(f"Getting container: {container_id}")

    docker_service = _get_docker_service()
    return docker_service.get_container(container_id)


@function_tool()
async def stop_container(
    ctx: RunContextWrapper[DevOpsContext],
    action: ContainerAction,
) -> Dict[str, Any]:
    """
    Stop a container.

    Args:
        ctx: Run context containing DevOpsContext
        action: Container action parameters

    Returns:
        Result dictionary
    """
    logger.info(f"Stopping container: {action.container_id}")

    docker_service = _get_docker_service()
    docker_service.stop_container(action.container_id, action.force)

    return {"status": "stopped", "container_id": action.container_id}


@function_tool()
async def start_container(
    ctx: RunContextWrapper[DevOpsContext],
    container_id: str,
) -> Dict[str, Any]:
    """
    Start a container.

    Args:
        ctx: Run context containing DevOpsContext
        container_id: Container ID or name

    Returns:
        Result dictionary
    """
    logger.info(f"Starting container: {container_id}")

    docker_service = _get_docker_service()
    docker_service.start_container(container_id)

    return {"status": "started", "container_id": container_id}


@function_tool()
async def restart_container(
    ctx: RunContextWrapper[DevOpsContext],
    container_id: str,
) -> Dict[str, Any]:
    """
    Restart a container.

    Args:
        ctx: Run context containing DevOpsContext
        container_id: Container ID or name

    Returns:
        Result dictionary
    """
    logger.info(f"Restarting container: {container_id}")

    docker_service = _get_docker_service()
    docker_service.restart_container(container_id)

    return {"status": "restarted", "container_id": container_id}


@function_tool()
async def remove_container(
    ctx: RunContextWrapper[DevOpsContext],
    action: ContainerAction,
) -> Dict[str, Any]:
    """
    Remove a container.

    Args:
        ctx: Run context containing DevOpsContext
        action: Container action parameters

    Returns:
        Result dictionary
    """
    logger.info(f"Removing container: {action.container_id}")

    docker_service = _get_docker_service()
    docker_service.remove_container(action.container_id, action.force)

    return {"status": "removed", "container_id": action.container_id}


@function_tool()
async def get_container_logs(
    ctx: RunContextWrapper[DevOpsContext],
    request: ContainerLogRequest,
) -> str:
    """
    Get container logs.

    Args:
        ctx: Run context containing DevOpsContext
        request: Log request parameters

    Returns:
        Log string
    """
    logger.info(f"Getting logs for container: {request.container_id}")

    docker_service = _get_docker_service()
    return docker_service.get_logs(
        request.container_id,
        request.tail,
        request.timestamps,
    )


@function_tool()
async def list_images(
    ctx: RunContextWrapper[DevOpsContext],
    dangling: bool = False,
) -> List[Dict[str, Any]]:
    """
    List Docker images.

    Args:
        ctx: Run context containing DevOpsContext
        dangling: Show dangling images

    Returns:
        List of image info dictionaries
    """
    logger.info("Listing images")

    docker_service = _get_docker_service()
    return docker_service.list_images(dangling=dangling)