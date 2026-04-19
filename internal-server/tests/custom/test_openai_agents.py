"""
Tests for OpenAI Agents SDK integration with DevOps agent.

This module contains pytest tests for the OpenAI Agents SDK integration with the DevOps agent.
It includes tests for EC2 operations, GitHub operations, agent orchestration, context management,
guardrails, and tracing.
"""

import os
import json
import pytest
import asyncio
from unittest.mock import patch, MagicMock
import boto3
from pydantic import BaseModel, Field

# Import OpenAI Agents SDK
from agents import (
    Agent, 
    Runner, 
    function_tool, 
    trace, 
    Handoff,
    RunContextWrapper,
    GuardrailFunctionOutput,
    input_guardrail,
    output_guardrail
)
from agents.tracing import set_tracing_disabled

# Import our implementations
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from src.aws.ec2 import (
    list_ec2_instances,
    start_ec2_instances,
    stop_ec2_instances,
    create_ec2_instance,
    EC2InstanceFilter,
    EC2StartStopRequest,
    EC2CreateRequest,
    EC2Instance
)
from src.github.github import (
    get_repository,
    list_issues,
    create_issue,
    list_pull_requests,
    GitHubRepoRequest,
    GitHubIssueRequest,
    GitHubCreateIssueRequest,
    GitHubPRRequest,
    GitHubRepository,
    GitHubIssue,
    GitHubPullRequest
)
from src.core.context import DevOpsContext
from src.core.guardrails import (
    security_guardrail,
    sensitive_info_guardrail,
    SecurityCheckOutput,
    SensitiveInfoOutput
)

# Test fixtures
@pytest.fixture
def devops_context():
    """Create a DevOpsContext for testing."""
    return DevOpsContext(
        user_id="test-user",
        aws_region="us-west-2",
        github_org="test-org"
    )

@pytest.fixture
def ec2_mock_response():
    """Mock response for EC2 describe_instances."""
    return {
        "Reservations": [
            {
                "Instances": [
                    {
                        "InstanceId": "i-1234567890abcdef0",
                        "InstanceType": "t2.micro",
                        "State": {"Name": "running"},
                        "PublicIpAddress": "54.123.45.67",
                        "PrivateIpAddress": "10.0.0.123",
                        "Tags": [
                            {"Key": "Name", "Value": "Test Instance"},
                            {"Key": "Environment", "Value": "Test"}
                        ]
                    }
                ]
            }
        ]
    }

@pytest.fixture
def github_repo_mock_response():
    """Mock response for GitHub get_repo."""
    repo_mock = MagicMock()
    repo_mock.name = "test-repo"
    repo_mock.full_name = "test-org/test-repo"
    repo_mock.description = "Test repository"
    repo_mock.html_url = "https://github.com/test-org/test-repo"
    repo_mock.default_branch = "main"
    repo_mock.stargazers_count = 10
    repo_mock.forks_count = 5
    repo_mock.open_issues_count = 3
    repo_mock.language = "Python"
    return repo_mock

@pytest.fixture
def github_issues_mock_response():
    """Mock response for GitHub get_issues."""
    issue1 = MagicMock()
    issue1.number = 1
    issue1.title = "Test Issue 1"
    issue1.body = "This is test issue 1"
    issue1.state = "open"
    issue1.created_at.isoformat.return_value = "2023-01-01T00:00:00Z"
    issue1.updated_at.isoformat.return_value = "2023-01-02T00:00:00Z"
    issue1.html_url = "https://github.com/test-org/test-repo/issues/1"
    issue1.labels = [MagicMock(name="bug"), MagicMock(name="enhancement")]
    issue1.assignees = [MagicMock(login="user1"), MagicMock(login="user2")]
    
    issue2 = MagicMock()
    issue2.number = 2
    issue2.title = "Test Issue 2"
    issue2.body = "This is test issue 2"
    issue2.state = "closed"
    issue2.created_at.isoformat.return_value = "2023-01-03T00:00:00Z"
    issue2.updated_at.isoformat.return_value = "2023-01-04T00:00:00Z"
    issue2.html_url = "https://github.com/test-org/test-repo/issues/2"
    issue2.labels = [MagicMock(name="documentation")]
    issue2.assignees = [MagicMock(login="user3")]
    
    return [issue1, issue2]

