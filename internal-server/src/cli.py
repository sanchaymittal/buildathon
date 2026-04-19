#!/usr/bin/env python3
"""
Command Line Interface for DevOps Agent.

This module provides a CLI for interacting with DevOps Agent,
allowing users to deploy repositories to Docker and integrate with GitHub.
"""

import sys
import argparse
import logging
import json
from typing import Optional, List

from .core.config import get_config, ConfigError
from .core.credentials import get_credential_manager, CredentialError
from .docker_svc.base import DockerServiceError, ContainerNotFoundError
from .docker_svc.compose_models import (
    ComposeLogsRequest,
    ComposeTargetRequest,
    DeployLocalRequest,
)
from .docker_svc.compose_service import ComposeDeployError, ComposeDeployService

# The legacy GitHub-clone + single-container Docker flow relies on optional
# packages (``docker``, ``agents``, ``PyGithub``). Import lazily so the
# local-compose flow keeps working even when those aren't installed.
try:  # pragma: no cover - depends on optional deps
    from .docker_svc.service import DockerService
    from .docker_svc.deploy import DockerDeployService

    _LEGACY_DOCKER_AVAILABLE = True
except Exception:  # pragma: no cover
    DockerService = None  # type: ignore[assignment]
    DockerDeployService = None  # type: ignore[assignment]
    _LEGACY_DOCKER_AVAILABLE = False

try:  # pragma: no cover - depends on optional deps
    from .github.github import GitHubError, AuthenticationError, GitHubService

    _GITHUB_CLI_AVAILABLE = True
except Exception:  # pragma: no cover

    class GitHubError(Exception):
        pass

    class AuthenticationError(GitHubError):
        pass

    GitHubService = None  # type: ignore[assignment]
    _GITHUB_CLI_AVAILABLE = False

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("devops-agent")

COLORS = {
    "red": "\033[91m",
    "green": "\033[92m",
    "yellow": "\033[93m",
    "cyan": "\033[96m",
    "reset": "\033[0m",
    "bold": "\033[1m",
}


def print_error(
    message: str, details: Optional[str] = None, suggestion: Optional[str] = None
) -> None:
    """Print a formatted error message."""
    print(f"{COLORS['red']}{COLORS['bold']}ERROR: {message}{COLORS['reset']}")
    if details:
        print(f"{details}")
    if suggestion:
        print(f"\n{COLORS['yellow']}SUGGESTION: {suggestion}{COLORS['reset']}")


def handle_cli_error(error: Exception) -> int:
    """Handle CLI errors with user-friendly messages."""
    logger.debug(f"Error details: {error}", exc_info=True)

    if isinstance(error, CredentialError):
        if "GitHub" in str(error):
            print_error(
                "GitHub credentials error",
                f"Error: {error}",
                "Set GITHUB_TOKEN or add to ~/.devops/credentials.json",
            )
        return 1

    if isinstance(error, GitHubError):
        if isinstance(error, AuthenticationError):
            print_error(
                "GitHub authentication failed",
                f"Error: {error}",
                "Check your GitHub token.",
            )
        else:
            print_error(f"GitHub error", f"Error: {error}")
        return 1

    if isinstance(error, DockerServiceError):
        print_error(
            f"Docker operation failed",
            f"Error: {error}",
            getattr(error, "suggestion", None),
        )
        return 1

    print_error(f"Unexpected error", f"Error: {error}")
    return 1


