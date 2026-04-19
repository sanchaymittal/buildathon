"""Lightweight Gemini Agents compatibility layer.

This module mirrors the subset of agent SDK features used by the DevOps Agent
codebase, enabling drop-in replacement for function tools and guardrails while
deferring actual model execution to future Gemini integrations.
"""

from __future__ import annotations

import contextlib
import functools
import inspect
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Generic, Iterable, List, Optional, TypeVar


T = TypeVar("T")


class RunContextWrapper(Generic[T]):
    """Simple wrapper that carries the runtime context object."""

    def __init__(self, context: T):
        self.context = context


@dataclass
class GuardrailFunctionOutput:
    """Represents the outcome of guardrail checks."""

    tripwire_triggered: bool
    output_info: Any = None


@dataclass
class Handoff:
    agent: "Agent"
    description: str


@dataclass
class Agent:
    """Minimal agent definition used for tests and orchestration."""

    name: str
    instructions: str
    tools: List[Any] = field(default_factory=list)
    handoffs: List[Handoff] = field(default_factory=list)
    model: Optional[str] = None


class Runner:
    """Placeholder runner for Gemini orchestration.

    The actual invocation logic should be provided by a real Gemini SDK client.
    """

    @staticmethod
    async def run(agent: Agent, prompt: str, context: Any = None) -> Any:
        raise NotImplementedError(
            "Gemini Runner integration is not implemented. Inject a custom runner or mock in tests."
        )

_TRACING_DISABLED = False


def set_tracing_disabled(disabled: bool) -> None:
    """Enable or disable tracing output."""

    global _TRACING_DISABLED
    _TRACING_DISABLED = disabled


def function_tool(*decorator_args: Any, **decorator_kwargs: Any) -> Callable[[Callable[..., Any]], Any]:
    """Decorator that marks a coroutine/function as a Gemini function tool."""

    def decorator(func: Callable[..., Any]) -> Any:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

        async def on_invoke_tool(run_context: RunContextWrapper[Any], *tool_args: Any, **tool_kwargs: Any) -> Any:
            if inspect.iscoroutinefunction(func):
                return await func(run_context, *tool_args, **tool_kwargs)  # type: ignore[arg-type]
            return func(run_context, *tool_args, **tool_kwargs)  # type: ignore[arg-type]

        wrapper.on_invoke_tool = on_invoke_tool  # type: ignore[attr-defined]
        wrapper.original = func  # type: ignore[attr-defined]
        return wrapper

    if decorator_args and callable(decorator_args[0]) and not decorator_kwargs:
        return decorator(decorator_args[0])

    return decorator


def input_guardrail(func: Optional[Callable[..., Any]] = None) -> Callable[[Callable[..., Any]], Callable[..., Awaitable[GuardrailFunctionOutput]]]:
    """Decorator for Gemini input guardrails."""

    def decorator(inner: Callable[..., Any]) -> Callable[..., Awaitable[GuardrailFunctionOutput]]:
        @functools.wraps(inner)
        async def wrapped(*args: Any, **kwargs: Any) -> GuardrailFunctionOutput:
            if inspect.iscoroutinefunction(inner):
                return await inner(*args, **kwargs)  # type: ignore[return-value]
            return inner(*args, **kwargs)  # type: ignore[return-value]

        return wrapped

    if func is not None:
        return decorator(func)

    return decorator


def output_guardrail(func: Optional[Callable[..., Any]] = None) -> Callable[[Callable[..., Any]], Callable[..., Awaitable[GuardrailFunctionOutput]]]:
    """Decorator for Gemini output guardrails."""

    def decorator(inner: Callable[..., Any]) -> Callable[..., Awaitable[GuardrailFunctionOutput]]:
        @functools.wraps(inner)
        async def wrapped(*args: Any, **kwargs: Any) -> GuardrailFunctionOutput:
            if inspect.iscoroutinefunction(inner):
                return await inner(*args, **kwargs)  # type: ignore[return-value]
            return inner(*args, **kwargs)  # type: ignore[return-value]

        return wrapped

    if func is not None:
        return decorator(func)

    return decorator


@contextlib.contextmanager
def trace(name: str) -> Iterable[None]:
    """Lightweight tracing context manager placeholder."""

    if _TRACING_DISABLED:
        yield
        return

    yield


__all__ = [
    "Agent",
    "Runner",
    "Handoff",
    "RunContextWrapper",
    "GuardrailFunctionOutput",
    "function_tool",
    "input_guardrail",
    "output_guardrail",
    "set_tracing_disabled",
    "trace",
]