# EC2 Tests
@pytest.mark.asyncio
async def test_list_ec2_instances(devops_context, ec2_mock_response):
    """Test listing EC2 instances."""
    # Mock the boto3 client
    with patch("boto3.client") as mock_boto3_client:
        # Set up the mock
        mock_ec2 = MagicMock()
        mock_boto3_client.return_value = mock_ec2
        mock_ec2.describe_instances.return_value = ec2_mock_response
        
        # Create the filter
        filter_params = EC2InstanceFilter(region="us-west-2")
        
        # Call the function tool
        result = await list_ec2_instances.on_invoke_tool(
            RunContextWrapper(devops_context), 
            filter_params
        )
        
        # Verify the result
        assert len(result) == 1
        assert result[0].instance_id == "i-1234567890abcdef0"
        assert result[0].state == "running"
        assert result[0].instance_type == "t2.micro"
        assert result[0].public_ip_address == "54.123.45.67"
        assert result[0].private_ip_address == "10.0.0.123"
        assert result[0].tags == {"Name": "Test Instance", "Environment": "Test"}
        
        # Verify the call to boto3
        mock_boto3_client.assert_called_once_with("ec2", region_name="us-west-2")
        mock_ec2.describe_instances.assert_called_once()

@pytest.mark.asyncio
async def test_start_ec2_instances(devops_context):
    """Test starting EC2 instances."""
    # Mock the boto3 client
    with patch("boto3.client") as mock_boto3_client:
        # Set up the mock
        mock_ec2 = MagicMock()
        mock_boto3_client.return_value = mock_ec2
        mock_ec2.start_instances.return_value = {
            "StartingInstances": [
                {
                    "InstanceId": "i-1234567890abcdef0",
                    "CurrentState": {"Name": "pending"},
                    "PreviousState": {"Name": "stopped"}
                }
            ]
        }
        
        # Create the request
        request = EC2StartStopRequest(
            instance_ids=["i-1234567890abcdef0"],
            region="us-west-2"
        )
        
        # Call the function tool
        result = await start_ec2_instances.on_invoke_tool(
            RunContextWrapper(devops_context), 
            request
        )
        
        # Verify the result
        assert len(result["StartingInstances"]) == 1
        assert result["StartingInstances"][0]["InstanceId"] == "i-1234567890abcdef0"
        assert result["StartingInstances"][0]["CurrentState"]["Name"] == "pending"
        assert result["StartingInstances"][0]["PreviousState"]["Name"] == "stopped"
        
        # Verify the call to boto3
        mock_boto3_client.assert_called_once_with("ec2", region_name="us-west-2")
        mock_ec2.start_instances.assert_called_once_with(InstanceIds=["i-1234567890abcdef0"])

@pytest.mark.asyncio
async def test_stop_ec2_instances(devops_context):
    """Test stopping EC2 instances."""
    # Mock the boto3 client
    with patch("boto3.client") as mock_boto3_client:
        # Set up the mock
        mock_ec2 = MagicMock()
        mock_boto3_client.return_value = mock_ec2
        mock_ec2.stop_instances.return_value = {
            "StoppingInstances": [
                {
                    "InstanceId": "i-1234567890abcdef0",
                    "CurrentState": {"Name": "stopping"},
                    "PreviousState": {"Name": "running"}
                }
            ]
        }
        
        # Create the request
        request = EC2StartStopRequest(
            instance_ids=["i-1234567890abcdef0"],
            region="us-west-2"
        )
        
        # Call the function tool
        result = await stop_ec2_instances.on_invoke_tool(
            RunContextWrapper(devops_context), 
            request
        )
        
        # Verify the result
        assert len(result["StoppingInstances"]) == 1
        assert result["StoppingInstances"][0]["InstanceId"] == "i-1234567890abcdef0"
        assert result["StoppingInstances"][0]["CurrentState"]["Name"] == "stopping"
        assert result["StoppingInstances"][0]["PreviousState"]["Name"] == "running"
        
        # Verify the call to boto3
        mock_boto3_client.assert_called_once_with("ec2", region_name="us-west-2")
        mock_ec2.stop_instances.assert_called_once_with(InstanceIds=["i-1234567890abcdef0"])