def setup_docker_parser(subparsers):
    """Set up the argument parser for Docker commands."""
    docker_parser = subparsers.add_parser("docker", help="Docker operations")
    docker_subparsers = docker_parser.add_subparsers(
        dest="docker_command", help="Docker command"
    )

    # Deploy command
    deploy_parser = docker_subparsers.add_parser(
        "deploy", help="Deploy a GitHub repository"
    )
    deploy_parser.add_argument(
        "--repo", required=True, help="GitHub repository (owner/repo)"
    )
    deploy_parser.add_argument("--branch", default="main", help="GitHub branch")
    deploy_parser.add_argument("--port", type=int, default=80, help="Container port")
    deploy_parser.add_argument(
        "--env", help="Environment variables (KEY=VALUE, comma-separated)"
    )

    # List deployments
    list_parser = docker_subparsers.add_parser("list", help="List deployments")

    # Logs
    logs_parser = docker_subparsers.add_parser("logs", help="Get deployment logs")
    logs_parser.add_argument("deploy_id", help="Deployment ID")
    logs_parser.add_argument("--tail", type=int, default=100, help="Number of lines")

    # Stop
    stop_parser = docker_subparsers.add_parser("stop", help="Stop a deployment")
    stop_parser.add_argument("deploy_id", help="Deployment ID")

    # Start
    start_parser = docker_subparsers.add_parser(
        "start", help="Start a stopped deployment"
    )
    start_parser.add_argument("deploy_id", help="Deployment ID")

    # Remove
    rm_parser = docker_subparsers.add_parser("rm", help="Remove a deployment")
    rm_parser.add_argument("deploy_id", help="Deployment ID")

    # Containers
    ps_parser = docker_subparsers.add_parser("ps", help="List containers")
    ps_parser.add_argument("--all", action="store_true", help="Show all containers")

    # ------------------------------------------------------------------
    # Local Compose deployment (hackathon MVP)
    # ------------------------------------------------------------------
    compose_parser = docker_subparsers.add_parser(
        "compose",
        help="Deploy a local project via docker compose",
    )
    compose_subparsers = compose_parser.add_subparsers(
        dest="compose_command", help="Compose command"
    )

    compose_up = compose_subparsers.add_parser(
        "up", help="Bring up a local project with docker compose"
    )
    compose_up.add_argument("--path", required=True, help="Path to the local project")
    compose_up.add_argument(
        "--compose-file",
        default=None,
        help="Compose file relative to --path (auto-detected if omitted)",
    )
    compose_up.add_argument("--project", default=None, help="Compose project name")
    compose_up.add_argument(
        "--env",
        action="append",
        default=[],
        help="Environment variable KEY=VALUE (repeatable)",
    )
    compose_up.add_argument(
        "--env-file", default=None, help="Path to .env file relative to --path"
    )
    compose_up.add_argument(
        "--no-build", action="store_true", help="Do not pass --build"
    )
    compose_up.add_argument("--pull", action="store_true", help="Pass --pull always")

    compose_down = compose_subparsers.add_parser(
        "down", help="Bring down a local compose project"
    )
    compose_down.add_argument("--path", required=True, help="Path to the local project")
    compose_down.add_argument("--compose-file", default=None)
    compose_down.add_argument("--project", default=None, help="Compose project name")

    compose_status = compose_subparsers.add_parser(
        "status", help="Show service status for a local compose project"
    )
    compose_status.add_argument(
        "--path", required=True, help="Path to the local project"
    )
    compose_status.add_argument("--compose-file", default=None)
    compose_status.add_argument("--project", default=None, help="Compose project name")

    compose_logs = compose_subparsers.add_parser(
        "logs", help="Show logs for a local compose project"
    )
    compose_logs.add_argument("--path", required=True, help="Path to the local project")
    compose_logs.add_argument("--compose-file", default=None)
    compose_logs.add_argument("--project", default=None, help="Compose project name")
    compose_logs.add_argument(
        "--service", default=None, help="Limit to a single service"
    )
    compose_logs.add_argument(
        "--tail", type=int, default=200, help="Lines of logs to show"
    )


def setup_github_parser(subparsers):
    """Set up the argument parser for GitHub commands."""
    github_parser = subparsers.add_parser("github", help="GitHub operations")
    github_subparsers = github_parser.add_subparsers(
        dest="github_command", help="GitHub command"
    )

    # List repositories
    list_repos_parser = github_subparsers.add_parser(
        "list-repos", help="List GitHub repositories"
    )
    list_repos_parser.add_argument("--org", help="GitHub organization")
    list_repos_parser.add_argument("--user", help="GitHub username")
    list_repos_parser.add_argument(
        "--output", choices=["json", "table"], default="table"
    )

    # Get repository
    get_repo_parser = github_subparsers.add_parser(
        "get-repo", help="Get repository details"
    )
    get_repo_parser.add_argument(
        "repo", help="Repository name or full path (owner/repo)"
    )
    get_repo_parser.add_argument("--owner", help="Repository owner")

    # Get README
    get_readme_parser = github_subparsers.add_parser("get-readme", help="Get README")
    get_readme_parser.add_argument(
        "repo", help="Repository name or full path (owner/repo)"
    )
    get_readme_parser.add_argument("--owner", help="Repository owner")
    get_readme_parser.add_argument("--ref", help="Git reference")

    # List branches
    list_branches_parser = github_subparsers.add_parser(
        "list-branches", help="List branches"
    )
    list_branches_parser.add_argument(
        "repo", help="Repository name or full path (owner/repo)"
    )
    list_branches_parser.add_argument("--owner", help="Repository owner")


def setup_serve_parser(subparsers):
    """Set up the argument parser for serve command."""
    serve_parser = subparsers.add_parser("serve", help="Start the API server")
    serve_parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    serve_parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    serve_parser.add_argument(
        "--reload", action="store_true", help="Enable auto-reload"
    )


