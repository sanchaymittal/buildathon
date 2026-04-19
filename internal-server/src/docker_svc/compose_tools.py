"""
Compose Tools - Agent-facing tool functions for local Compose deployments.

These thin wrappers expose ``ComposeDeployService`` to the Gemini Agents
runtime. The decorator comes from ``src.gemini_agents.function_tool`` which
attaches the ``on_invoke_tool`` / ``original`` metadata the runner uses to
dispatch tool calls and coerce pydantic arguments.
"""

from __future__ import annotations

import logging
from typing import List

from ..core.context import DevOpsContext
from ..gemini_agents import RunContextWrapper, function_tool
from .compose_models import (
    ComposeLogsRequest,
    ComposeServiceStatus,
    ComposeTargetRequest,
    DeployLocalRequest,
    DeployLocalResult,
)
from .compose_service import ComposeDeployService

logger = logging.getLogger(__name__)


def _get_service() -> ComposeDeployService:
    return ComposeDeployService(skip_verification=True)


@function_tool()
async def deploy_local_project(
    ctx: RunContextWrapper[DevOpsContext],
    request: DeployLocalRequest,
) -> DeployLocalResult:
    """
    Deploy a local project directory via ``docker compose up -d``.

    The target directory must contain a Dockerfile and a compose file
    (``compose.yml`` or ``docker-compose.yml``). ``AGENTS.md`` is read as
    advisory context if present.
    """
    logger.info("Deploying local project: %s", request.project_path)
    return _get_service().deploy(request)


@function_tool()
async def project_status(
    ctx: RunContextWrapper[DevOpsContext],
    request: ComposeTargetRequest,
) -> List[ComposeServiceStatus]:
    """Return the status of each compose service in a local project."""
    logger.info("Checking status for: %s", request.project_path)
    return _get_service().status(request)


@function_tool()
async def stop_local_project(
    ctx: RunContextWrapper[DevOpsContext],
    request: ComposeTargetRequest,
) -> str:
    """Stop a local compose project via ``docker compose down``."""
    logger.info("Stopping local project: %s", request.project_path)
    return _get_service().down(request)


@function_tool()
async def project_logs(
    ctx: RunContextWrapper[DevOpsContext],
    request: ComposeLogsRequest,
) -> str:
    """Return recent logs for a local compose project."""
    logger.info("Fetching logs for: %s", request.project_path)
    return _get_service().logs(request)