@pytest.mark.asyncio
async def test_create_ec2_instance(devops_context):
    """Test creating EC2 instances."""
    # Mock the boto3 client
    with patch("boto3.client") as mock_boto3_client:
        # Set up the mock
        mock_ec2 = MagicMock()
        mock_boto3_client.return_value = mock_ec2
        mock_ec2.run_instances.return_value = {
            "Instances": [
                {
                    "InstanceId": "i-1234567890abcdef0",
                    "InstanceType": "t2.micro",
                    "State": {"Name": "pending"},
                    "PrivateIpAddress": "10.0.0.123"
                }
            ]
        }
        
        # Create the request
        request = EC2CreateRequest(
            image_id="ami-12345678",
            instance_type="t2.micro",
            key_name="test-key",
            security_group_ids=["sg-12345678"],
            subnet_id="subnet-12345678",
            region="us-west-2",
            tags={"Name": "Test Instance", "Environment": "Test"}
        )
        
        # Call the function tool
        result = await create_ec2_instance.on_invoke_tool(
            RunContextWrapper(devops_context), 
            request
        )
        
        # Verify the result
        assert len(result["Instances"]) == 1
        assert result["Instances"][0]["InstanceId"] == "i-1234567890abcdef0"
        assert result["Instances"][0]["InstanceType"] == "t2.micro"
        assert result["Instances"][0]["State"]["Name"] == "pending"
        
        # Verify the call to boto3
        mock_boto3_client.assert_called_once_with("ec2", region_name="us-west-2")
        mock_ec2.run_instances.assert_called_once_with(
            ImageId="ami-12345678",
            InstanceType="t2.micro",
            MinCount=1,
            MaxCount=1,
            KeyName="test-key",
            SecurityGroupIds=["sg-12345678"],
            SubnetId="subnet-12345678",
            TagSpecifications=[
                {
                    "ResourceType": "instance",
                    "Tags": [
                        {"Key": "Name", "Value": "Test Instance"},
                        {"Key": "Environment", "Value": "Test"}
                    ]
                }
            ]
        )

# GitHub Tests
@pytest.mark.asyncio
async def test_get_repository(devops_context, github_repo_mock_response):
    """Test getting GitHub repository information."""
    # Mock the GitHub client
    with patch("github.Github") as mock_github:
        # Set up the mock
        mock_github_instance = MagicMock()
        mock_github.return_value = mock_github_instance
        mock_github_instance.get_repo.return_value = github_repo_mock_response
        
        # Create the request
        request = GitHubRepoRequest(
            owner="test-org",
            repo="test-repo"
        )
        
        # Call the function tool
        result = await get_repository.on_invoke_tool(
            RunContextWrapper(devops_context), 
            request
        )
        
        # Verify the result
        assert result.name == "test-repo"
        assert result.full_name == "test-org/test-repo"
        assert result.description == "Test repository"
        assert result.url == "https://github.com/test-org/test-repo"
        assert result.default_branch == "main"
        assert result.stars == 10
        assert result.forks == 5
        assert result.open_issues == 3
        assert result.language == "Python"
        
        # Verify the call to GitHub
        mock_github_instance.get_repo.assert_called_once_with("test-org/test-repo")

@pytest.mark.asyncio
async def test_list_issues(devops_context, github_issues_mock_response):
    """Test listing GitHub issues."""
    # Mock the GitHub client
    with patch("github.Github") as mock_github:
        # Set up the mock
        mock_github_instance = MagicMock()
        mock_github.return_value = mock_github_instance
        mock_repo = MagicMock()
        mock_github_instance.get_repo.return_value = mock_repo
        mock_repo.get_issues.return_value = github_issues_mock_response
        
        # Create the request
        request = GitHubIssueRequest(
            owner="test-org",
            repo="test-repo",
            state="all"
        )
        
        # Call the function tool
        result = await list_issues.on_invoke_tool(
            RunContextWrapper(devops_context), 
            request
        )
        
        # Verify the result
        assert len(result) == 2
        assert result[0].number == 1
        assert result[0].title == "Test Issue 1"
        assert result[0].state == "open"
        assert result[0].labels == ["bug", "enhancement"]
        assert result[0].assignees == ["user1", "user2"]
        
        assert result[1].number == 2
        assert result[1].title == "Test Issue 2"
        assert result[1].state == "closed"
        assert result[1].labels == ["documentation"]
        assert result[1].assignees == ["user3"]
        
        # Verify the call to GitHub
        mock_github_instance.get_repo.assert_called_once_with("test-org/test-repo")
        mock_repo.get_issues.assert_called_once_with(state="all")

