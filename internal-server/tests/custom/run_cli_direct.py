"""
Script to run the CLI directly with mocked dependencies.
"""

import sys
import os
import argparse
import json
from unittest.mock import MagicMock

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

# Mock the agents module and other dependencies
sys.modules['agents'] = MagicMock()
sys.modules['agents.types'] = MagicMock()
sys.modules['agents.types'].RunContext = MagicMock()

# Create mock classes for missing dependencies
class ConfigError(Exception):
    """Mock ConfigError class."""
    pass

class CredentialError(Exception):
    """Mock CredentialError class."""
    pass

class AWSServiceError(Exception):
    """Mock AWSServiceError class."""
    pass

class ResourceNotFoundError(AWSServiceError):
    """Mock ResourceNotFoundError class."""
    pass

class PermissionDeniedError(AWSServiceError):
    """Mock PermissionDeniedError class."""
    pass

class ValidationError(AWSServiceError):
    """Mock ValidationError class."""
    pass

class RateLimitError(AWSServiceError):
    """Mock RateLimitError class."""
    pass

class ResourceLimitError(AWSServiceError):
    """Mock ResourceLimitError class."""
    pass

class GitHubError(Exception):
    """Mock GitHubError class."""
    pass

class AuthenticationError(GitHubError):
    """Mock AuthenticationError class."""
    pass

# Mock AWS and GitHub services
class MockEC2Service:
    def __init__(self, credentials=None):
        self.credentials = credentials
    
    def list_instances(self, filters=None):
        instances = [
            {
                'InstanceId': 'i-1234567890abcdef0',
                'InstanceType': 't2.micro',
                'State': {'Name': 'running'},
                'Tags': [{'Key': 'Name', 'Value': 'Test Instance'}],
                'LaunchTime': '2023-01-01T00:00:00Z'
            },
            {
                'InstanceId': 'i-0987654321fedcba0',
                'InstanceType': 't3.small',
                'State': {'Name': 'stopped'},
                'Tags': [{'Key': 'Name', 'Value': 'Dev Server'}],
                'LaunchTime': '2023-02-15T12:30:00Z'
            }
        ]
        
        # Apply filters if provided
        if filters:
            filtered_instances = []
            for instance in instances:
                match = True
                for filter_item in filters:
                    if filter_item['Name'] == 'instance-state-name':
                        if instance['State']['Name'] not in filter_item['Values']:
                            match = False
                            break
                if match:
                    filtered_instances.append(instance)
            return filtered_instances
        
        return instances
    
    def get_instance(self, instance_id):
        if instance_id == 'i-1234567890abcdef0':
            return {
                'InstanceId': 'i-1234567890abcdef0',
                'InstanceType': 't2.micro',
                'State': {'Name': 'running'},
                'PublicIpAddress': '54.123.45.67',
                'PrivateIpAddress': '10.0.0.123',
                'Tags': [{'Key': 'Name', 'Value': 'Test Instance'}],
                'LaunchTime': '2023-01-01T00:00:00Z'
            }
        elif instance_id == 'i-0987654321fedcba0':
            return {
                'InstanceId': 'i-0987654321fedcba0',
                'InstanceType': 't3.small',
                'State': {'Name': 'stopped'},
                'PrivateIpAddress': '10.0.0.124',
                'Tags': [{'Key': 'Name', 'Value': 'Dev Server'}],
                'LaunchTime': '2023-02-15T12:30:00Z'
            }
        else:
            raise ResourceNotFoundError(f"Instance {instance_id} not found")
    
    def create_instance(self, name, instance_type, ami_id, subnet_id=None, 
                       security_group_ids=None, key_name=None, wait=False):
        return {
            'InstanceId': 'i-newinstance12345',
            'InstanceType': instance_type,
            'State': {'Name': 'pending'},
            'Tags': [{'Key': 'Name', 'Value': name}]
        }
    
    def start_instance(self, instance_id, wait=False):
        return {'InstanceId': instance_id, 'State': {'Name': 'pending'}}
    
    def stop_instance(self, instance_id, force=False, wait=False):
        return {'InstanceId': instance_id, 'State': {'Name': 'stopping'}}
    
    def terminate_instance(self, instance_id, wait=False):
        return {'InstanceId': instance_id, 'State': {'Name': 'shutting-down'}}
    
    def deploy_from_github(self, instance_id, repository, branch='main', 
                          deploy_path='/var/www/html', setup_script=None, github_token=None):
        return {
            'status': 'success',
            'instance_id': instance_id,
            'repository': repository,
            'branch': branch,
            'deploy_path': deploy_path,
            'output': 'Deployment completed successfully'
        }

