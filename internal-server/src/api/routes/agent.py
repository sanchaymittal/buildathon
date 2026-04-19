"""
Agent Routes - FastAPI endpoints for the Gemini-backed DevOps agent.

Surface:

- ``POST /agent/run``                     one-shot prompt (no persisted session)
- ``POST /agent/sessions``                spawn a new session
- ``GET  /agent/sessions``                list sessions
- ``GET  /agent/sessions/{id}``           fetch session summary
- ``POST /agent/sessions/{id}/run``       run a prompt against a session
- ``DELETE /agent/sessions/{id}``         close a session
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ...agent import (
    AgentGuardrailError,
    AgentSessionStore,
    get_session_store,
)
from ...agent.sessions import AgentSession
from ...core.credentials import CredentialError

router = APIRouter(prefix="/agent", tags=["agent"])


def get_store() -> AgentSessionStore:
    return get_session_store()


# ---------------------------------------------------------------- Request/Response models
class AgentRunRequest(BaseModel):
    prompt: str = Field(..., description="User prompt")
    model: Optional[str] = Field(
        None, description="Override the Gemini model for this call"
    )
    user_id: str = Field("anonymous", description="Caller identifier for audit")


class AgentRunResponse(BaseModel):
    output: str
    tool_calls: List[Dict[str, Any]]
    trace_id: str
    model: str
    finish_reason: str
    iterations: int


class AgentSessionCreateRequest(BaseModel):
    user_id: str = Field("anonymous")
    model: Optional[str] = None
    environment: str = Field("dev")


class AgentSessionSummary(BaseModel):
    session_id: str
    agent: str
    model: Optional[str]
    user_id: str
    created_at: float
    last_used_at: float
    turns: int
    history_messages: int


class AgentSessionRunRequest(BaseModel):
    prompt: str = Field(..., description="User prompt")


# ---------------------------------------------------------------- Error helpers
def _run_error_to_http(exc: Exception) -> HTTPException:
    if isinstance(exc, CredentialError):
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Gemini credentials unavailable: {exc}",
        )
    if isinstance(exc, AgentGuardrailError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    if isinstance(exc, KeyError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc).strip("'")
        )
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
    )


def _session_to_summary(session: AgentSession) -> AgentSessionSummary:
    data = session.summary()
    return AgentSessionSummary(**data)


def _run_result_to_response(result: Any) -> AgentRunResponse:
    # ``result`` is ``RunResult`` (a dataclass with dataclass children).
    return AgentRunResponse(
        output=result.output,
        tool_calls=[asdict(tc) for tc in result.tool_calls],
        trace_id=result.trace_id,
        model=result.model,
        finish_reason=result.finish_reason,
        iterations=result.iterations,
    )


# ---------------------------------------------------------------- Endpoints
@router.post("/run", response_model=AgentRunResponse)
async def agent_run(
    request: AgentRunRequest,
    store: AgentSessionStore = Depends(get_store),
) -> AgentRunResponse:
    """Run a one-shot prompt against a fresh agent (no persisted session)."""
    try:
        result = await store.one_shot(
            request.prompt, user_id=request.user_id, model=request.model
        )
    except Exception as exc:  # noqa: BLE001
        raise _run_error_to_http(exc)
    return _run_result_to_response(result)


@router.post(
    "/sessions",
    response_model=AgentSessionSummary,
    status_code=status.HTTP_201_CREATED,
)
def create_session(
    request: AgentSessionCreateRequest,
    store: AgentSessionStore = Depends(get_store),
) -> AgentSessionSummary:
    """Spawn a new persistent agent session."""
    session = store.spawn(
        user_id=request.user_id,
        model=request.model,
        environment=request.environment,
    )
    return _session_to_summary(session)


@router.get("/sessions", response_model=List[AgentSessionSummary])
def list_sessions(
    store: AgentSessionStore = Depends(get_store),
) -> List[AgentSessionSummary]:
    """List all active sessions."""
    return [_session_to_summary(s) for s in store.list()]


@router.get("/sessions/{session_id}", response_model=AgentSessionSummary)
def get_session(
    session_id: str,
    store: AgentSessionStore = Depends(get_store),
) -> AgentSessionSummary:
    try:
        session = store.require(session_id)
    except KeyError as exc:
        raise _run_error_to_http(exc)
    return _session_to_summary(session)


@router.post("/sessions/{session_id}/run", response_model=AgentRunResponse)
async def run_session(
    session_id: str,
    request: AgentSessionRunRequest,
    store: AgentSessionStore = Depends(get_store),
) -> AgentRunResponse:
    """Run a prompt against an existing session."""
    try:
        result = await store.run(session_id, request.prompt)
    except Exception as exc:  # noqa: BLE001
        raise _run_error_to_http(exc)
    return _run_result_to_response(result)


@router.delete("/sessions/{session_id}")
def close_session(
    session_id: str,
    store: AgentSessionStore = Depends(get_store),
) -> Dict[str, Any]:
    if not store.close(session_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {session_id}",
        )
    return {"status": "closed", "session_id": session_id}
