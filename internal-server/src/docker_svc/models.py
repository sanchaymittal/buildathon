"""
Docker Models Module - Provides data models for Docker operations.

This module defines Pydantic models for Docker deployment requests,
container representations, and deployment tracking.
"""

import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field


class DeployRequest(BaseModel):
    """Request model for deploying a repository to Docker."""
    repository: str = Field(
        description="GitHub repository in format 'owner/repo' or full URL"
    )

    branch: str = Field(
        default="main",
        description="Git branch to deploy"
    )

    container_port: int = Field(
        default=80,
        description="Port the application listens on inside the container"
    )

    env: Dict[str, str] = Field(
        default_factory=dict,
        description="Environment variables to set in the container"
    )

    build_args: Dict[str, str] = Field(
        default_factory=dict,
        description="Build arguments for Docker build"
    )

    name: Optional[str] = Field(
        default=None,
        description="Optional name for the deployment (auto-derived from repo if not provided)"
    )


class DeployUserRequest(BaseModel):
    """Minimal request model for user-scoped deployments."""

    repository: str = Field(
        description="GitHub repository in format 'owner/repo' or full URL"
    )

    user_id: str = Field(
        description="Unique user identifier for tenant segregation"
    )


class ContainerStatus(BaseModel):
    """Container status information."""
    container_id: str
    name: str
    image: str
    status: str
    state: str
    created: str
    ports: Dict[str, Any] = {}
    labels: Dict[str, str] = {}


class Deployment(BaseModel):
    """Model representing a Docker deployment."""
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique deployment identifier"
    )

    user_id: Optional[str] = Field(
        default=None,
        description="User identifier associated with the deployment"
    )

    repository: str = Field(
        description="GitHub repository that was deployed"
    )

    branch: str = Field(
        default="main",
        description="Git branch that was deployed"
    )

    image: str = Field(
        description="Docker image tag that was built"
    )

    container_id: str = Field(
        description="Docker container ID"
    )

    container_name: str = Field(
        description="Docker container name"
    )

    host_port: int = Field(
        description="Host port the container is mapped to"
    )

    container_port: int = Field(
        description="Container internal port"
    )

    url: str = Field(
        description="URL to access the deployed application"
    )

    status: str = Field(
        description="Deployment status (building, running, stopped, failed)"
    )

    created_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="Creation timestamp"
    )

    logs_tail: Optional[str] = Field(
        default=None,
        description="Tail of container logs"
    )

    env: Dict[str, str] = Field(
        default_factory=dict,
        description="Environment variables used"
    )

    labels: Dict[str, str] = Field(
        default_factory=dict,
        description="Docker labels"
    )


class ContainerFilter(BaseModel):
    """Filter parameters for listing containers."""
    all: bool = Field(
        default=False,
        description="Show all containers (including stopped)"
    )

    label_filter: Optional[Dict[str, str]] = Field(
        default=None,
        description="Filter by labels"
    )


class ContainerAction(BaseModel):
    """Action parameters for container operations."""
    container_id: str = Field(
        description="Container ID or name"
    )

    force: bool = Field(
        default=False,
        description="Force stop/remove even if running"
    )


class ContainerLogRequest(BaseModel):
    """Request for getting container logs."""
    container_id: str = Field(
        description="Container ID or name"
    )

    tail: int = Field(
        default=100,
        description="Number of lines to return"
    )

    timestamps: bool = Field(
        default=False,
        description="Include timestamps"
    )


class BuildRequest(BaseModel):
    """Request for building a Docker image."""
    path: str = Field(
        description="Path to the build context (directory with Dockerfile)"
    )

    tag: str = Field(
        description="Image tag (e.g., myapp:latest)"
    )

    build_args: Dict[str, str] = Field(
        default_factory=dict,
        description="Build arguments"
    )

    rm: bool = Field(
        default=True,
        description="Remove intermediate containers"
    )

    nocache: bool = Field(
        default=False,
        description="Disable cache"
    )


class RunContainerRequest(BaseModel):
    """Request for running a Docker container."""
    image: str = Field(
        description="Image to run"
    )

    name: Optional[str] = Field(
        default=None,
        description="Container name"
    )

    ports: Dict[str, int] = Field(
        default_factory=dict,
        description="Port mappings {host_port: container_port}"
    )

    env: Dict[str, str] = Field(
        default_factory=dict,
        description="Environment variables"
    )

    labels: Dict[str, str] = Field(
        default_factory=dict,
        description="Docker labels"
    )

    detach: bool = Field(
        default=True,
        description="Run in detached mode"
    )

    restart_policy: str = Field(
        default="unless-stopped",
        description="Restart policy (no, always, on-failure, unless-stopped)"
    )

    network: Optional[str] = Field(
        default=None,
        description="Network to connect to"
    )

    volumes: Dict[str, str] = Field(
        default_factory=dict,
        description="Volume mounts {host_path: container_path}"
    )


class ImageFilter(BaseModel):
    """Filter parameters for listing images."""
    dangling: bool = Field(
        default=False,
        description="Show dangling images"
    )

    label_filter: Optional[str] = Field(
        default=None,
        description="Filter by label"
    )
