"""
Compose Tools - Agent-facing tool functions for local Compose deployments.

These thin wrappers expose ``ComposeDeployService`` to the OpenAI Agents SDK.
If the ``agents`` package is not installed (e.g. during unit tests) the tool
functions are still importable as plain async coroutines.
"""

from __future__ import annotations

import logging
from typing import List

from .compose_models import (
    ComposeLogsRequest,
    ComposeServiceStatus,
    ComposeTargetRequest,
    DeployLocalRequest,
    DeployLocalResult,
)
from .compose_service import ComposeDeployService

logger = logging.getLogger(__name__)


try:  # pragma: no cover - the SDK may not be installed in minimal test envs
    from agents import function_tool, RunContextWrapper  # type: ignore
    from ..core.context import DevOpsContext

    _AGENTS_AVAILABLE = True
except Exception:  # pragma: no cover
    _AGENTS_AVAILABLE = False

    def function_tool(*_args, **_kwargs):  # type: ignore[no-redef]
        def decorator(func):
            return func

        return decorator

    class RunContextWrapper:  # type: ignore[no-redef]
        pass

    class DevOpsContext:  # type: ignore[no-redef]
        pass


def _get_service() -> ComposeDeployService:
    return ComposeDeployService(skip_verification=True)


@function_tool()
async def deploy_local_project(
    ctx: "RunContextWrapper[DevOpsContext]",
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
    ctx: "RunContextWrapper[DevOpsContext]",
    request: ComposeTargetRequest,
) -> List[ComposeServiceStatus]:
    """Return the status of each compose service in a local project."""
    logger.info("Checking status for: %s", request.project_path)
    return _get_service().status(request)


@function_tool()
async def stop_local_project(
    ctx: "RunContextWrapper[DevOpsContext]",
    request: ComposeTargetRequest,
) -> str:
    """Stop a local compose project via ``docker compose down``."""
    logger.info("Stopping local project: %s", request.project_path)
    return _get_service().down(request)


@function_tool()
async def project_logs(
    ctx: "RunContextWrapper[DevOpsContext]",
    request: ComposeLogsRequest,
) -> str:
    """Return recent logs for a local compose project."""
    logger.info("Fetching logs for: %s", request.project_path)
    return _get_service().logs(request)
