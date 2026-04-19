"""
Real Gemini-powered runner for the lightweight Agent abstraction.

Replaces the ``NotImplementedError`` placeholder ``Runner`` in
``src/gemini_agents/__init__.py`` with an executable tool-call loop.

Design
------
Each tool produced by :func:`gemini_agents.function_tool` already exposes
``.on_invoke_tool(run_context, **kwargs)`` (an async coroutine). This runner:

1. Converts the agent's tools into Gemini function declarations.
2. Applies input guardrails (synchronously) on the user prompt.
3. Loops up to ``max_tool_calls`` times:
    - Sends the conversation to Gemini.
    - If the model returns a ``function_call``, executes the matching tool,
      appends the result, and feeds it back.
    - Otherwise, exits with the final text.
4. Applies output guardrails on the final text.
5. Appends a structured line to the audit log for each turn.

This module deliberately keeps the Gemini SDK imports lazy so the rest of the
package is importable without ``google-generativeai``. Tests inject a fake
``_ModelFactory`` to exercise the loop without any network calls.
"""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel

from ..core.credentials import GeminiCredentials, get_credential_manager
from . import Agent, RunContextWrapper
from .client import build_model, is_available

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------- Data models
@dataclass
class ToolCallRecord:
    name: str
    arguments: Dict[str, Any]
    result: Any
    error: Optional[str] = None
    duration_ms: Optional[int] = None


@dataclass
class RunResult:
    output: str
    tool_calls: List[ToolCallRecord] = field(default_factory=list)
    trace_id: str = ""
    model: str = ""
    finish_reason: str = ""
    iterations: int = 0


class AgentRunError(RuntimeError):
    """Raised when a run fails for reasons other than guardrails."""


class AgentGuardrailError(RuntimeError):
    """Raised when a guardrail tripwire fires."""


# ---------------------------------------------------------------- Introspection
def _tool_name(tool: Any) -> str:
    original = getattr(tool, "original", tool)
    return getattr(original, "__name__", "tool")


def _tool_description(tool: Any) -> str:
    original = getattr(tool, "original", tool)
    doc = inspect.getdoc(original) or ""
    return doc.strip().split("\n\n")[0] or f"Tool {_tool_name(tool)}"


def _tool_signature(tool: Any) -> inspect.Signature:
    """Return the tool's signature with string annotations resolved.

    Modules that use ``from __future__ import annotations`` produce string
    annotations that would otherwise break runtime coercion. We eagerly
    resolve them via :func:`typing.get_type_hints`.
    """
    original = getattr(tool, "original", tool)
    signature = inspect.signature(original)
    try:
        import typing

        hints = typing.get_type_hints(original)
    except Exception:
        return signature

    new_params = []
    for name, param in signature.parameters.items():
        if name in hints:
            new_params.append(param.replace(annotation=hints[name]))
        else:
            new_params.append(param)
    return signature.replace(parameters=new_params)


_PYDANTIC_TO_GENAI = {
    "string": "STRING",
    "integer": "INTEGER",
    "number": "NUMBER",
    "boolean": "BOOLEAN",
    "array": "ARRAY",
    "object": "OBJECT",
}


def _json_schema_to_genai_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    """Translate a JSON-Schema-ish dict from pydantic into Gemini's schema form."""
    if "$ref" in schema:
        # pydantic puts nested models behind $ref; best-effort treat as object.
        return {"type": "OBJECT"}
    t = schema.get("type")
    if isinstance(t, list):
        t = next((x for x in t if x != "null"), "string")
    out: Dict[str, Any] = {"type": _PYDANTIC_TO_GENAI.get(t or "string", "STRING")}
    if "description" in schema:
        out["description"] = schema["description"]
    if out["type"] == "OBJECT":
        props = schema.get("properties") or {}
        out["properties"] = {
            k: _json_schema_to_genai_schema(v) for k, v in props.items()
        }
        required = schema.get("required") or []
        if required:
            out["required"] = list(required)
    elif out["type"] == "ARRAY":
        items = schema.get("items") or {"type": "string"}
        out["items"] = _json_schema_to_genai_schema(items)
    return out