class MockGitHubService:
    def __init__(self, token=None):
        self.token = token
    
    def list_repositories(self, org=None, user=None):
        return [
            {
                'name': 'repo1',
                'full_name': 'test-org/repo1',
                'description': 'Test repository 1',
                'default_branch': 'main',
                'stargazers_count': 10,
                'forks_count': 5,
                'language': 'Python'
            },
            {
                'name': 'repo2',
                'full_name': 'test-org/repo2',
                'description': 'Test repository 2',
                'default_branch': 'master',
                'stargazers_count': 15,
                'forks_count': 8,
                'language': 'JavaScript'
            }
        ]
    
    def get_repository(self, repo, owner=None):
        if '/' in repo and not owner:
            owner, repo = repo.split('/')
        
        return {
            'name': repo,
            'full_name': f"{owner}/{repo}",
            'description': 'Test repository',
            'default_branch': 'main',
            'stargazers_count': 10,
            'forks_count': 5,
            'language': 'Python',
            'html_url': f"https://github.com/{owner}/{repo}"
        }
    
    def get_readme(self, repo, owner=None, ref=None):
        if '/' in repo and not owner:
            owner, repo = repo.split('/')
        
        return {
            'name': 'README.md',
            'path': 'README.md',
            'decoded_content': f"# {repo}\n\nThis is a test repository README file."
        }
    
    def list_branches(self, repo, owner=None):
        if '/' in repo and not owner:
            owner, repo = repo.split('/')
        
        return [
            {
                'name': 'main',
                'commit': {'sha': '1234567890abcdef'},
                'protected': True
            },
            {
                'name': 'develop',
                'commit': {'sha': 'abcdef1234567890'},
                'protected': False
            }
        ]

# Mock credential manager
class MockCredentialManager:
    def get_aws_credentials(self, region=None):
        creds = MagicMock()
        creds.access_key_id = "mock-access-key"
        creds.secret_access_key = "mock-secret-key"
        creds.region = region or "us-west-2"
        return creds
    
    def get_github_credentials(self):
        creds = MagicMock()
        creds.token = "mock-token"
        return creds

# Mock config functions
def mock_get_config():
    return {
        "aws": {
            "region": "us-west-2",
            "profile": None,
            "tags": {
                "ManagedBy": "DevOpsAgent"
            }
        },
        "github": {
            "organization": "test-org",
            "api_url": "https://api.github.com"
        },
        "logging": {
            "level": "INFO",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        }
    }

# Patch the modules
sys.modules['devops.src.core.config'] = MagicMock()
sys.modules['devops.src.core.config'].get_config = mock_get_config
sys.modules['devops.src.core.config'].ConfigError = ConfigError

sys.modules['devops.src.core.credentials'] = MagicMock()
sys.modules['devops.src.core.credentials'].get_credential_manager = lambda: MockCredentialManager()
sys.modules['devops.src.core.credentials'].CredentialError = CredentialError

sys.modules['devops.src.aws.base'] = MagicMock()
sys.modules['devops.src.aws.base'].AWSServiceError = AWSServiceError
sys.modules['devops.src.aws.base'].ResourceNotFoundError = ResourceNotFoundError
sys.modules['devops.src.aws.base'].PermissionDeniedError = PermissionDeniedError
sys.modules['devops.src.aws.base'].ValidationError = ValidationError
sys.modules['devops.src.aws.base'].RateLimitError = RateLimitError
sys.modules['devops.src.aws.base'].ResourceLimitError = ResourceLimitError

sys.modules['devops.src.aws.ec2'] = MagicMock()
sys.modules['devops.src.aws.ec2'].EC2Service = MockEC2Service

sys.modules['devops.src.github.github'] = MagicMock()
sys.modules['devops.src.github.github'].GitHubService = MockGitHubService
sys.modules['devops.src.github.github'].GitHubError = GitHubError
sys.modules['devops.src.github.github'].AuthenticationError = AuthenticationError

# Import the CLI module
from devops.src.cli import main

if __name__ == "__main__":
    # If arguments are provided, use them, otherwise use default test arguments
    if len(sys.argv) > 1:
        main()
    else:
        # Run with default test arguments
        test_commands = [
            ["ec2", "list-instances", "--output", "table"],
            ["ec2", "list-instances", "--state", "running", "--output", "table"],
            ["ec2", "get-instance", "i-1234567890abcdef0", "--output", "json"],
            ["ec2", "create-instance", "--name", "New Server", "--type", "t2.micro", "--ami-id", "ami-12345678"],
            ["github", "list-repos", "--org", "test-org", "--output", "table"],
            ["github", "get-repo", "test-org/repo1", "--output", "json"],
            ["github", "get-readme", "test-org/repo1"],
            ["github", "list-branches", "test-org/repo1", "--output", "table"],
            ["deploy", "github-to-ec2", "--repo", "test-org/repo1", "--instance-id", "i-1234567890abcdef0"]
        ]
        
        print("=== Running CLI with test commands ===\n")
        for cmd in test_commands:
            print(f"\n=== Command: {' '.join(cmd)} ===")
            sys.argv = ["cli.py"] + cmd
            try:
                main()
            except SystemExit:
                pass  # Ignore SystemExit
            except Exception as e:
                print(f"Error: {e}")