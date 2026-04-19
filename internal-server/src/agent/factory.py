"""
Agent factory - assemble a DevOps agent from tools + prompts.

The default tool set is the local-compose MVP. Legacy docker-py and GitHub
tools are appended conditionally when their optional dependencies are
installed, so a minimal install still produces a usable agent.
"""

from __future__ import annotations

import logging
from typing import Any, List, Optional

from ..gemini_agents import Agent
from .prompts import DEVOPS_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


def default_tools() -> List[Any]:
    """Return the default tool set for the DevOps agent."""
    tools: List[Any] = []

    # Local-compose MVP tools - always available.
    try:
        from ..docker_svc.compose_tools import (
            deploy_local_project,
            project_logs,
            project_status,
            stop_local_project,
        )

        tools.extend(
            [deploy_local_project, project_status, stop_local_project, project_logs]
        )
    except Exception as exc:  # pragma: no cover
        logger.warning("Compose tools unavailable: %s", exc)

    # Legacy docker-py tools - optional.
    try:
        from ..docker_svc.tools import (  # type: ignore
            deploy_repository,
            get_container_logs,
            get_deployment,
            get_deployment_logs,
            list_containers,
            list_deployments,
            list_images,
            remove_container,
            remove_deployment,
            restart_container,
            restart_deployment,
            start_container,
            start_deployment,
            stop_container,
            stop_deployment,
        )

        tools.extend(
            [
                deploy_repository,
                list_deployments,
                get_deployment,
                stop_deployment,
                start_deployment,
                restart_deployment,
                remove_deployment,
                get_deployment_logs,
                list_containers,
                stop_container,
                start_container,
                restart_container,
                remove_container,
                get_container_logs,
                list_images,
            ]
        )
    except Exception as exc:
        logger.info("Legacy Docker tools disabled: %s", exc)

    # GitHub tools - optional.
    try:
        from ..github.github_tools import (  # type: ignore
            create_issue,
            get_repository,
            list_issues,
            list_pull_requests,
        )

        tools.extend([get_repository, list_issues, create_issue, list_pull_requests])
    except Exception as exc:
        logger.info("GitHub tools disabled: %s", exc)

    return tools


def build_devops_agent(
    *,
    tools: Optional[List[Any]] = None,
    model: Optional[str] = None,
    instructions: Optional[str] = None,
    name: str = "Agentic DevOps",
) -> Agent:
    """
    Build a DevOps :class:`Agent`.

    Args:
        tools: Override the default tool set. Pass an empty list to build a
            conversational-only agent.
        model: Override the Gemini model (defaults to the credential manager's
            configured default).
        instructions: Override the system prompt.
        name: Display name for the agent.
    """
    return Agent(
        name=name,
        instructions=instructions or DEVOPS_SYSTEM_PROMPT,
        tools=tools if tools is not None else default_tools(),
        model=model,
    )
