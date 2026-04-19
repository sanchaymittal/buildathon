"""Blue/green rollout helpers backed by ``ComposeDeployService``.

Vector uses these to spin up a candidate stack under
``<project_base>-<candidate_color>`` while the active stack keeps serving.
When Sentry signs off we flip ``active_color`` and tear down the previous
one.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Literal, Optional

from ..docker_svc.compose_models import (
    ComposeTargetRequest,
    DeployLocalRequest,
    DeployLocalResult,
)
from ..docker_svc.compose_service import ComposeDeployError, ComposeDeployService

logger = logging.getLogger(__name__)


def project_base(project_path: str) -> str:
    path = Path(project_path).expanduser().resolve()
    base = path.name.lower().replace(" ", "-") or "project"
    digest = hashlib.sha1(str(path).encode("utf-8")).hexdigest()[:6]
    return f"{base}-{digest}"


def project_name_for(project_path: str, color: str) -> str:
    return f"{project_base(project_path)}-{color}"


def deploy_candidate(
    service: ComposeDeployService,
    *,
    project_path: str,
    color: Literal["blue", "green"],
    compose_file: Optional[str] = None,
    pull: bool = False,
    env: Optional[dict] = None,
) -> DeployLocalResult:
    """Bring up the candidate stack without touching the active one."""
    name = project_name_for(project_path, color)
    request = DeployLocalRequest(
        project_path=project_path,
        project_name=name,
        compose_file=compose_file,
        build=True,
        pull=pull,
        env=env or {},
    )
    return service.deploy(request)


def teardown(
    service: ComposeDeployService,
    *,
    project_path: str,
    color: Literal["blue", "green"],
    compose_file: Optional[str] = None,
) -> dict:
    name = project_name_for(project_path, color)
    try:
        output = service.down(
            ComposeTargetRequest(
                project_path=project_path,
                project_name=name,
                compose_file=compose_file,
            )
        )
        return {"color": color, "output": output, "ok": True}
    except ComposeDeployError as exc:
        return {"color": color, "error": str(exc), "ok": False}


def candidate_status(
    service: ComposeDeployService,
    *,
    project_path: str,
    color: Literal["blue", "green"],
    compose_file: Optional[str] = None,
) -> list:
    name = project_name_for(project_path, color)
    return [
        s.model_dump()
        for s in service.status(
            ComposeTargetRequest(
                project_path=project_path,
                project_name=name,
                compose_file=compose_file,
            )
        )
    ]
