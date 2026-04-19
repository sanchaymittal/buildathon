"""
Docker Deploy Module - Provides orchestration for GitHub-to-Docker deployments.

This module handles cloning repositories, building images, and running containers.
"""

import io
import logging
import os
import shutil
import subprocess
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from .base import (
    DockerServiceError,
    ContainerNotFoundError,
    ImageBuildError,
    RepositoryError,
    docker_operation,
)
from .models import (
    ContainerFilter,
    ContainerAction,
    ContainerLogRequest,
    ContainerStatus,
    DeployRequest,
    Deployment,
)

logger = logging.getLogger(__name__)


def _parse_github_repo(repo: str) -> tuple:
    """Parse GitHub repository string into owner and repo."""
    if "/" not in repo:
        raise RepositoryError(
            f"Invalid repository format: {repo}. Use 'owner/repo' format."
        )

    parts = repo.split("/")
    if len(parts) != 2:
        raise RepositoryError(
            f"Invalid repository format: {repo}. Use 'owner/repo' format."
        )

    return parts[0], parts[1]


class DockerDeployService:
    """Service for deploying GitHub repositories to Docker."""

    def __init__(
        self,
        docker_service: Optional["DockerService"] = None,
        workspace_dir: str = "/tmp/devops-deploys",
    ):
        """
        Initialize the deployment service.

        Args:
            docker_service: DockerService instance (created if not provided)
            workspace_dir: Directory for cloned repositories
        """
        from .service import DockerService

        if docker_service:
            self.docker = docker_service
        else:
            self.docker = DockerService()

        self.workspace_dir = Path(workspace_dir)
        self.workspace_dir.mkdir(parents=True, exist_ok=True)

        self.deployments: Dict[str, Deployment] = {}

    @docker_operation("clone_repository")
    def _clone_repository(
        self,
        owner: str,
        repo: str,
        branch: str,
        target_dir: Path,
        github_token: Optional[str] = None,
    ) -> None:
        """
        Clone a GitHub repository.

        Args:
            owner: Repository owner
            repo: Repository name
            branch: Branch to checkout
            target_dir: Target directory
            github_token: Optional GitHub token for private repos
        """
        url = f"https://github.com/{owner}/{repo}.git"

        if github_token:
            url = f"https://x-access-token:{github_token}@github.com/{owner}/{repo}.git"

        try:
            result = subprocess.run(
                ["git", "clone", "--depth", "1", "--branch", branch, url, str(target_dir)],
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode != 0:
                error_msg = result.stderr or result.stdout
                if "not found" in error_msg.lower() or "404" in error_msg:
                    raise RepositoryError(
                        f"Repository or branch not found: {owner}/{repo} (branch: {branch})"
                    )
                raise RepositoryError(f"Git clone failed: {error_msg}")

        except subprocess.TimeoutExpired:
            raise RepositoryError(
                f"Git clone timed out for {owner}/{repo}",
                suggestion="Check your network connection or try a smaller repo."
            )
        except FileNotFoundError:
            raise RepositoryError(
                "Git is not installed",
                suggestion="Install git: apt-get install git"
            )

    @docker_operation("check_dockerfile")
    def _check_dockerfile(self, path: Path) -> bool:
        """
        Check if a Dockerfile exists in the path.

        Args:
            path: Directory to check

        Returns:
            True if Dockerfile exists
        """
        dockerfile_path = path / "Dockerfile"
        return dockerfile_path.exists()

    @docker_operation("generate_deployment_name")
    def _generate_deployment_name(self, repo: str) -> str:
        """
        Generate a deployment name from repository.

        Args:
            repo: Repository in owner/repo format

        Returns:
            Deployment name
        """
        owner, name = _parse_github_repo(repo)
        safe_name = "".join(c if c.isalnum() or c in "-_" else "-" for c in name)
        return f"devops-{safe_name}"

    @docker_operation("deploy_from_github")
    def deploy_from_github(
        self,
        request: DeployRequest,
        github_token: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Deployment:
        """
        Deploy a GitHub repository to Docker.

        Args:
            request: Deployment request
            github_token: Optional GitHub token for private repos

        Returns:
            Deployment object
        """
        owner, repo = _parse_github_repo(request.repository)

        deploy_id = str(uuid.uuid4())[:8]
        name = request.name or self._generate_deployment_name(request.repository)
        container_name = f"{name}-{deploy_id}"

        target_dir = self.workspace_dir / deploy_id
        target_dir.mkdir(parents=True, exist_ok=True)

        try:
            self._clone_repository(
                owner=owner,
                repo=repo,
                branch=request.branch,
                target_dir=target_dir,
                github_token=github_token,
            )

            if not self._check_dockerfile(target_dir):
                raise RepositoryError(
                    f"No Dockerfile found in {request.repository}:{request.branch}",
                    suggestion="Add a Dockerfile to the repository root or use 'build_args' for runtime detection."
                )

            image_tag = f"devops-{repo}:{request.branch}-{deploy_id}"

            build_result = self.docker.build_image(
                path=str(target_dir),
                tag=image_tag,
                build_args=request.build_args,
            )

            host_port = self.docker._allocate_free_port()

            labels = {
                "managed-by": "devops-agent",
                "deployment-id": deploy_id,
                "repository": request.repository,
                "branch": request.branch,
            }
            if user_id:
                labels["user-id"] = user_id

            container = self.docker.run_container(
                image=image_tag,
                name=container_name,
                ports={str(host_port): request.container_port},
                env=request.env,
                labels=labels,
                detach=True,
                restart_policy="unless-stopped",
            )

            container.reload()

            deployment = Deployment(
                id=deploy_id,
                user_id=user_id,
                repository=request.repository,
                branch=request.branch,
                image=image_tag,
                container_id=container.id,
                container_name=container_name,
                host_port=host_port,
                container_port=request.container_port,
                url=f"http://localhost:{host_port}",
                status="running",
                env=request.env,
                labels=labels,
            )

            self.deployments[deploy_id] = deployment

            return deployment

        except Exception as e:
            logger.error(f"Deployment failed: {e}")
            raise
        finally:
            if target_dir.exists():
                shutil.rmtree(target_dir, ignore_errors=True)

    def list_deployments(self) -> List[Deployment]:
        """List all deployments."""
        return list(self.deployments.values())

    def get_deployment(self, deploy_id: str) -> Deployment:
        """Get a deployment by ID."""
        if deploy_id not in self.deployments:
            raise DockerServiceError(f"Deployment '{deploy_id}' not found")
        return self.deployments[deploy_id]

    @docker_operation("stop_deployment")
    def stop_deployment(self, deploy_id: str) -> Deployment:
        """Stop a deployment."""
        deployment = self.get_deployment(deploy_id)

        self.docker.stop_container(deployment.container_id, force=True)

        deployment.status = "stopped"
        self.deployments[deploy_id] = deployment

        return deployment

    @docker_operation("start_deployment")
    def start_deployment(self, deploy_id: str) -> Deployment:
        """Start a stopped deployment."""
        deployment = self.get_deployment(deploy_id)

        self.docker.start_container(deployment.container_id)

        deployment.status = "running"
        self.deployments[deploy_id] = deployment

        return deployment

    @docker_operation("restart_deployment")
    def restart_deployment(self, deploy_id: str) -> Deployment:
        """Restart a deployment."""
        deployment = self.get_deployment(deploy_id)

        self.docker.restart_container(deployment.container_id)

        deployment.status = "running"
        self.deployments[deploy_id] = deployment

        return deployment

    @docker_operation("remove_deployment")
    def remove_deployment(self, deploy_id: str) -> Dict[str, Any]:
        """Remove a deployment and its container."""
        deployment = self.get_deployment(deploy_id)

        try:
            self.docker.remove_container(deployment.container_id, force=True)
        except ContainerNotFoundError:
            pass

        try:
            self.docker.remove_image(deployment.image, force=True)
        except Exception:
            pass

        del self.deployments[deploy_id]

        return {"status": "removed", "deployment_id": deploy_id}

    @docker_operation("get_deployment_logs")
    def get_deployment_logs(
        self,
        deploy_id: str,
        tail: int = 100,
    ) -> str:
        """Get deployment logs."""
        deployment = self.get_deployment(deploy_id)

        return self.docker.get_logs(
            deployment.container_id,
            tail=tail,
            timestamps=False,
        )

    @docker_operation("list_managed_containers")
    def list_managed_containers(self) -> List[Dict[str, Any]]:
        """List containers managed by this service."""
        return self.docker.list_containers(
            all=True,
            label_filter={"managed-by": "devops-agent"},
        )

    @docker_operation("redeploy")
    def redeploy(
        self,
        deploy_id: str,
        github_token: Optional[str] = None,
    ) -> Deployment:
        """Redeploy a repository (rebuild and restart)."""
        deployment = self.get_deployment(deploy_id)

        request = DeployRequest(
            repository=deployment.repository,
            branch=deployment.branch,
            container_port=deployment.container_port,
            env=deployment.env,
        )

        old_container_id = deployment.container_id

        try:
            new_deployment = self.deploy_from_github(
                request,
                github_token,
                user_id=deployment.user_id,
            )

            self.docker.remove_container(old_container_id, force=True)

            return new_deployment

        except Exception as e:
            deployment.status = "failed"
            self.deployments[deploy_id] = deployment
            raise DockerServiceError(f"Redeployment failed: {e}")