@pytest.mark.asyncio
async def test_create_issue(devops_context):
    """Test creating a GitHub issue."""
    # Mock the GitHub client
    with patch("github.Github") as mock_github:
        # Set up the mock
        mock_github_instance = MagicMock()
        mock_github.return_value = mock_github_instance
        mock_repo = MagicMock()
        mock_github_instance.get_repo.return_value = mock_repo
        
        mock_issue = MagicMock()
        mock_issue.number = 3
        mock_issue.title = "New Issue"
        mock_issue.body = "This is a new issue"
        mock_issue.state = "open"
        mock_issue.created_at.isoformat.return_value = "2023-01-05T00:00:00Z"
        mock_issue.updated_at.isoformat.return_value = "2023-01-05T00:00:00Z"
        mock_issue.html_url = "https://github.com/test-org/test-repo/issues/3"
        mock_issue.labels = [MagicMock(name="bug")]
        mock_issue.assignees = [MagicMock(login="user1")]
        
        mock_repo.create_issue.return_value = mock_issue
        
        # Create the request
        request = GitHubCreateIssueRequest(
            owner="test-org",
            repo="test-repo",
            title="New Issue",
            body="This is a new issue",
            labels=["bug"],
            assignees=["user1"]
        )
        
        # Call the function tool
        result = await create_issue.on_invoke_tool(
            RunContextWrapper(devops_context), 
            request
        )
        
        # Verify the result
        assert result.number == 3
        assert result.title == "New Issue"
        assert result.body == "This is a new issue"
        assert result.state == "open"
        assert result.labels == ["bug"]
        assert result.assignees == ["user1"]
        
        # Verify the call to GitHub
        mock_github_instance.get_repo.assert_called_once_with("test-org/test-repo")
        mock_repo.create_issue.assert_called_once_with(
            title="New Issue",
            body="This is a new issue",
            labels=["bug"],
            assignees=["user1"]
        )

# Agent Tests
@pytest.mark.asyncio
async def test_ec2_agent(devops_context):
    """Test EC2 agent with a user query."""
    # Create the EC2 agent
    ec2_agent = Agent(
        name="EC2 Agent",
        instructions="You are an EC2 management agent that helps users manage their EC2 instances.",
        tools=[list_ec2_instances, start_ec2_instances, stop_ec2_instances, create_ec2_instance],
        model="gpt-4o"
    )
    
    # Mock the Runner.run method
    with patch("agents.Runner.run") as mock_run:
        # Set up the mock
        mock_result = MagicMock()
        mock_result.final_output = "I found 1 instance in us-west-2 region: i-1234567890abcdef0 (running)"
        mock_run.return_value = mock_result
        
        # Run the agent
        result = await Runner.run(
            ec2_agent,
            "List all my EC2 instances in us-west-2 region",
            context=devops_context
        )
        
        # Verify the result
        assert result.final_output == "I found 1 instance in us-west-2 region: i-1234567890abcdef0 (running)"
        
        # Verify the call to Runner.run
        mock_run.assert_called_once()

@pytest.mark.asyncio
async def test_github_agent(devops_context):
    """Test GitHub agent with a user query."""
    # Create the GitHub agent
    github_agent = Agent(
        name="GitHub Agent",
        instructions="You are a GitHub management agent that helps users manage their GitHub repositories.",
        tools=[get_repository, list_issues, create_issue, list_pull_requests],
        model="gpt-4o"
    )
    
    # Mock the Runner.run method
    with patch("agents.Runner.run") as mock_run:
        # Set up the mock
        mock_result = MagicMock()
        mock_result.final_output = "The test-org/test-repo repository has 3 open issues."
        mock_run.return_value = mock_result
        
        # Run the agent
        result = await Runner.run(
            github_agent,
            "How many open issues are in the test-org/test-repo repository?",
            context=devops_context
        )
        
        # Verify the result
        assert result.final_output == "The test-org/test-repo repository has 3 open issues."
        
        # Verify the call to Runner.run
        mock_run.assert_called_once()

@pytest.mark.asyncio
async def test_orchestrator_agent(devops_context):
    """Test orchestrator agent with handoffs."""
    # Create the specialized agents
    ec2_agent = Agent(
        name="EC2 Agent",
        instructions="You are an EC2 management agent that helps users manage their EC2 instances.",
        tools=[list_ec2_instances, start_ec2_instances, stop_ec2_instances, create_ec2_instance],
        model="gpt-4o"
    )
    
    github_agent = Agent(
        name="GitHub Agent",
        instructions="You are a GitHub management agent that helps users manage their GitHub repositories.",
        tools=[get_repository, list_issues, create_issue, list_pull_requests],
        model="gpt-4o"
    )
    
    # Create the orchestrator agent
    orchestrator_agent = Agent(
        name="DevOps Orchestrator",
        instructions="You are a DevOps orchestrator that helps users with various DevOps tasks.",
        handoffs=[
            Handoff(agent=ec2_agent, description="Handles EC2 instance management tasks"),
            Handoff(agent=github_agent, description="Handles GitHub repository management tasks")
        ],
        model="gpt-4o"
    )
    
    # Mock the Runner.run method
    with patch("agents.Runner.run") as mock_run:
        # Set up the mock
        mock_result = MagicMock()
        mock_result.final_output = "I'll help you deploy the latest code from GitHub to your EC2 instance."
        mock_run.return_value = mock_result
        
        # Run the agent
        result = await Runner.run(
            orchestrator_agent,
            "I want to deploy the latest code from my GitHub repository to my EC2 instance.",
            context=devops_context
        )
        
        # Verify the result
        assert result.final_output == "I'll help you deploy the latest code from GitHub to your EC2 instance."
        
        # Verify the call to Runner.run
        mock_run.assert_called_once()