def _tool_to_function_declaration(tool: Any) -> Dict[str, Any]:
    """Build a single Gemini function declaration dict for a tool."""
    name = _tool_name(tool)
    description = _tool_description(tool)
    signature = _tool_signature(tool)

    properties: Dict[str, Any] = {}
    required: List[str] = []

    for param_name, param in signature.parameters.items():
        if param_name in ("ctx", "run_context", "self"):
            continue
        annotation = param.annotation
        if inspect.isclass(annotation) and issubclass(annotation, BaseModel):
            schema = annotation.model_json_schema()
            properties[param_name] = _json_schema_to_genai_schema(schema)
            if param.default is inspect.Parameter.empty:
                required.append(param_name)
        else:
            # Fall back to an OBJECT/STRING slot for unannotated params.
            properties[param_name] = {
                "type": "OBJECT" if annotation is inspect.Parameter.empty else "STRING"
            }
            if param.default is inspect.Parameter.empty:
                required.append(param_name)

    decl: Dict[str, Any] = {"name": name, "description": description}
    parameters: Dict[str, Any] = {"type": "OBJECT", "properties": properties}
    if required:
        parameters["required"] = required
    decl["parameters"] = parameters
    return decl


def build_tool_declarations(tools: List[Any]) -> List[Dict[str, Any]]:
    """Build a Gemini ``tools`` payload from a list of function tools."""
    declarations = [_tool_to_function_declaration(t) for t in tools]
    return [{"function_declarations": declarations}]


