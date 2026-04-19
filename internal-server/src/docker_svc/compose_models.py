"""
Compose Models - Pydantic models for local Docker Compose deployments.

These models support the hackathon MVP flow: take a local repo path that
contains a Dockerfile and a compose file (``compose.yml`` or
``docker-compose.yml``) and run it on the local Docker daemon.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class DeployLocalRequest(BaseModel):
    """Request model for deploying a local project via Docker Compose."""

    project_path: str = Field(
        description="Absolute or relative path to the local project directory"
    )

    compose_file: Optional[str] = Field(
        default=None,
        description=(
            "Compose filename relative to project_path. If omitted, the service "
            "auto-detects 'compose.yml' then 'docker-compose.yml'."
        ),
    )

    project_name: Optional[str] = Field(
        default=None,
        description=(
            "Compose project name. Defaults to '<basename>-<shorthash>' of "
            "project_path."
        ),
    )

    env: Dict[str, str] = Field(
        default_factory=dict,
        description="Environment variables passed to 'docker compose up'",
    )

    env_file: Optional[str] = Field(
        default=None,
        description="Optional .env file relative to project_path",
    )

    build: bool = Field(
        default=True,
        description="Whether to pass --build to 'docker compose up'",
    )

    pull: bool = Field(
        default=False,
        description="Whether to pass --pull always to 'docker compose up'",
    )


class ComposeServiceStatus(BaseModel):
    """Status of a single compose service."""

    service: str
    container_id: str = ""
    name: str = ""
    state: str = ""
    status: str = ""
    ports: str = ""


class DeployLocalResult(BaseModel):
    """Result of a local compose deployment."""

    status: str = Field(description="'succeeded' or 'failed'")
    project_name: str
    project_path: str
    compose_file: str
    services: List[ComposeServiceStatus] = Field(default_factory=list)
    output: str = ""
    error: Optional[str] = None
    agents_md_excerpt: Optional[str] = None


class ComposeLogsRequest(BaseModel):
    """Request for fetching compose logs."""

    project_path: str
    compose_file: Optional[str] = None
    project_name: Optional[str] = None
    service: Optional[str] = None
    tail: int = 200


class ComposeTargetRequest(BaseModel):
    """Reference to a compose project for stop/status operations."""

    project_path: str
    compose_file: Optional[str] = None
    project_name: Optional[str] = None