def format_output(data, format_type="table"):
    """Format output data."""
    if format_type == "json":
        return json.dumps(data, indent=2, default=str)

    if isinstance(data, list) and data and isinstance(data[0], dict):
        keys = set()
        for item in data:
            keys.update(item.keys())

        priority_fields = ["id", "name", "repository", "url", "status"]
        ordered_keys = [k for k in priority_fields if k in keys]
        ordered_keys.extend([k for k in keys if k not in ordered_keys])

        result = " | ".join(ordered_keys) + "\n"
        result += "-" * len(result) + "\n"

        for item in data:
            row = []
            for key in ordered_keys:
                value = item.get(key, "")
                row.append(str(value)[:30])
            result += " | ".join(row) + "\n"

        return result

    elif isinstance(data, dict):
        result = ""
        for key, value in data.items():
            if isinstance(value, dict):
                value = json.dumps(value, default=str)
            result += f"{key}: {value}\n"
        return result

    return str(data)


def handle_docker_command(args):
    """Handle Docker-related commands."""
    try:
        # Local-Compose MVP flow: runs without docker-py / GitHub credentials.
        if args.docker_command == "compose":
            return handle_compose_command(args)

        if not _LEGACY_DOCKER_AVAILABLE:
            print_error(
                "Legacy Docker deployment flow unavailable",
                "The 'docker' or 'agents' Python package is not installed.",
                "Use 'docker compose ...' (local project) or 'pip install docker agents'.",
            )
            return 1

        cred_manager = get_credential_manager()
        github_creds = cred_manager.get_github_credentials()

        deploy_svc = DockerDeployService()

        if args.docker_command == "deploy":
            env = {}
            if args.env:
                for pair in args.env.split(","):
                    if "=" in pair:
                        k, v = pair.split("=", 1)
                        env[k] = v

            from .docker_svc.models import DeployRequest

            request = DeployRequest(
                repository=args.repo,
                branch=args.branch,
                container_port=args.port,
                env=env,
            )

            deployment = deploy_svc.deploy_from_github(request, github_creds.token)

            print(f"{COLORS['green']}Deployed!{COLORS['reset']}")
            print(f"URL: {deployment.url}")
            print(f"Container: {deployment.container_name}")
            return 0

        elif args.docker_command == "list":
            deployments = deploy_svc.list_deployments()

            if not deployments:
                print(f"{COLORS['yellow']}No deployments found.{COLORS['reset']}")
            else:
                data = [
                    {
                        "id": d.id,
                        "repository": d.repository,
                        "branch": d.branch,
                        "url": d.url,
                        "status": d.status,
                    }
                    for d in deployments
                ]
                print(format_output(data, "table"))
            return 0

        elif args.docker_command == "logs":
            logs = deploy_svc.get_deployment_logs(args.deploy_id, args.tail)
            print(logs)
            return 0

        elif args.docker_command == "stop":
            deploy_svc.stop_deployment(args.deploy_id)
            print(
                f"{COLORS['green']}Stopped deployment {args.deploy_id}{COLORS['reset']}"
            )
            return 0

        elif args.docker_command == "start":
            deploy_svc.start_deployment(args.deploy_id)
            print(
                f"{COLORS['green']}Started deployment {args.deploy_id}{COLORS['reset']}"
            )
            return 0

        elif args.docker_command == "rm":
            deploy_svc.remove_deployment(args.deploy_id)
            print(
                f"{COLORS['green']}Removed deployment {args.deploy_id}{COLORS['reset']}"
            )
            return 0

        elif args.docker_command == "ps":
            docker_svc = DockerService()
            containers = docker_svc.list_containers(all=args.all)

            if not containers:
                print(f"{COLORS['yellow']}No containers found.{COLORS['reset']}")
            else:
                print(format_output(containers, "table"))
            return 0

        return 0

    except Exception as e:
        return handle_cli_error(e)


def _parse_env_list(pairs):
    """Parse a list of KEY=VALUE strings into a dict."""
    env = {}
    for pair in pairs or []:
        if "=" not in pair:
            raise ValueError(f"--env must be KEY=VALUE, got: {pair}")
        key, value = pair.split("=", 1)
        env[key.strip()] = value
    return env