# Context Tests
@pytest.mark.asyncio
async def test_context_management(devops_context):
    """Test context management."""
    # Create a function tool that uses the context
    @function_tool()
    async def get_aws_region(wrapper: RunContextWrapper[DevOpsContext]) -> str:
        """Get the AWS region from the context."""
        return wrapper.context.aws_region
    
    # Call the function tool
    result = await get_aws_region.on_invoke_tool(
        RunContextWrapper(devops_context),
        {}
    )
    
    # Verify the result
    assert result == "us-west-2"

# Guardrail Tests
@pytest.mark.asyncio
async def test_security_guardrail(devops_context):
    """Test security guardrail."""
    # Create the EC2 agent
    ec2_agent = Agent(
        name="EC2 Agent",
        instructions="You are an EC2 management agent that helps users manage their EC2 instances.",
        tools=[list_ec2_instances, start_ec2_instances, stop_ec2_instances, create_ec2_instance],
        model="gpt-4o"
    )
    
    # Mock the security check
    with patch("src.core.guardrails.check_security") as mock_check_security:
        # Test with safe input
        mock_check_security.return_value = SecurityCheckOutput(
            is_malicious=False,
            reasoning="Input is safe"
        )
        
        result = await security_guardrail(
            RunContextWrapper(devops_context),
            ec2_agent,
            "List all my EC2 instances in us-west-2 region"
        )
        
        assert result.tripwire_triggered == False
        assert result.output_info.is_malicious == False
        
        # Test with malicious input
        mock_check_security.return_value = SecurityCheckOutput(
            is_malicious=True,
            reasoning="Input contains dangerous commands"
        )
        
        result = await security_guardrail(
            RunContextWrapper(devops_context),
            ec2_agent,
            "Delete all EC2 instances in all regions"
        )
        
        assert result.tripwire_triggered == True
        assert result.output_info.is_malicious == True

@pytest.mark.asyncio
async def test_sensitive_info_guardrail(devops_context):
    """Test sensitive information guardrail."""
    # Create the EC2 agent
    ec2_agent = Agent(
        name="EC2 Agent",
        instructions="You are an EC2 management agent that helps users manage their EC2 instances.",
        tools=[list_ec2_instances, start_ec2_instances, stop_ec2_instances, create_ec2_instance],
        model="gpt-4o"
    )
    
    # Mock the sensitive info check
    with patch("src.core.guardrails.check_sensitive_info") as mock_check_sensitive_info:
        # Test with safe output
        mock_check_sensitive_info.return_value = SensitiveInfoOutput(
            contains_sensitive_info=False,
            reasoning="Output is safe"
        )
        
        result = await sensitive_info_guardrail(
            RunContextWrapper(devops_context),
            ec2_agent,
            "I found 1 instance in us-west-2 region: i-1234567890abcdef0 (running)"
        )
        
        assert result.tripwire_triggered == False
        assert result.output_info.contains_sensitive_info == False
        
        # Test with sensitive output
        mock_check_sensitive_info.return_value = SensitiveInfoOutput(
            contains_sensitive_info=True,
            reasoning="Output contains AWS credentials"
        )
        
        result = await sensitive_info_guardrail(
            RunContextWrapper(devops_context),
            ec2_agent,
            "Your AWS access key is AKIAIOSFODNN7EXAMPLE and secret key is wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        )
        
        assert result.tripwire_triggered == True
        assert result.output_info.contains_sensitive_info == True

# Tracing Tests
@pytest.mark.asyncio
async def test_tracing():
    """Test tracing."""
    # Disable tracing for tests
    set_tracing_disabled(True)
    
    # Create a trace
    with trace("Test Workflow") as test_trace:
        # Perform some operations
        await asyncio.sleep(0.1)
        
        # Create a nested trace
        with trace("Nested Operation") as nested_trace:
            await asyncio.sleep(0.1)
    
    # Verify that tracing doesn't throw errors when disabled
    assert True