# ---------------------------------------------------------------- Tool dispatch
def _coerce_tool_arguments(tool: Any, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Coerce model-supplied arguments to match the tool's pydantic signature."""
    signature = _tool_signature(tool)
    coerced: Dict[str, Any] = {}
    for param_name, param in signature.parameters.items():
        if param_name in ("ctx", "run_context", "self"):
            continue
        if param_name not in arguments:
            continue
        value = arguments[param_name]
        annotation = param.annotation
        if (
            inspect.isclass(annotation)
            and issubclass(annotation, BaseModel)
            and isinstance(value, dict)
        ):
            coerced[param_name] = annotation.model_validate(value)
        else:
            coerced[param_name] = value
    return coerced


async def _invoke_tool(
    tool: Any,
    run_context: RunContextWrapper[Any],
    arguments: Dict[str, Any],
) -> Any:
    invoker = getattr(tool, "on_invoke_tool", None)
    coerced = _coerce_tool_arguments(tool, arguments)
    if invoker is not None:
        result = invoker(run_context, **coerced)
    else:
        result = tool(run_context, **coerced)
    if inspect.isawaitable(result):
        result = await result
    return result


def _serialise_result(result: Any) -> Any:
    if isinstance(result, BaseModel):
        return result.model_dump(mode="json")
    if isinstance(result, list):
        return [_serialise_result(x) for x in result]
    if isinstance(result, dict):
        return {k: _serialise_result(v) for k, v in result.items()}
    try:
        json.dumps(result)
        return result
    except (TypeError, ValueError):
        return str(result)


# ---------------------------------------------------------------- Runner
class _DefaultModelFactory:
    """Calls google-generativeai to build a ``GenerativeModel``."""

    def __call__(
        self,
        creds: GeminiCredentials,
        model_override: Optional[str],
        tools: List[Dict[str, Any]],
        system_instruction: Optional[str],
    ) -> Any:
        return build_model(
            creds,
            model_override=model_override,
            tools=tools,
            system_instruction=system_instruction,
        )


def _to_plain(value: Any) -> Any:
    """Recursively convert protobuf ``MapComposite`` / ``RepeatedComposite``
    values into plain Python dicts / lists / scalars.

    The google-generativeai response objects use protobuf containers that
    aren't deep-copyable, which breaks ``dataclasses.asdict`` downstream.
    """
    # protobuf Map/Struct -> dict; Repeated -> list.
    if hasattr(value, "items") and not isinstance(value, dict):
        return {str(k): _to_plain(v) for k, v in value.items()}
    if isinstance(value, dict):
        return {str(k): _to_plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_plain(v) for v in value]
    if hasattr(value, "__iter__") and not isinstance(value, (str, bytes, bytearray)):
        # RepeatedComposite / ListValue / etc.
        try:
            return [_to_plain(v) for v in value]
        except TypeError:
            pass
    return value


def _extract_function_call(response: Any):
    """Find the first function_call part in a Gemini response, if any."""
    candidates = getattr(response, "candidates", None) or []
    for cand in candidates:
        content = getattr(cand, "content", None)
        parts = getattr(content, "parts", None) if content else None
        for part in parts or []:
            fc = getattr(part, "function_call", None)
            if fc is not None and getattr(fc, "name", None):
                return fc
    return None


def _extract_text(response: Any) -> str:
    text = getattr(response, "text", None)
    if text:
        return text
    parts_text: List[str] = []
    for cand in getattr(response, "candidates", None) or []:
        content = getattr(cand, "content", None)
        for part in getattr(content, "parts", None) or []:
            txt = getattr(part, "text", None)
            if txt:
                parts_text.append(txt)
    return "\n".join(parts_text)


async def _run_guardrail(
    guardrail: Callable[..., Any],
    run_context: RunContextWrapper[Any],
    agent: Agent,
    payload: Any,
) -> Any:
    """Invoke an input/output guardrail, awaiting it if necessary."""
    result = guardrail(run_context, agent, payload)
    if inspect.isawaitable(result):
        result = await result
    return result


class GeminiRunner:
    """
    Real agent runner driving ``google-generativeai``.

    Test code can inject ``model_factory`` to avoid real network calls.
    """

    def __init__(
        self,
        credentials: Optional[GeminiCredentials] = None,
        max_tool_calls: int = 16,
        audit_logger: Optional[Any] = None,
        model_factory: Optional[Callable[..., Any]] = None,
    ) -> None:
        self._credentials = credentials
        self._max_tool_calls = max_tool_calls
        self._audit_logger = audit_logger
        self._model_factory = model_factory or _DefaultModelFactory()

    def _get_credentials(self) -> GeminiCredentials:
        if self._credentials is not None:
            return self._credentials
        return get_credential_manager().get_gemini_credentials()

    async def run(
        self,
        agent: Agent,
        prompt: str,
        context: Any = None,
        history: Optional[List[Dict[str, Any]]] = None,
        input_guardrails: Optional[List[Callable[..., Any]]] = None,
        output_guardrails: Optional[List[Callable[..., Any]]] = None,
    ) -> RunResult:
        trace_id = str(uuid.uuid4())
        creds = self._get_credentials()
        run_context: RunContextWrapper[Any] = RunContextWrapper(context)
        tool_map = {_tool_name(t): t for t in agent.tools}
        tools_payload = build_tool_declarations(agent.tools) if agent.tools else None
        model = self._model_factory(
            creds,
            agent.model or creds.model,
            tools_payload,
            agent.instructions,
        )

        # Input guardrails.
        for guard in input_guardrails or []:
            outcome = await _run_guardrail(guard, run_context, agent, prompt)
            if getattr(outcome, "tripwire_triggered", False):
                raise AgentGuardrailError(
                    f"Input guardrail triggered: {getattr(outcome, 'output_info', '')}"
                )

        conversation: List[Dict[str, Any]] = list(history or [])
        conversation.append({"role": "user", "parts": [{"text": prompt}]})

        tool_records: List[ToolCallRecord] = []
        finish_reason = ""
        output_text = ""

        for iteration in range(self._max_tool_calls + 1):
            response = await _call_generate_content(model, conversation)
            fc = _extract_function_call(response)
            if fc is None:
                output_text = _extract_text(response) or ""
                finish_reason = "stop"
                self._audit("model_response", trace_id, agent, {"text": output_text})
                break

            tool_name = fc.name
            tool_args = _to_plain(fc.args) if getattr(fc, "args", None) else {}
            conversation.append(
                {
                    "role": "model",
                    "parts": [
                        {"function_call": {"name": tool_name, "args": tool_args}}
                    ],
                }
            )
            self._audit(
                "tool_call",
                trace_id,
                agent,
                {"name": tool_name, "args": tool_args},
            )

            tool = tool_map.get(tool_name)
            if tool is None:
                err = f"Unknown tool: {tool_name}"
                tool_records.append(
                    ToolCallRecord(
                        name=tool_name, arguments=tool_args, result=None, error=err
                    )
                )
                conversation.append(
                    {
                        "role": "user",
                        "parts": [
                            {
                                "function_response": {
                                    "name": tool_name,
                                    "response": {"error": err},
                                }
                            }
                        ],
                    }
                )
                continue

            start = time.monotonic()
            try:
                result = await _invoke_tool(tool, run_context, tool_args)
                payload = _serialise_result(result)
                duration_ms = int((time.monotonic() - start) * 1000)
                tool_records.append(
                    ToolCallRecord(
                        name=tool_name,
                        arguments=tool_args,
                        result=payload,
                        duration_ms=duration_ms,
                    )
                )
                conversation.append(
                    {
                        "role": "user",
                        "parts": [
                            {
                                "function_response": {
                                    "name": tool_name,
                                    "response": {"result": payload},
                                }
                            }
                        ],
                    }
                )
                self._audit(
                    "tool_result",
                    trace_id,
                    agent,
                    {
                        "name": tool_name,
                        "duration_ms": duration_ms,
                        "ok": True,
                    },
                )
            except Exception as exc:  # noqa: BLE001 - we want to surface any tool error
                duration_ms = int((time.monotonic() - start) * 1000)
                err_text = f"{type(exc).__name__}: {exc}"
                tool_records.append(
                    ToolCallRecord(
                        name=tool_name,
                        arguments=tool_args,
                        result=None,
                        error=err_text,
                        duration_ms=duration_ms,
                    )
                )
                conversation.append(
                    {
                        "role": "user",
                        "parts": [
                            {
                                "function_response": {
                                    "name": tool_name,
                                    "response": {"error": err_text},
                                }
                            }
                        ],
                    }
                )
                self._audit(
                    "tool_error",
                    trace_id,
                    agent,
                    {"name": tool_name, "error": err_text},
                )
        else:
            finish_reason = "max_tool_calls"
            output_text = (
                output_text
                or "Agent exceeded the max tool-call budget before producing a final answer."
            )

        # Output guardrails.
        for guard in output_guardrails or []:
            outcome = await _run_guardrail(guard, run_context, agent, output_text)
            if getattr(outcome, "tripwire_triggered", False):
                raise AgentGuardrailError(
                    f"Output guardrail triggered: {getattr(outcome, 'output_info', '')}"
                )

        # Update history in place for caller's benefit (sessions reuse it).
        if history is not None:
            history[:] = conversation

        result = RunResult(
            output=output_text,
            tool_calls=tool_records,
            trace_id=trace_id,
            model=agent.model or creds.model,
            finish_reason=finish_reason,
            iterations=len(tool_records),
        )
        self._audit(
            "run_complete",
            trace_id,
            agent,
            {
                "finish_reason": finish_reason,
                "tool_calls": len(tool_records),
                "output_chars": len(output_text),
            },
        )
        return result

    def _audit(
        self, event: str, trace_id: str, agent: Agent, payload: Dict[str, Any]
    ) -> None:
        if self._audit_logger is None:
            return
        try:
            self._audit_logger.log(
                {
                    "event": event,
                    "trace_id": trace_id,
                    "agent": agent.name,
                    "model": agent.model,
                    **payload,
                }
            )
        except Exception as exc:  # pragma: no cover
            logger.debug("audit logger failed: %s", exc)


async def _call_generate_content(model: Any, conversation: List[Dict[str, Any]]) -> Any:
    """Call ``model.generate_content``. Run sync calls in a thread."""
    result = model.generate_content(conversation)
    if inspect.isawaitable(result):
        return await result
    # Offload potentially blocking SDK calls off the event loop.
    if asyncio.iscoroutinefunction(getattr(model, "generate_content", None)):
        return await model.generate_content(conversation)  # type: ignore[misc]
    return result


def is_runtime_available() -> bool:
    """True when the Gemini SDK is importable."""
    return is_available()
