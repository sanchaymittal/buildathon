"""Gemini Agents integration smoke tests geared toward Docker-native workflows."""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from src.gemini_agents import Agent, Runner, RunContextWrapper, function_tool, set_tracing_disabled, trace

from src.core.context import DevOpsContext
from src.core.guardrails import (
    security_guardrail,
    sensitive_info_guardrail,
    SecurityCheckOutput,
    SensitiveInfoOutput,
)


@pytest.fixture
def devops_context():
    return DevOpsContext(
        user_id="test-user",
        github_org="demo-org",
        environment="dev",
        metadata={"docker_host": "unix:///var/run/docker.sock"},
    )


@function_tool()
async def list_demo_containers(_: RunContextWrapper[DevOpsContext]) -> list[dict]:
    return [
        {
            "id": "container-1234",
            "name": "demo_web",
            "image": "demo/web:latest",
            "status": "running",
        }
    ]


@pytest.mark.asyncio
async def test_agent_runner_invocation(devops_context):
    docker_agent = Agent(
        name="Docker Agent",
        instructions="List demo containers",
        tools=[list_demo_containers],
        model="gemini-1.5-pro",
    )

    with patch("gemini_agents.Runner.run") as mock_run:
        mock_result = MagicMock()
        mock_result.final_output = "Found 1 container"
        mock_run.return_value = mock_result

        result = await Runner.run(
            docker_agent,
            "List containers",
            context=devops_context,
        )

        assert result.final_output == "Found 1 container"
        mock_run.assert_called_once()


@pytest.mark.asyncio
async def test_security_guardrail_allows_safe_requests(devops_context):
    docker_agent = Agent(name="Docker Agent", instructions="Manage containers", tools=[], model="gemini-1.5-pro")

    with patch("src.core.guardrails.check_security") as mock_check_security:
        mock_check_security.return_value = SecurityCheckOutput(is_malicious=False, reasoning="Safe command")

        result = await security_guardrail(
            RunContextWrapper(devops_context),
            docker_agent,
            "List all containers",
        )

        assert result.tripwire_triggered is False
        assert result.output_info.is_malicious is False


@pytest.mark.asyncio
async def test_security_guardrail_blocks_dangerous_requests(devops_context):
    docker_agent = Agent(name="Docker Agent", instructions="Manage containers", tools=[], model="gemini-1.5-pro")

    with patch("src.core.guardrails.check_security") as mock_check_security:
        mock_check_security.return_value = SecurityCheckOutput(
            is_malicious=True,
            reasoning="Command attempts to wipe host",
        )

        result = await security_guardrail(
            RunContextWrapper(devops_context),
            docker_agent,
            "rm -rf /",
        )

        assert result.tripwire_triggered is True
        assert result.output_info.is_malicious is True


@pytest.mark.asyncio
async def test_sensitive_info_guardrail(devops_context):
    docker_agent = Agent(name="Docker Agent", instructions="Manage containers", tools=[], model="gemini-1.5-pro")

    with patch("src.core.guardrails.check_sensitive_info") as mock_check_sensitive_info:
        mock_check_sensitive_info.return_value = SensitiveInfoOutput(
            contains_sensitive_info=False,
            reasoning="No secrets detected",
        )

        result = await sensitive_info_guardrail(
            RunContextWrapper(devops_context),
            docker_agent,
            "Container demo_web is healthy",
        )

        assert result.tripwire_triggered is False
        assert result.output_info.contains_sensitive_info is False

        mock_check_sensitive_info.return_value = SensitiveInfoOutput(
            contains_sensitive_info=True,
            reasoning="Output contains registry credentials",
        )

        result = await sensitive_info_guardrail(
            RunContextWrapper(devops_context),
            docker_agent,
            "Registry password is super-secret",
        )

        assert result.tripwire_triggered is True
        assert result.output_info.contains_sensitive_info is True


@pytest.mark.asyncio
async def test_tracing_disabled_is_harmless():
    set_tracing_disabled(True)

    with trace("Test Workflow"):
        await asyncio.sleep(0.01)
        with trace("Nested Operation"):
            await asyncio.sleep(0.01)

    assert True
