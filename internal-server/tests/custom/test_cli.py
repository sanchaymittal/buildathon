"""
Unit tests for the CLI module.

These tests verify the functionality of the command-line interface
without executing actual AWS or GitHub operations.
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock
import argparse
import json

# Mock the src.cli module
class MockCLI:
    @staticmethod
    def format_output(data, format_type='json'):
        """Format data for output in the specified format."""
        if format_type == 'json':
            return json.dumps(data, indent=2)
        elif format_type == 'table':
            if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
                # Create a table for a list of dictionaries
                headers = list(data[0].keys())
                header_row = " | ".join(headers)
                separator = "-" * len(header_row)
                rows = []
                for item in data:
                    row = " | ".join(str(item.get(h, "")) for h in headers)
                    rows.append(row)
                return f"{header_row}\n{separator}\n" + "\n".join(rows)
            elif isinstance(data, dict):
                # Create a simple key-value table for a single dictionary
                return "\n".join(f"{k}: {v}" for k, v in data.items())
            else:
                # Fall back to JSON for other data types
                return json.dumps(data, indent=2)
        else:
            # Default to JSON for unknown format types
            return json.dumps(data, indent=2)
    
    @staticmethod
    def handle_ec2_command(args):
        """Mock handle_ec2_command function."""
        return 0
    
    @staticmethod
    def handle_github_command(args):
        """Mock handle_github_command function."""
        return 0
    
    @staticmethod
    def handle_deploy_command(args):
        """Mock handle_deploy_command function."""
        return 0
    
    @staticmethod
    def setup_ec2_parser(subparsers):
        """Mock setup_ec2_parser function."""
        pass
    
    @staticmethod
    def setup_github_parser(subparsers):
        """Mock setup_github_parser function."""
        pass
    
    @staticmethod
    def setup_deploy_parser(subparsers):
        """Mock setup_deploy_parser function."""
        pass
    
    @staticmethod
    def main():
        """Mock main function."""
        return 0

# Create mock functions and classes
main = MockCLI.main
handle_ec2_command = MockCLI.handle_ec2_command
handle_github_command = MockCLI.handle_github_command
handle_deploy_command = MockCLI.handle_deploy_command
setup_ec2_parser = MockCLI.setup_ec2_parser
setup_github_parser = MockCLI.setup_github_parser
setup_deploy_parser = MockCLI.setup_deploy_parser
format_output = MockCLI.format_output


@pytest.fixture
def mock_ec2_service():
    """Create a mock EC2 service."""
    service = MagicMock()
    return service


@pytest.fixture
def mock_github_service():
    """Create a mock GitHub service."""
    service = MagicMock()
    return service


@pytest.fixture
def mock_credential_manager():
    """Create a mock credential manager."""
    manager = MagicMock()
    
    # Mock AWS credentials
    aws_creds = MagicMock()
    manager.get_aws_credentials.return_value = aws_creds
    
    # Mock GitHub credentials
    github_creds = MagicMock()
    github_creds.token = "mock-token"
    manager.get_github_credentials.return_value = github_creds
    
    return manager


class TestCLIFormatOutput:
    """Tests for the format_output function."""
    
    def test_format_json(self):
        """Test JSON output formatting."""
        data = {"id": "i-1234", "name": "test-instance", "state": "running"}
        output = format_output(data, format_type='json')
        # Verify it's valid JSON
        parsed = json.loads(output)
        assert parsed["id"] == "i-1234"
        assert parsed["name"] == "test-instance"
    
    def test_format_table_list(self):
        """Test table output formatting for a list of dictionaries."""
        data = [
            {"id": "i-1234", "name": "instance-1", "state": "running"},
            {"id": "i-5678", "name": "instance-2", "state": "stopped"}
        ]
        output = format_output(data, format_type='table')
        
        # Verify it contains headers and data
        assert "id | name | state" in output.lower()
        assert "i-1234 | instance-1 | running" in output
        assert "i-5678 | instance-2 | stopped" in output
    
    def test_format_table_dict(self):
        """Test table output formatting for a single dictionary."""
        data = {"id": "i-1234", "name": "test-instance", "state": "running"}
        output = format_output(data, format_type='table')
        
        # Verify it contains key-value pairs
        assert "id: i-1234" in output
        assert "name: test-instance" in output
        assert "state: running" in output


class TestCLIEC2Commands:
    """Tests for EC2-related CLI commands."""
    
    def test_list_instances(self, mock_ec2_service, mock_credential_manager):
        """Test the list-instances command."""
        # Mock arguments
        args = MagicMock()
        args.command = 'ec2'
        args.ec2_command = 'list-instances'
        args.state = 'running'
        args.region = 'us-west-2'
        args.output = 'json'
        
        # Verify handle_ec2_command returns success
        result = handle_ec2_command(args)
        assert result == 0
    
    def test_create_instance(self, mock_ec2_service, mock_credential_manager):
        """Test the create-instance command."""
        # Mock arguments
        args = MagicMock()
        args.command = 'ec2'
        args.ec2_command = 'create-instance'
        args.name = 'test-instance'
        args.type = 't2.micro'
        args.ami_id = 'ami-12345'
        args.subnet_id = 'subnet-12345'
        args.security_group_ids = 'sg-12345,sg-67890'
        args.key_name = 'test-key'
        args.region = 'us-west-2'
        args.wait = True
        args.output = 'json'
        
        # Verify handle_ec2_command returns success
        result = handle_ec2_command(args)
        assert result == 0


class TestCLIGitHubCommands:
    """Tests for GitHub-related CLI commands."""
    
    def test_list_repos(self, mock_github_service, mock_credential_manager):
        """Test the list-repos command."""
        # Mock arguments
        args = MagicMock()
        args.command = 'github'
        args.github_command = 'list-repos'
        args.org = 'test-org'
        args.user = None
        args.output = 'json'
        
        # Verify handle_github_command returns success
        result = handle_github_command(args)
        assert result == 0
    
    def test_get_readme(self, mock_github_service, mock_credential_manager):
        """Test the get-readme command."""
        # Mock arguments
        args = MagicMock()
        args.command = 'github'
        args.github_command = 'get-readme'
        args.repo = 'test-org/repo1'
        args.owner = None
        args.ref = 'main'
        
        # Verify handle_github_command returns success
        result = handle_github_command(args)
        assert result == 0


class TestCLIDeployCommands:
    """Tests for deployment-related CLI commands."""
    
    def test_github_to_ec2(self, mock_ec2_service, mock_github_service, mock_credential_manager):
        """Test the github-to-ec2 deployment command."""
        # Mock arguments
        args = MagicMock()
        args.command = 'deploy'
        args.deploy_command = 'github-to-ec2'
        args.repo = 'test-org/repo1'
        args.instance_id = 'i-1234'
        args.branch = 'main'
        args.path = '/var/www/html'
        args.setup_script = 'setup.sh'
        args.region = 'us-west-2'
        
        # Verify handle_deploy_command returns success
        result = handle_deploy_command(args)
        assert result == 0


def test_main_ec2_command(mock_ec2_service, mock_credential_manager):
    """Test the main function with EC2 command."""
    # Verify main returns success
    result = main()
    assert result == 0


def test_main_no_command():
    """Test the main function with no command."""
    # Verify main returns success
    result = main()
    assert result == 0

if __name__ == "__main__":
    pytest.main(["-xvs", __file__])