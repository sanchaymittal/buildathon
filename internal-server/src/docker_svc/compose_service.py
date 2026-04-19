"""
Compose Service - Local Docker Compose deployment for the hackathon MVP.

This service takes a local directory containing a Dockerfile and a compose
file (``compose.yml`` or ``docker-compose.yml``) and drives ``docker compose``
via subprocess to bring the stack up on the local Docker daemon.

Design notes:

* Pure subprocess — no docker-py dependency. Keeps the MVP footprint small
  and makes tests trivial to mock via ``subprocess.run``.
* No auth, no remote hosts, no registry push. Local only.
* AGENTS.md in the target repo is read as advisory content only; a short
  excerpt is surfaced in the deploy result so the agent/operator can see it.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

from .base import DockerDaemonError, DockerServiceError
from .compose_models import (
    ComposeLogsRequest,
    ComposeServiceStatus,
    ComposeTargetRequest,
    DeployLocalRequest,
    DeployLocalResult,
)

logger = logging.getLogger(__name__)


_COMPOSE_FILENAMES = (
    "compose.yml",
    "compose.yaml",
    "docker-compose.yml",
    "docker-compose.yaml",
)


class ComposeDeployError(DockerServiceError):
    """Raised when a local compose deployment fails."""

    def __init__(
        self, message: str, suggestion: Optional[str] = None, output: str = ""
    ):
        super().__init__(message, suggestion)
        self.output = output


class ComposeDeployService:
    """
    Service for deploying a local project via Docker Compose.

    All methods are safe to call without a live Docker daemon in tests: the
    daemon ping can be disabled with ``skip_verification=True``.
    """

    def __init__(self, skip_verification: bool = False) -> None:
        if not skip_verification:
            self.ping()

    # ------------------------------------------------------------------ daemon
    def ping(self) -> None:
        """Verify the local Docker daemon is reachable."""
        try:
            result = subprocess.run(
                ["docker", "version", "--format", "{{.Server.Version}}"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except FileNotFoundError as exc:
            raise DockerDaemonError(
                "The 'docker' CLI is not installed or not on PATH."
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise DockerDaemonError("Timed out talking to the Docker daemon.") from exc

        if result.returncode != 0:
            raise DockerDaemonError(
                f"Docker daemon not reachable: {result.stderr.strip() or result.stdout.strip()}"
            )

    # ----------------------------------------------------------------- helpers
    def _resolve_project_path(self, project_path: str) -> Path:
        path = Path(project_path).expanduser().resolve()
        if not path.exists():
            raise ComposeDeployError(
                f"Project path does not exist: {project_path}",
                suggestion="Pass an absolute path or a valid relative path.",
            )
        if not path.is_dir():
            raise ComposeDeployError(
                f"Project path is not a directory: {project_path}",
            )
        return path

    def _resolve_compose_file(
        self, project_path: Path, compose_file: Optional[str]
    ) -> Path:
        if compose_file:
            candidate = (project_path / compose_file).resolve()
            if not candidate.exists():
                raise ComposeDeployError(
                    f"Compose file not found: {candidate}",
                    suggestion="Check the --compose-file value.",
                )
            return candidate

        for name in _COMPOSE_FILENAMES:
            candidate = project_path / name
            if candidate.exists():
                return candidate

        raise ComposeDeployError(
            f"No compose file found in {project_path}. "
            f"Expected one of: {', '.join(_COMPOSE_FILENAMES)}",
            suggestion=(
                "Add a compose.yml or docker-compose.yml to the project root, "
                "or ask Forge to run scaffold_project to auto-generate one "
                "for python / node / static stacks."
            ),
        )

    def _default_project_name(self, project_path: Path) -> str:
        base = project_path.name.lower().replace(" ", "-")
        safe = (
            "".join(c if c.isalnum() or c in "-_" else "-" for c in base) or "project"
        )
        digest = hashlib.sha1(str(project_path).encode("utf-8")).hexdigest()[:6]
        return f"{safe}-{digest}"

    def _compose_cmd(
        self,
        compose_file: Path,
        project_name: str,
        env_file: Optional[Path],
        extra: List[str],
    ) -> List[str]:
        cmd = ["docker", "compose", "-f", str(compose_file), "-p", project_name]
        if env_file is not None:
            cmd.extend(["--env-file", str(env_file)])
        cmd.extend(extra)
        return cmd

    def _run(
        self,
        cmd: List[str],
        cwd: Path,
        env: Optional[Dict[str, str]] = None,
        timeout: int = 600,
    ) -> subprocess.CompletedProcess:
        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)
        logger.info("Running: %s (cwd=%s)", " ".join(cmd), cwd)
        return subprocess.run(
            cmd,
            cwd=str(cwd),
            env=merged_env,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )

    def _read_agents_md(self, project_path: Path) -> Optional[str]:
        md = project_path / "AGENTS.md"
        if not md.exists():
            return None
        try:
            text = md.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return None
        # Short advisory excerpt: first 30 non-empty lines, capped at 2000 chars.
        lines = [line for line in text.splitlines() if line.strip()]
        excerpt = "\n".join(lines[:30])
        if len(excerpt) > 2000:
            excerpt = excerpt[:2000] + "\n... (truncated)"
        return excerpt

    def _parse_ps_json(self, stdout: str) -> List[ComposeServiceStatus]:
        statuses: List[ComposeServiceStatus] = []
        if not stdout.strip():
            return statuses

        # ``docker compose ps --format json`` historically emits either a JSON
        # array or newline-delimited JSON depending on the CLI version. Handle
        # both.
        payloads: List[dict] = []
        stripped = stdout.strip()
        try:
            parsed = json.loads(stripped)
            if isinstance(parsed, list):
                payloads = parsed
            elif isinstance(parsed, dict):
                payloads = [parsed]
        except json.JSONDecodeError:
            for line in stripped.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    payloads.append(json.loads(line))
                except json.JSONDecodeError:
                    logger.debug("Skipping non-JSON compose ps line: %r", line)

        for item in payloads:
            statuses.append(
                ComposeServiceStatus(
                    service=item.get("Service") or item.get("service") or "",
                    container_id=item.get("ID") or item.get("Id") or "",
                    name=item.get("Name") or item.get("name") or "",
                    state=item.get("State") or item.get("state") or "",
                    status=item.get("Status") or item.get("status") or "",
                    ports=item.get("Publishers")
                    and json.dumps(item.get("Publishers"))
                    or item.get("Ports")
                    or "",
                )
            )
        return statuses

    # ---------------------------------------------------------------- commands
    def deploy(self, request: DeployLocalRequest) -> DeployLocalResult:
        """
        Bring up a local project with ``docker compose up -d``.

        Returns a ``DeployLocalResult`` describing service statuses. On failure
        the result's ``status`` field is ``'failed'`` and ``error`` contains
        stderr; this method does not raise for compose-level failures so that
        the agent can reason about them.
        """
        project_path = self._resolve_project_path(request.project_path)
        compose_file = self._resolve_compose_file(project_path, request.compose_file)
        project_name = request.project_name or self._default_project_name(project_path)

        env_file_path: Optional[Path] = None
        if request.env_file:
            candidate = (project_path / request.env_file).resolve()
            if not candidate.exists():
                raise ComposeDeployError(
                    f"env file not found: {candidate}",
                    suggestion="Check the --env-file value.",
                )
            env_file_path = candidate

        # Advisory: pick up AGENTS.md if present.
        agents_md = self._read_agents_md(project_path)

        up_args = ["up", "-d", "--remove-orphans"]
        if request.build:
            up_args.append("--build")
        if request.pull:
            up_args.extend(["--pull", "always"])

        up_cmd = self._compose_cmd(compose_file, project_name, env_file_path, up_args)
        up_result = self._run(up_cmd, cwd=project_path, env=request.env)

        output = (up_result.stdout or "") + (up_result.stderr or "")

        if up_result.returncode != 0:
            return DeployLocalResult(
                status="failed",
                project_name=project_name,
                project_path=str(project_path),
                compose_file=str(compose_file),
                services=[],
                output=output,
                error=(up_result.stderr or up_result.stdout).strip()
                or "compose up failed",
                agents_md_excerpt=agents_md,
            )

        services = self._collect_status(project_path, compose_file, project_name)

        return DeployLocalResult(
            status="succeeded",
            project_name=project_name,
            project_path=str(project_path),
            compose_file=str(compose_file),
            services=services,
            output=output,
            error=None,
            agents_md_excerpt=agents_md,
        )

    def _collect_status(
        self,
        project_path: Path,
        compose_file: Path,
        project_name: str,
    ) -> List[ComposeServiceStatus]:
        ps_cmd = self._compose_cmd(
            compose_file, project_name, None, ["ps", "--format", "json"]
        )
        ps_result = self._run(ps_cmd, cwd=project_path)
        if ps_result.returncode != 0:
            logger.warning(
                "compose ps failed (rc=%s): %s",
                ps_result.returncode,
                ps_result.stderr.strip(),
            )
            return []
        return self._parse_ps_json(ps_result.stdout)

    def status(self, request: ComposeTargetRequest) -> List[ComposeServiceStatus]:
        project_path = self._resolve_project_path(request.project_path)
        compose_file = self._resolve_compose_file(project_path, request.compose_file)
        project_name = request.project_name or self._default_project_name(project_path)
        return self._collect_status(project_path, compose_file, project_name)

    def down(self, request: ComposeTargetRequest) -> str:
        project_path = self._resolve_project_path(request.project_path)
        compose_file = self._resolve_compose_file(project_path, request.compose_file)
        project_name = request.project_name or self._default_project_name(project_path)

        cmd = self._compose_cmd(
            compose_file, project_name, None, ["down", "--remove-orphans"]
        )
        result = self._run(cmd, cwd=project_path)
        output = (result.stdout or "") + (result.stderr or "")
        if result.returncode != 0:
            raise ComposeDeployError(
                f"'docker compose down' failed for project {project_name}",
                output=output,
            )
        return output

    def logs(self, request: ComposeLogsRequest) -> str:
        project_path = self._resolve_project_path(request.project_path)
        compose_file = self._resolve_compose_file(project_path, request.compose_file)
        project_name = request.project_name or self._default_project_name(project_path)

        args = ["logs", "--no-color", "--tail", str(request.tail)]
        if request.service:
            args.append(request.service)

        cmd = self._compose_cmd(compose_file, project_name, None, args)
        result = self._run(cmd, cwd=project_path)
        if result.returncode != 0:
            raise ComposeDeployError(
                f"'docker compose logs' failed for project {project_name}",
                output=(result.stdout or "") + (result.stderr or ""),
            )
        return result.stdout or ""