def handle_compose_command(args):
    """Handle 'docker compose ...' local deployment commands."""
    try:
        if not args.compose_command:
            print_error(
                "Missing compose subcommand",
                suggestion="Try 'docker compose up --path ./myrepo'.",
            )
            return 1

        service = ComposeDeployService(skip_verification=False)

        if args.compose_command == "up":
            env = _parse_env_list(args.env)
            request = DeployLocalRequest(
                project_path=args.path,
                compose_file=args.compose_file,
                project_name=args.project,
                env=env,
                env_file=args.env_file,
                build=not args.no_build,
                pull=args.pull,
            )
            result = service.deploy(request)
            if result.status == "succeeded":
                print(
                    f"{COLORS['green']}Deployed {result.project_name} "
                    f"({len(result.services)} service(s)){COLORS['reset']}"
                )
            else:
                print(
                    f"{COLORS['red']}Deployment failed for {result.project_name}"
                    f"{COLORS['reset']}"
                )
            if result.agents_md_excerpt:
                print(f"\n{COLORS['cyan']}AGENTS.md (excerpt):{COLORS['reset']}")
                print(result.agents_md_excerpt)
            if result.services:
                print(f"\n{COLORS['cyan']}Services:{COLORS['reset']}")
                for svc in result.services:
                    print(
                        f"  - {svc.service:<20} {svc.state or svc.status:<20} "
                        f"{svc.name}"
                    )
            if result.output.strip():
                print(f"\n{COLORS['cyan']}Output:{COLORS['reset']}\n{result.output}")
            return 0 if result.status == "succeeded" else 1

        target = ComposeTargetRequest(
            project_path=args.path,
            compose_file=args.compose_file,
            project_name=args.project,
        )

        if args.compose_command == "down":
            output = service.down(target)
            print(f"{COLORS['green']}Brought down project{COLORS['reset']}")
            if output.strip():
                print(output)
            return 0

        if args.compose_command == "status":
            statuses = service.status(target)
            if not statuses:
                print(f"{COLORS['yellow']}No services running.{COLORS['reset']}")
                return 0
            data = [s.model_dump() for s in statuses]
            print(format_output(data, "table"))
            return 0

        if args.compose_command == "logs":
            logs_req = ComposeLogsRequest(
                project_path=args.path,
                compose_file=args.compose_file,
                project_name=args.project,
                service=args.service,
                tail=args.tail,
            )
            print(service.logs(logs_req))
            return 0

        return 0

    except Exception as e:  # noqa: BLE001 - surfaced via handle_cli_error
        return handle_cli_error(e)


def handle_github_command(args):
    """Handle GitHub-related commands."""
    try:
        cred_manager = get_credential_manager()
        github_creds = cred_manager.get_github_credentials()

        github = GitHubService(token=github_creds.token)

        if args.github_command == "list-repos":
            repos = github.list_repositories(org=args.org, user=args.user)

            if not repos:
                print(f"{COLORS['yellow']}No repositories found.{COLORS['reset']}")
            else:
                simplified = [
                    {
                        "Name": r["name"],
                        "FullName": r["full_name"],
                        "Stars": r.get("stargazers_count", 0),
                        "Language": r.get("language", ""),
                    }
                    for r in repos
                ]
                print(format_output(simplified, args.output))
            return 0

        elif args.github_command == "get-repo":
            repo = github.get_repository(args.repo, owner=args.owner)
            print(format_output(repo, "table"))
            return 0

        elif args.github_command == "get-readme":
            readme = github.get_readme(args.repo, owner=args.owner, ref=args.ref)
            if "decoded_content" in readme:
                print(readme["decoded_content"])
            else:
                print(format_output(readme, "json"))
            return 0

        elif args.github_command == "list-branches":
            branches = github.list_branches(args.repo, owner=args.owner)

            if not branches:
                print(f"{COLORS['yellow']}No branches found.{COLORS['reset']}")
            else:
                simplified = [
                    {"Name": b["name"], "SHA": b["commit"]["sha"][:7]} for b in branches
                ]
                print(format_output(simplified, "table"))
            return 0

        return 0

    except Exception as e:
        return handle_cli_error(e)


def handle_serve_command(args):
    """Handle serve command."""
    try:
        from .api.app import run

        print(
            f"{COLORS['green']}Starting API server on {args.host}:{args.port}...{COLORS['reset']}"
        )
        run(host=args.host, port=args.port, reload=args.reload)
    except Exception as e:
        return handle_cli_error(e)


def main():
    """Main entry point for the CLI."""
    try:
        parser = argparse.ArgumentParser(description="DevOps Agent CLI")
        parser.add_argument("--debug", action="store_true", help="Enable debug logging")

        subparsers = parser.add_subparsers(dest="command", help="Command group")

        setup_docker_parser(subparsers)
        setup_github_parser(subparsers)
        setup_serve_parser(subparsers)

        args = parser.parse_args()

        if args.debug:
            logging.getLogger().setLevel(logging.DEBUG)

        if not args.command:
            parser.print_help()
            sys.exit(1)

        if args.command == "docker":
            if not args.docker_command:
                parser.parse_args(["docker", "--help"])
                sys.exit(1)
            sys.exit(handle_docker_command(args))

        elif args.command == "github":
            if not args.github_command:
                parser.parse_args(["github", "--help"])
                sys.exit(1)
            sys.exit(handle_github_command(args))

        elif args.command == "serve":
            handle_serve_command(args)

        sys.exit(0)

    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(130)
    except Exception as e:
        print_error("Unexpected error", f"Error: {e}")
        if args and getattr(args, "debug", False):
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
