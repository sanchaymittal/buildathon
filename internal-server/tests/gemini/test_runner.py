"""Unit tests for GeminiRunner with a fake model factory (no network)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional

import pytest
from pydantic import BaseModel

from src.core.credentials import GeminiCredentials
from src.gemini_agents import Agent, function_tool
from src.gemini_agents.runner import (
    AgentGuardrailError,
    GeminiRunner,
    build_tool_declarations,
)


# ---------------------------------------------------------------- Fake model
@dataclass
class FakeFunctionCall:
    name: str
    args: dict


@dataclass
class FakePart:
    text: Optional[str] = None
    function_call: Optional[FakeFunctionCall] = None


@dataclass
class FakeContent:
    parts: List[FakePart]


@dataclass
class FakeCandidate:
    content: FakeContent


@dataclass
class FakeResponse:
    candidates: List[FakeCandidate]

    @property
    def text(self) -> str:
        for c in self.candidates:
            for p in c.content.parts:
                if p.text:
                    return p.text
        return ""


def _text_response(text: str) -> FakeResponse:
    return FakeResponse(
        candidates=[FakeCandidate(content=FakeContent(parts=[FakePart(text=text)]))]
    )


def _function_call_response(name: str, args: dict) -> FakeResponse:
    return FakeResponse(
        candidates=[
            FakeCandidate(
                content=FakeContent(
                    parts=[
                        FakePart(function_call=FakeFunctionCall(name=name, args=args))
                    ]
                )
            )
        ]
    )


class FakeModel:
    """Scripted responses. ``responses`` is popped in order on each call."""

    def __init__(self, responses: List[FakeResponse]):
        self._responses = list(responses)
        self.conversations: List[Any] = []

    def generate_content(self, conversation):
        self.conversations.append(conversation)
        if not self._responses:
            raise AssertionError("Ran out of scripted responses")
        return self._responses.pop(0)


def make_factory(model: FakeModel):
    def factory(creds, model_override, tools, system_instruction):
        return model

    return factory


# ---------------------------------------------------------------- Sample tool
class AddRequest(BaseModel):
    a: int
    b: int


@function_tool()
async def add(ctx, request: AddRequest) -> dict:
    """Add two integers."""
    return {"sum": request.a + request.b}


@function_tool()
async def greet(ctx, name: str) -> str:
    """Greet someone by name."""
    return f"hello {name}"


# ---------------------------------------------------------------- Tests
@pytest.fixture
def creds():
    return GeminiCredentials(api_key="test", model="gemini-2.5-flash")


class TestToolDeclarations:
    def test_pydantic_model_becomes_object_schema(self):
        decls = build_tool_declarations([add])
        (payload,) = decls
        (decl,) = payload["function_declarations"]
        assert decl["name"] == "add"
        assert decl["parameters"]["type"] == "OBJECT"
        props = decl["parameters"]["properties"]
        assert "request" in props
        assert props["request"]["type"] == "OBJECT"
        assert "a" in props["request"]["properties"]
        assert decl["parameters"]["required"] == ["request"]

    def test_plain_string_param(self):
        decls = build_tool_declarations([greet])
        decl = decls[0]["function_declarations"][0]
        assert decl["name"] == "greet"
        assert decl["parameters"]["properties"]["name"]["type"] == "STRING"


class TestRunLoop:
    @pytest.mark.asyncio
    async def test_no_tool_call_returns_text_immediately(self, creds):
        model = FakeModel([_text_response("hello world")])
        runner = GeminiRunner(credentials=creds, model_factory=make_factory(model))
        agent = Agent(name="t", instructions="be helpful", tools=[add])

        result = await runner.run(agent, "hi")

        assert result.output == "hello world"
        assert result.finish_reason == "stop"
        assert result.tool_calls == []

    @pytest.mark.asyncio
    async def test_single_tool_call_then_final_text(self, creds):
        model = FakeModel(
            [
                _function_call_response("add", {"request": {"a": 2, "b": 3}}),
                _text_response("the answer is 5"),
            ]
        )
        runner = GeminiRunner(credentials=creds, model_factory=make_factory(model))
        agent = Agent(name="t", instructions="", tools=[add])

        result = await runner.run(agent, "add 2 and 3")

        assert result.output == "the answer is 5"
        assert len(result.tool_calls) == 1
        call = result.tool_calls[0]
        assert call.name == "add"
        assert call.result == {"sum": 5}
        assert call.error is None

    @pytest.mark.asyncio
    async def test_unknown_tool_call_is_recorded_with_error(self, creds):
        model = FakeModel(
            [
                _function_call_response("does_not_exist", {}),
                _text_response("sorry"),
            ]
        )
        runner = GeminiRunner(credentials=creds, model_factory=make_factory(model))
        agent = Agent(name="t", instructions="", tools=[add])

        result = await runner.run(agent, "hi")

        assert result.tool_calls[0].name == "does_not_exist"
        assert result.tool_calls[0].error == "Unknown tool: does_not_exist"

    @pytest.mark.asyncio
    async def test_tool_raising_is_captured(self, creds):
        @function_tool()
        async def boom(ctx) -> str:
            raise RuntimeError("boom")

        model = FakeModel(
            [
                _function_call_response("boom", {}),
                _text_response("done"),
            ]
        )
        runner = GeminiRunner(credentials=creds, model_factory=make_factory(model))
        agent = Agent(name="t", instructions="", tools=[boom])

        result = await runner.run(agent, "run boom")
        assert result.tool_calls[0].error.startswith("RuntimeError: boom")
        assert result.output == "done"

    @pytest.mark.asyncio
    async def test_max_tool_calls_respected(self, creds):
        # Always return a function_call -> runner should stop at max budget.
        responses = [
            _function_call_response("add", {"request": {"a": 1, "b": 1}})
            for _ in range(10)
        ]
        model = FakeModel(responses)
        runner = GeminiRunner(
            credentials=creds, max_tool_calls=3, model_factory=make_factory(model)
        )
        agent = Agent(name="t", instructions="", tools=[add])

        result = await runner.run(agent, "loop")
        assert result.finish_reason == "max_tool_calls"
        # max_tool_calls=3 -> loop runs 4 iterations (3+1), 4 function_calls
        # recorded before budget trips.
        assert len(result.tool_calls) == 4

    @pytest.mark.asyncio
    async def test_input_guardrail_trips_before_model_call(self, creds):
        model = FakeModel([_text_response("should-not-reach")])
        runner = GeminiRunner(credentials=creds, model_factory=make_factory(model))
        agent = Agent(name="t", instructions="", tools=[])

        async def input_guard(ctx, agent, payload):
            class _GO:
                tripwire_triggered = True
                output_info = "blocked"

            return _GO()

        with pytest.raises(AgentGuardrailError):
            await runner.run(agent, "evil input", input_guardrails=[input_guard])
        # Model never got called.
        assert model.conversations == []

    @pytest.mark.asyncio
    async def test_output_guardrail_trips_after_model(self, creds):
        model = FakeModel([_text_response("sensitive output")])
        runner = GeminiRunner(credentials=creds, model_factory=make_factory(model))
        agent = Agent(name="t", instructions="", tools=[])

        async def output_guard(ctx, agent, payload):
            class _GO:
                tripwire_triggered = "sensitive" in payload
                output_info = "leaked"

            return _GO()

        with pytest.raises(AgentGuardrailError):
            await runner.run(agent, "go", output_guardrails=[output_guard])

    @pytest.mark.asyncio
    async def test_history_is_populated(self, creds):
        model = FakeModel([_text_response("done")])
        runner = GeminiRunner(credentials=creds, model_factory=make_factory(model))
        agent = Agent(name="t", instructions="", tools=[])
        history: list = []

        await runner.run(agent, "hello", history=history)

        # history should include the user turn at minimum.
        assert any(
            msg["role"] == "user" and msg["parts"][0].get("text") == "hello"
            for msg in history
        )
