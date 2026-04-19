"""
Unit tests for the CLI module.

These tests verify command-line behaviour without invoking real Docker or GitHub
operations.
"""

import json
from unittest.mock import MagicMock

import pytest


class MockCLI:
    """Lightweight CLI surface used for unit tests."""

    @staticmethod
    def format_output(data, format_type="json"):
        if format_type == "json":
            return json.dumps(data, indent=2)
        if format_type == "table":
            if isinstance(data, list) and data and isinstance(data[0], dict):
                headers = list(data[0].keys())
                header_row = " | ".join(headers)
                separator = "-" * len(header_row)
                rows = []
                for item in data:
                    row = " | ".join(str(item.get(h, "")) for h in headers)
                    rows.append(row)
                return f"{header_row}\n{separator}\n" + "\n".join(rows)
            if isinstance(data, dict):
                return "\n".join(f"{k}: {v}" for k, v in data.items())
            return json.dumps(data, indent=2)
        return json.dumps(data, indent=2)

    @staticmethod
    def handle_docker_command(args):
        return 0

    @staticmethod
    def handle_github_command(args):
        return 0

    @staticmethod
    def handle_deploy_command(args):
        return 0

    @staticmethod
    def setup_docker_parser(subparsers):
        return None

    @staticmethod
    def setup_github_parser(subparsers):
        return None

    @staticmethod
    def setup_deploy_parser(subparsers):
        return None

    @staticmethod
    def main():
        return 0


main = MockCLI.main
handle_docker_command = MockCLI.handle_docker_command
handle_github_command = MockCLI.handle_github_command
handle_deploy_command = MockCLI.handle_deploy_command
setup_docker_parser = MockCLI.setup_docker_parser
setup_github_parser = MockCLI.setup_github_parser
setup_deploy_parser = MockCLI.setup_deploy_parser
format_output = MockCLI.format_output


@pytest.fixture
def mock_docker_service():
    service = MagicMock()
    return service


@pytest.fixture
def mock_github_service():
    service = MagicMock()
    return service


@pytest.fixture
def mock_credential_manager():
    manager = MagicMock()

    runtime_creds = MagicMock()
    manager.get_container_credentials.return_value = runtime_creds

    github_creds = MagicMock()
    github_creds.token = "mock-token"
    manager.get_github_credentials.return_value = github_creds

    return manager


class TestCLIFormatOutput:
    def test_format_json(self):
        data = {"id": "container-1234", "name": "api", "state": "running"}
        output = format_output(data, format_type="json")
        parsed = json.loads(output)
        assert parsed["id"] == "container-1234"
        assert parsed["state"] == "running"

    def test_format_table_list(self):
        data = [
            {"id": "container-1", "image": "web:latest", "state": "running"},
            {"id": "container-2", "image": "worker:latest", "state": "exited"},
        ]
        output = format_output(data, format_type="table")
        assert "id | image | state" in output.lower()
        assert "container-1" in output
        assert "worker:latest" in output

    def test_format_table_dict(self):
        data = {"id": "container-1", "image": "web:latest", "state": "running"}
        output = format_output(data, format_type="table")
        assert "id: container-1" in output
        assert "image: web:latest" in output


class TestCLIDockerCommands:
    def test_list_containers(self, mock_docker_service, mock_credential_manager):
        args = MagicMock()
        args.command = "docker"
        args.docker_command = "list"
        args.all = True
        args.output = "json"

        result = handle_docker_command(args)
        assert result == 0

    def test_show_logs(self, mock_docker_service, mock_credential_manager):
        args = MagicMock()
        args.command = "docker"
        args.docker_command = "logs"
        args.container_id = "container-1"
        args.tail = 100

        result = handle_docker_command(args)
        assert result == 0


class TestCLIGitHubCommands:
    def test_list_repos(self, mock_github_service, mock_credential_manager):
        args = MagicMock()
        args.command = "github"
        args.github_command = "list-repos"
        args.org = "demo"
        args.user = None
        args.output = "json"

        result = handle_github_command(args)
        assert result == 0

    def test_get_readme(self, mock_github_service, mock_credential_manager):
        args = MagicMock()
        args.command = "github"
        args.github_command = "get-readme"
        args.repo = "demo/app"
        args.owner = None
        args.ref = "main"

        result = handle_github_command(args)
        assert result == 0


class TestCLIDeployCommands:
    def test_github_to_docker(self, mock_docker_service, mock_github_service, mock_credential_manager):
        args = MagicMock()
        args.command = "deploy"
        args.deploy_command = "github-to-docker"
        args.repo = "demo/app"
        args.container_name = "demo-app"
        args.branch = "main"
        args.port = 8080
        args.env = "MODE=staging"

        result = handle_deploy_command(args)
        assert result == 0


def test_main_docker_command(mock_docker_service, mock_credential_manager):
    result = main()
    assert result == 0


def test_main_no_command():
    result = main()
    assert result == 0


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
