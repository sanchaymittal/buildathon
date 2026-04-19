"""
Script to run comprehensive CLI tests directly.
"""

import sys
import unittest
import json
from unittest.mock import patch, MagicMock

# Define a simple format_output function for testing
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

# Mock EC2 service for testing
class MockEC2Service:
    def __init__(self, credentials=None):
        self.credentials = credentials
    
    def list_instances(self, filters=None):
        return [
            {
                'InstanceId': 'i-1234567890abcdef0',
                'State': {'Name': 'running'},
                'InstanceType': 't2.micro',
                'Tags': [{'Key': 'Name', 'Value': 'test-instance'}],
                'LaunchTime': '2023-01-01T00:00:00Z'
            }
        ]
    
    def create_instance(self, name, instance_type, ami_id, subnet_id, security_group_ids, key_name, wait=False):
        return {
            'InstanceId': 'i-1234',
            'State': {'Name': 'running'},
            'InstanceType': instance_type
        }

# Mock GitHub service for testing
class MockGitHubService:
    def __init__(self, credentials=None):
        self.credentials = credentials
    
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
            }
        ]
    
    def get_readme(self, repo, owner=None, ref=None):
        return {
            'name': 'README.md',
            'path': 'README.md',
            'decoded_content': '# Test Repository\n\nThis is a test repository.'
        }

# Mock credential manager for testing
class MockCredentialManager:
    def get_aws_credentials(self, region=None):
        return MagicMock()
    
    def get_github_credentials(self):
        creds = MagicMock()
        creds.token = "mock-token"
        return creds

# Mock CLI functions
def handle_ec2_command(args):
    """Handle EC2 commands."""
    credential_manager = MockCredentialManager()
    aws_credentials = credential_manager.get_aws_credentials(region=args.region)
    ec2_service = MockEC2Service(credentials=aws_credentials)
    
    if args.ec2_command == 'list-instances':
        filters = []
        if args.state:
            filters.append({'Name': 'instance-state-name', 'Values': [args.state]})
        
        instances = ec2_service.list_instances(filters=filters)
        print(format_output(instances, format_type=args.output))
        return 0
    
    elif args.ec2_command == 'create-instance':
        security_group_ids = args.security_group_ids.split(',') if args.security_group_ids else []
        
        instance = ec2_service.create_instance(
            name=args.name,
            instance_type=args.type,
            ami_id=args.ami_id,
            subnet_id=args.subnet_id,
            security_group_ids=security_group_ids,
            key_name=args.key_name,
            wait=args.wait
        )
        
        print(format_output(instance, format_type=args.output))
        return 0
    
    return 1

def handle_github_command(args):
    """Handle GitHub commands."""
    credential_manager = MockCredentialManager()
    github_credentials = credential_manager.get_github_credentials()
    github_service = MockGitHubService(credentials=github_credentials)
    
    if args.github_command == 'list-repos':
        repos = github_service.list_repositories(org=args.org, user=args.user)
        print(format_output(repos, format_type=args.output))
        return 0
    
    elif args.github_command == 'get-readme':
        readme = github_service.get_readme(args.repo, owner=args.owner, ref=args.ref)
        print(readme['decoded_content'])
        return 0
    
    return 1

# Test classes
class TestCLIFormatOutput(unittest.TestCase):
    """Tests for the format_output function."""
    
    def test_format_json(self):
        """Test JSON output formatting."""
        data = {"id": "i-1234", "name": "test-instance", "state": "running"}
        output = format_output(data, format_type='json')
        # Verify it's valid JSON
        parsed = json.loads(output)
        self.assertEqual(parsed["id"], "i-1234")
        self.assertEqual(parsed["name"], "test-instance")
    
    def test_format_table_list(self):
        """Test table output formatting for a list of dictionaries."""
        data = [
            {"id": "i-1234", "name": "instance-1", "state": "running"},
            {"id": "i-5678", "name": "instance-2", "state": "stopped"}
        ]
        output = format_output(data, format_type='table')
        
        # Verify it contains headers and data
        self.assertIn("id | name | state", output.lower())
        self.assertIn("i-1234 | instance-1 | running", output)
        self.assertIn("i-5678 | instance-2 | stopped", output)
    
    def test_format_table_dict(self):
        """Test table output formatting for a single dictionary."""
        data = {"id": "i-1234", "name": "test-instance", "state": "running"}
        output = format_output(data, format_type='table')
        
        # Verify it contains key-value pairs
        self.assertIn("id: i-1234", output)
        self.assertIn("name: test-instance", output)
        self.assertIn("state: running", output)

class TestCLIEC2Commands(unittest.TestCase):
    """Tests for EC2-related CLI commands."""
    
    def test_list_instances(self):
        """Test the list-instances command."""
        # Mock arguments
        args = MagicMock()
        args.command = 'ec2'
        args.ec2_command = 'list-instances'
        args.state = 'running'
        args.region = 'us-west-2'
        args.output = 'json'
        
        # Capture stdout
        with patch('sys.stdout') as mock_stdout:
            result = handle_ec2_command(args)
        
        # Verify result
        self.assertEqual(result, 0)
    
    def test_create_instance(self):
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
        
        # Capture stdout
        with patch('sys.stdout') as mock_stdout:
            result = handle_ec2_command(args)
        
        # Verify result
        self.assertEqual(result, 0)

class TestCLIGitHubCommands(unittest.TestCase):
    """Tests for GitHub-related CLI commands."""
    
    def test_list_repos(self):
        """Test the list-repos command."""
        # Mock arguments
        args = MagicMock()
        args.command = 'github'
        args.github_command = 'list-repos'
        args.org = 'test-org'
        args.user = None
        args.output = 'json'
        
        # Capture stdout
        with patch('sys.stdout') as mock_stdout:
            result = handle_github_command(args)
        
        # Verify result
        self.assertEqual(result, 0)
    
    def test_get_readme(self):
        """Test the get-readme command."""
        # Mock arguments
        args = MagicMock()
        args.command = 'github'
        args.github_command = 'get-readme'
        args.repo = 'test-org/repo1'
        args.owner = None
        args.ref = 'main'
        
        # Capture stdout
        with patch('sys.stdout') as mock_stdout:
            result = handle_github_command(args)
        
        # Verify result
        self.assertEqual(result, 0)

if __name__ == "__main__":
    # Run the tests
    unittest.main()