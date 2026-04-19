"""
Team Routes - FastAPI endpoints for the five-agent DevOps team.

  POST /team/runs                     kick off a new run
  GET  /team/runs                     list runs
  GET  /team/runs/{id}                run summary + current TeamContext
  GET  /team/runs/{id}/events         append-only event log
  POST /team/runs/{id}/approve        resume a waiting run
  POST /team/runs/{id}/reject         fail a waiting run
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ...agent.team import (
    TeamExecutor,
    TeamRunStore,
    execute_in_background,
    get_team_run_store,
)
from ...agent.team.context import TeamRunStatus
from ...core.credentials import CredentialError

router = APIRouter(prefix="/team", tags=["team"])


def get_store() -> TeamRunStore:
    return get_team_run_store()


def get_executor() -> TeamExecutor:
    # A fresh executor per request is cheap; it binds to the default store.
    return TeamExecutor(get_team_run_store())


# ---------------------------------------------------------------- models
class TeamRunCreate(BaseModel):
    task: str = Field(..., description="What the team should accomplish")
    project_path: str = Field(..., description="Local repo path for Forge / Vector")
    user_id: str = Field("anonymous", description="Caller identifier for audit")


class TeamRunSummary(BaseModel):
    run_id: str
    status: str
    task: str
    project_path: str
    branch: Optional[str] = None
    commit_sha: Optional[str] = None
    pr_ref: Optional[str] = None
    finding_count: int = 0
    highest_severity: Optional[str] = None
    rollout: Dict[str, Any] = {}
    approvals: Dict[str, bool] = {}
    blocking_reason: Optional[str] = None
    notes: List[str] = []
    updated_at: float = 0.0
    event_count: int = 0


class TeamEventOut(BaseModel):
    event: str
    timestamp: float
    payload: Dict[str, Any] = {}


class ApprovalRequest(BaseModel):
    gate: str
    reason: Optional[str] = None


# ---------------------------------------------------------------- helpers
def _summarise(run) -> TeamRunSummary:
    return TeamRunSummary(**run.summary())


def _events_out(run) -> List[TeamEventOut]:
    return [
        TeamEventOut(
            event=e.event,
            timestamp=e.timestamp,
            payload={k: v for k, v in e.payload.items()},
        )
        for e in run.events
    ]


def _error_to_http(exc: Exception) -> HTTPException:
    if isinstance(exc, CredentialError):
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Gemini credentials unavailable: {exc}",
        )
    if isinstance(exc, KeyError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc).strip("'"),
        )
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
    )


# ---------------------------------------------------------------- endpoints
@router.post(
    "/runs", response_model=TeamRunSummary, status_code=status.HTTP_202_ACCEPTED
)
async def create_team_run(
    request: TeamRunCreate,
    store: TeamRunStore = Depends(get_store),
    executor: TeamExecutor = Depends(get_executor),
) -> TeamRunSummary:
    """Kick off a team run. Returns immediately with ``status=planning``."""
    run = store.create(
        task=request.task,
        project_path=request.project_path,
        user_id=request.user_id,
    )
    await execute_in_background(executor, run)
    return _summarise(run)


@router.get("/runs", response_model=List[TeamRunSummary])
def list_team_runs(
    store: TeamRunStore = Depends(get_store),
) -> List[TeamRunSummary]:
    return [_summarise(r) for r in store.list()]


@router.get("/runs/{run_id}", response_model=TeamRunSummary)
def get_team_run(
    run_id: str, store: TeamRunStore = Depends(get_store)
) -> TeamRunSummary:
    try:
        run = store.require(run_id)
    except KeyError as exc:
        raise _error_to_http(exc)
    return _summarise(run)


@router.get("/runs/{run_id}/events", response_model=List[TeamEventOut])
def get_team_run_events(
    run_id: str, store: TeamRunStore = Depends(get_store)
) -> List[TeamEventOut]:
    try:
        run = store.require(run_id)
    except KeyError as exc:
        raise _error_to_http(exc)
    return _events_out(run)


@router.post("/runs/{run_id}/approve", response_model=TeamRunSummary)
async def approve_team_run(
    run_id: str,
    request: ApprovalRequest,
    store: TeamRunStore = Depends(get_store),
    executor: TeamExecutor = Depends(get_executor),
) -> TeamRunSummary:
    try:
        run = store.require(run_id)
    except KeyError as exc:
        raise _error_to_http(exc)
    if run.context.status != TeamRunStatus.waiting_for_approval:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Run is in status '{run.context.status.value}', not waiting "
                "for approval."
            ),
        )
    store.record_approval(run_id, request.gate, approved=True, reason=request.reason)
    # Resume in the background so the approval call returns promptly.
    import asyncio

    asyncio.create_task(executor.resume(run))
    return _summarise(run)


@router.post("/runs/{run_id}/reject", response_model=TeamRunSummary)
def reject_team_run(
    run_id: str,
    request: ApprovalRequest,
    store: TeamRunStore = Depends(get_store),
) -> TeamRunSummary:
    try:
        run = store.require(run_id)
    except KeyError as exc:
        raise _error_to_http(exc)
    if run.context.status != TeamRunStatus.waiting_for_approval:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Run is in status '{run.context.status.value}', not waiting "
                "for approval."
            ),
        )
    store.record_approval(run_id, request.gate, approved=False, reason=request.reason)
    return _summarise(run)
