"""
Programmatic example: deploy the bundled sample-app via ComposeDeployService.

Run from the repo root with:

    python examples/docker_compose_local_deploy.py

Requires a running Docker daemon and the ``docker compose`` CLI. No GitHub
token, AWS credentials, or agents-SDK install is required for this flow.
"""

from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
sys.path.insert(0, REPO_ROOT)

from src.docker_svc.compose_models import (  # noqa: E402
    ComposeTargetRequest,
    DeployLocalRequest,
)
from src.docker_svc.compose_service import ComposeDeployService  # noqa: E402


def main() -> int:
    project_path = os.path.join(HERE, "sample-app")
    service = ComposeDeployService(skip_verification=False)

    print(f"==> Deploying {project_path}")
    result = service.deploy(
        DeployLocalRequest(
            project_path=project_path,
            env={"GREETING": "Hello from the local deploy example"},
        )
    )

    print(f"status: {result.status}")
    print(f"project: {result.project_name}")
    if result.agents_md_excerpt:
        print("\n--- AGENTS.md (excerpt) ---")
        print(result.agents_md_excerpt)
        print("---------------------------\n")

    for svc in result.services:
        print(f"  {svc.service}: {svc.state or svc.status} ({svc.name})")

    if result.status != "succeeded":
        print(f"error: {result.error}")
        return 1

    print("\nTry: curl http://localhost:8000/")
    print(
        f"Tear down with: python -m src.cli docker compose down --path {project_path}"
    )
    # Demonstrate the status/down API too (commented out so the sample stays
    # running after the script exits):
    _ = service.status(ComposeTargetRequest(project_path=project_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
