"""
Docker Service Module - Provides functionality for Docker container operations.

This module enables building images, running containers, and managing
Docker deployments.
"""

import io
import logging
import socket
import time
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse

import docker
from docker.errors import APIError, NotFound
from docker.models.containers import Container
from docker.models.images import Image

from .base import (
    DockerServiceError,
    ContainerNotFoundError,
    ImageNotFoundError,
    ImageBuildError,
    ContainerStartError,
    ContainerStopError,
    DockerDaemonError,
    PortAllocationError,
    docker_operation,
)

logger = logging.getLogger(__name__)


class DockerService:
    """Service class for managing Docker containers and images."""

    def __init__(self, base_url: Optional[str] = None):
        """
        Initialize the Docker service.

        Args:
            base_url: Docker daemon URL (default: local socket)
        """
        try:
            if base_url:
                self.client = docker.DockerClient(base_url=base_url)
            else:
                self.client = docker.from_env()
        except Exception as e:
            raise DockerDaemonError(f"Failed to connect to Docker daemon: {e}")

        self._verify_connection()

    def _verify_connection(self) -> None:
        """Verify Docker daemon is accessible."""
        try:
            self.client.ping()
        except Exception as e:
            raise DockerDaemonError(f"Docker daemon not accessible: {e}")

    @docker_operation("list_containers")
    def list_containers(
        self,
        all: bool = False,
        label_filter: Optional[Dict[str, str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        List containers.

        Args:
            all: Show all containers (including stopped)
            label_filter: Filter by labels

        Returns:
            List of container info dictionaries
        """
        filters = {}
        if label_filter:
            filters["label"] = [f"{k}={v}" for k, v in label_filter.items()]

        containers = self.client.containers.list(all=all, filters=filters)

        result = []
        for c in containers:
            result.append({
                "id": c.id,
                "short_id": c.short_id,
                "name": c.name,
                "image": c.image.tags[0] if c.image.tags else c.image.short_id,
                "status": c.status,
                "state": c.attrs.get("State", {}).get("Status"),
                "created": c.attrs.get("Created"),
                "ports": {p.get("HostPort"): p.get("ContainerPort")
                         for p in c.ports or []},
                "labels": c.labels,
            })

        return result

    @docker_operation("get_container")
    def get_container(self, container_id: str) -> Dict[str, Any]:
        """
        Get container details.

        Args:
            container_id: Container ID or name

        Returns:
            Container info dictionary
        """
        try:
            container = self.client.containers.get(container_id)
        except NotFound:
            raise ContainerNotFoundError(container_id)
        except APIError as e:
            raise DockerServiceError(f"Failed to get container: {e}")

        ports = {}
        for port, bindings in container.ports.items():
            if bindings:
                ports[port] = [{"HostPort": b.get("HostPort"),
                               "HostIp": b.get("HostIp")}
                              for b in bindings]

        return {
            "id": container.id,
            "short_id": container.short_id,
            "name": container.name,
            "image": container.image.tags[0] if container.image.tags else container.image.short_id,
            "status": container.status,
            "state": container.attrs.get("State", {}).get("Status"),
            "created": container.attrs.get("Created"),
            "ports": ports,
            "labels": container.labels,
            "env": [e for e in container.attrs.get("Config", {}).get("Env", [])],
            "cmd": container.attrs.get("Config", {}).get("Cmd"),
            "workdir": container.attrs.get("Config", {}).get("WorkingDir"),
        }

    def _allocate_free_port(self) -> int:
        """
        Find and allocate a free host port.

        Returns:
            Free port number
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('127.0.0.1', 0))
            port = s.getsockname()[1]
            return port

    @docker_operation("build_image")
    def build_image(
        self,
        path: str,
        tag: str,
        build_args: Optional[Dict[str, str]] = None,
        rm: bool = True,
        nocache: bool = False,
    ) -> Dict[str, Any]:
        """
        Build a Docker image.

        Args:
            path: Path to build context
            tag: Image tag (e.g., myapp:latest)
            build_args: Build arguments
            rm: Remove intermediate containers
            nocache: Disable cache

        Returns:
            Build result with image info
        """
        try:
            image, logs = self.client.images.build(
                path=path,
                tag=tag,
                buildargs=build_args or {},
                rm=rm,
                nocache=nocache,
            )
        except APIError as e:
            raise ImageBuildError(f"Build failed: {e.explanation}")

        return {
            "image": image,
            "id": image.id,
            "short_id": image.short_id,
            "tags": image.tags,
        }

    @docker_operation("run_container")
    def run_container(
        self,
        image: str,
        name: Optional[str] = None,
        ports: Optional[Dict[str, int]] = None,
        env: Optional[Dict[str, str]] = None,
        labels: Optional[Dict[str, str]] = None,
        detach: bool = True,
        restart_policy: str = "unless-stopped",
        network: Optional[str] = None,
        volumes: Optional[Dict[str, str]] = None,
    ) -> Container:
        """
        Run a Docker container.

        Args:
            image: Image name
            name: Container name
            ports: Port mappings {host_port: container_port}
            env: Environment variables
            labels: Docker labels
            detach: Run detached
            restart_policy: Restart policy
            network: Network name
            volumes: Volume mounts {host_path: container_path}

        Returns:
            Container object
        """
        port_bindings = {}
        if ports:
            for host_port, container_port in ports.items():
                port_bindings[f"{container_port}/tcp"] = host_port

        # Allocate free port if not specified
        if ports is None:
            free_port = self._allocate_free_port()
            port_bindings = {"80/tcp": free_port}

        env_list = None
        if env:
            env_list = [f"{k}={v}" for k, v in env.items()]

        labels = labels or {}
        labels["managed-by"] = "devops-agent"

        restart_policy_dict = {"Name": restart_policy}

        try:
            container = self.client.containers.run(
                image=image,
                name=name,
                ports=port_bindings,
                environment=env_list,
                labels=labels,
                detach=detach,
                restart_policy=restart_policy_dict,
                network=network,
                volumes=volumes,
                remove=False,
            )
        except APIError as e:
            raise ContainerStartError(image, str(e.explanation))

        return container

    @docker_operation("stop_container")
    def stop_container(self, container_id: str, force: bool = False) -> None:
        """
        Stop a container.

        Args:
            container_id: Container ID or name
            force: Force stop
        """
        try:
            container = self.client.containers.get(container_id)
            container.stop(force=force)
        except NotFound:
            raise ContainerNotFoundError(container_id)
        except APIError as e:
            raise ContainerStopError(container_id, str(e.explanation))

    @docker_operation("start_container")
    def start_container(self, container_id: str) -> None:
        """
        Start a container.

        Args:
            container_id: Container ID or name
        """
        try:
            container = self.client.containers.get(container_id)
            container.start()
        except NotFound:
            raise ContainerNotFoundError(container_id)
        except APIError as e:
            raise ContainerStartError(container_id, str(e.explanation))

    @docker_operation("restart_container")
    def restart_container(self, container_id: str) -> None:
        """
        Restart a container.

        Args:
            container_id: Container ID or name
        """
        try:
            container = self.client.containers.get(container_id)
            container.restart()
        except NotFound:
            raise ContainerNotFoundError(container_id)
        except APIError as e:
            raise ContainerStartError(container_id, str(e.explanation))

    @docker_operation("remove_container")
    def remove_container(self, container_id: str, force: bool = False) -> None:
        """
        Remove a container.

        Args:
            container_id: Container ID or name
            force: Force remove
        """
        try:
            container = self.client.containers.get(container_id)
            container.remove(force=force)
        except NotFound:
            raise ContainerNotFoundError(container_id)
        except APIError as e:
            raise DockerServiceError(f"Failed to remove container: {e.explanation}")

    @docker_operation("get_logs")
    def get_logs(self, container_id: str, tail: int = 100, timestamps: bool = False) -> str:
        """
        Get container logs.

        Args:
            container_id: Container ID or name
            tail: Number of lines
            timestamps: Include timestamps

        Returns:
            Log string
        """
        try:
            container = self.client.containers.get(container_id)
        except NotFound:
            raise ContainerNotFoundError(container_id)

        logs = container.logs(
            tail=tail,
            timestamps=timestamps,
            stream=False,
        )

        if isinstance(logs, bytes):
            return logs.decode("utf-8", errors="replace")
        return str(logs)

    @docker_operation("exec_in_container")
    def exec_in_container(self, container_id: str, cmd: List[str]) -> str:
        """
        Execute a command in a running container.

        Args:
            container_id: Container ID or name
            cmd: Command and arguments

        Returns:
            Command output
        """
        try:
            container = self.client.containers.get(container_id)
        except NotFound:
            raise ContainerNotFoundError(container_id)

        result = container.exec_run(cmd, socket=False)

        if result.output:
            return result.output.decode("utf-8", errors="replace")
        return ""

    @docker_operation("list_images")
    def list_images(
        self,
        dangling: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        List images.

        Args:
            dangling: Show dangling images

        Returns:
            List of image info dictionaries
        """
        filters = {}
        if dangling:
            filters["dangling"] = True

        images = self.client.images.list(filters=filters)

        result = []
        for img in images:
            result.append({
                "id": img.id,
                "short_id": img.short_id,
                "tags": img.tags,
                "size": img.attrs.get("Size"),
                "created": img.attrs.get("Created"),
            })

        return result

    @docker_operation("remove_image")
    def remove_image(self, image: str, force: bool = False) -> None:
        """
        Remove an image.

        Args:
            image: Image name or ID
            force: Force remove
        """
        try:
            img = self.client.images.get(image)
            img.remove(force=force)
        except NotFound:
            raise ImageNotFoundError(image)
        except APIError as e:
            raise DockerServiceError(f"Failed to remove image: {e.explanation}")

    @docker_operation("prune_images")
    def prune_images(self, dangling: bool = True) -> Dict[str, Any]:
        """
        Prune unused images.

        Args:
            dangling: Only prune dangling images

        Returns:
            Prune result
        """
        return self.client.images.prune(dangling=dangling)

    @docker_operation("prune_containers")
    def prune_containers(self) -> Dict[str, Any]:
        """
        Prune stopped containers.

        Returns:
            Prune result
        """
        return self.client.containers.prune()

    def close(self) -> None:
        """Close the Docker client connection."""
        self.client.close()