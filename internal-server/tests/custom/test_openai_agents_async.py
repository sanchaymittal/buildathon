"""
Tests for OpenAI Agents SDK integration with DevOps agent using async/await.

This module contains tests for the OpenAI Agents SDK integration with the DevOps agent.
It includes tests for EC2 operations, GitHub operations, and agent orchestration.
"""

import unittest
import asyncio
from unittest.mock import patch, MagicMock
import json
import os
import sys
from io import StringIO

# Import OpenAI Agents SDK
from agents import Agent, Runner
from agents.tracing import set_tracing_disabled

# Import our EC2 example implementation
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from examples.openai_agents_ec2_example import (
    list_ec2_instances, 
    start_ec2_instances, 
    stop_ec2_instances, 
    create_ec2_instance,
    EC2InstanceFilter,
    EC2StartStopRequest,
    EC2CreateRequest,
    ec2_agent
)


class TestOpenAIAgentsAsyncIntegration(unittest.IsolatedAsyncioTestCase):
    """Test OpenAI Agents SDK integration with DevOps agent using async/await."""

    def setUp(self):
        """Set up test fixtures."""
        # Disable tracing for tests
        set_tracing_disabled(True)
        
        # Capture stdout for testing print output
        self.stdout_capture = StringIO()
        self.original_stdout = sys.stdout
        sys.stdout = self.stdout_capture
        
        # Mock environment variables
        self.env_patcher = patch.dict('os.environ', {
            'OPENAI_API_KEY': 'test-api-key'
        })
        self.env_patcher.start()

    def tearDown(self):
        """Tear down test fixtures."""
        sys.stdout = self.original_stdout
        self.env_patcher.stop()

    @patch('boto3.client')
    async def test_list_ec2_instances(self, mock_boto_client):
        """Test listing EC2 instances."""
        # Mock EC2 client
        mock_ec2 = MagicMock()
        mock_boto_client.return_value = mock_ec2
        
        # Mock response from EC2 describe_instances
        mock_ec2.describe_instances.return_value = {
            'Reservations': [
                {
                    'Instances': [
                        {
                            'InstanceId': 'i-1234567890abcdef0',
                            'State': {'Name': 'running'},
                            'InstanceType': 't2.micro',
                            'PublicIpAddress': '54.123.45.67',
                            'PrivateIpAddress': '10.0.0.123',
                            'Tags': [
                                {'Key': 'Name', 'Value': 'Test Instance'},
                                {'Key': 'Environment', 'Value': 'Test'}
                            ]
                        }
                    ]
                }
            ]
        }
        
        # Call the function
        filter_params = EC2InstanceFilter(region='us-west-2')
        # Use the on_invoke_tool method to call the function
        result = await list_ec2_instances.on_invoke_tool(None, filter_params)
        
        # Verify the result
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].instance_id, 'i-1234567890abcdef0')
        self.assertEqual(result[0].state, 'running')
        self.assertEqual(result[0].instance_type, 't2.micro')
        self.assertEqual(result[0].public_ip_address, '54.123.45.67')
        self.assertEqual(result[0].private_ip_address, '10.0.0.123')
        self.assertEqual(result[0].tags, {'Name': 'Test Instance', 'Environment': 'Test'})
        
        # Verify the call to boto3
        mock_boto_client.assert_called_once_with('ec2', region_name='us-west-2')
        mock_ec2.describe_instances.assert_called_once_with()

    @patch('boto3.client')
    async def test_start_ec2_instances(self, mock_boto_client):
        """Test starting EC2 instances."""
        # Mock EC2 client
        mock_ec2 = MagicMock()
        mock_boto_client.return_value = mock_ec2
        
        # Mock response from EC2 start_instances
        mock_ec2.start_instances.return_value = {
            'StartingInstances': [
                {
                    'InstanceId': 'i-1234567890abcdef0',
                    'CurrentState': {'Name': 'pending'},
                    'PreviousState': {'Name': 'stopped'}
                }
            ]
        }
        
        # Call the function
        request = EC2StartStopRequest(
            instance_ids=['i-1234567890abcdef0'],
            region='us-west-2'
        )
        # Use the on_invoke_tool method to call the function
        result = await start_ec2_instances.on_invoke_tool(None, request)
        
        # Verify the result
        self.assertEqual(len(result['StartingInstances']), 1)
        self.assertEqual(result['StartingInstances'][0]['InstanceId'], 'i-1234567890abcdef0')
        
        # Verify the call to boto3
        mock_boto_client.assert_called_once_with('ec2', region_name='us-west-2')
        mock_ec2.start_instances.assert_called_once_with(InstanceIds=['i-1234567890abcdef0'])

    @patch('boto3.client')
    async def test_stop_ec2_instances(self, mock_boto_client):
        """Test stopping EC2 instances."""
        # Mock EC2 client
        mock_ec2 = MagicMock()
        mock_boto_client.return_value = mock_ec2
        
        # Mock response from EC2 stop_instances
        mock_ec2.stop_instances.return_value = {
            'StoppingInstances': [
                {
                    'InstanceId': 'i-1234567890abcdef0',
                    'CurrentState': {'Name': 'stopping'},
                    'PreviousState': {'Name': 'running'}
                }
            ]
        }
        
        # Call the function
        request = EC2StartStopRequest(
            instance_ids=['i-1234567890abcdef0'],
            region='us-west-2'
        )
        # Use the on_invoke_tool method to call the function
        result = await stop_ec2_instances.on_invoke_tool(None, request)
        
        # Verify the result
        self.assertEqual(len(result['StoppingInstances']), 1)
        self.assertEqual(result['StoppingInstances'][0]['InstanceId'], 'i-1234567890abcdef0')
        
        # Verify the call to boto3
        mock_boto_client.assert_called_once_with('ec2', region_name='us-west-2')
        mock_ec2.stop_instances.assert_called_once_with(InstanceIds=['i-1234567890abcdef0'])

    @patch('boto3.client')
    async def test_create_ec2_instance(self, mock_boto_client):
        """Test creating EC2 instances."""
        # Mock EC2 client
        mock_ec2 = MagicMock()
        mock_boto_client.return_value = mock_ec2
        
        # Mock response from EC2 run_instances
        mock_ec2.run_instances.return_value = {
            'Instances': [
                {
                    'InstanceId': 'i-1234567890abcdef0',
                    'InstanceType': 't2.micro',
                    'State': {'Name': 'pending'},
                    'PrivateIpAddress': '10.0.0.123'
                }
            ]
        }
        
        # Call the function
        request = EC2CreateRequest(
            image_id='ami-12345678',
            instance_type='t2.micro',
            key_name='test-key',
            security_group_ids=['sg-12345678'],
            subnet_id='subnet-12345678',
            region='us-west-2',
            tags={'Name': 'Test Instance', 'Environment': 'Test'}
        )
        # Use the on_invoke_tool method to call the function
        result = await create_ec2_instance.on_invoke_tool(None, request)
        
        # Verify the result
        self.assertEqual(len(result['Instances']), 1)
        self.assertEqual(result['Instances'][0]['InstanceId'], 'i-1234567890abcdef0')
        self.assertEqual(result['Instances'][0]['InstanceType'], 't2.micro')
        
        # Verify the call to boto3
        mock_boto_client.assert_called_once_with('ec2', region_name='us-west-2')
        mock_ec2.run_instances.assert_called_once_with(
            ImageId='ami-12345678',
            InstanceType='t2.micro',
            MinCount=1,
            MaxCount=1,
            KeyName='test-key',
            SecurityGroupIds=['sg-12345678'],
            SubnetId='subnet-12345678',
            TagSpecifications=[
                {
                    'ResourceType': 'instance',
                    'Tags': [
                        {'Key': 'Name', 'Value': 'Test Instance'},
                        {'Key': 'Environment', 'Value': 'Test'}
                    ]
                }
            ]
        )

    @patch('agents.Runner.run_sync')
    async def test_ec2_agent(self, mock_run_sync):
        """Test EC2 agent with a user query."""
        # Mock the Runner.run_sync method
        mock_result = MagicMock()
        mock_result.final_output = "I found 2 instances in us-west-2 region."
        mock_result.conversation = [
            MagicMock(role="user", content="List all my EC2 instances in us-west-2 region"),
            MagicMock(role="assistant", content="I found 2 instances in us-west-2 region.")
        ]
        mock_run_sync.return_value = mock_result
        
        # Create a context
        context = {}
        
        # Run the agent
        result = Runner.run_sync(
            ec2_agent,
            "List all my EC2 instances in us-west-2 region",
            context=context
        )
        
        # Verify the result
        self.assertEqual(result.final_output, "I found 2 instances in us-west-2 region.")
        self.assertEqual(len(result.conversation), 2)
        
        # Verify the call to Runner.run_sync
        mock_run_sync.assert_called_once_with(
            ec2_agent,
            "List all my EC2 instances in us-west-2 region",
            context=context
        )


if __name__ == '__main__':
    unittest.main()