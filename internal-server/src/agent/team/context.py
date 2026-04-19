"""
Shared state for the five-agent DevOps team.

Every tool and handoff in a team run sees the same :class:`TeamContext`
instance via ``RunContextWrapper``. Agents mutate it only through explicit
tool functions so the state is auditable and deterministic.
"""

from __future__ import annotations

import time
from enum import Enum
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class TeamRunStatus(str, Enum):
    planning = "planning"
    engineering = "engineering"
    security_review = "security_review"
    waiting_for_approval = "waiting_for_approval"
    deploying = "deploying"
    watching = "watching"
    succeeded = "succeeded"
    rolled_back = "rolled_back"
    failed = "failed"

    @property
    def is_terminal(self) -> bool:
        return self in (
            TeamRunStatus.succeeded,
            TeamRunStatus.rolled_back,
            TeamRunStatus.failed,
        )


_SEVERITY_ORDER = {
    "critical": 4,
    "high": 3,
    "medium": 2,
    "low": 1,
    "info": 0,
}


class SecurityFinding(BaseModel):
    """A single security finding produced by a scanner."""

    scanner: Literal["semgrep", "trivy", "gitleaks", "stub"]
    severity: Literal["info", "low", "medium", "high", "critical"]
    title: str
    file: Optional[str] = None
    line: Optional[int] = None
    details: Optional[str] = None

    @property
    def severity_rank(self) -> int:
        return _SEVERITY_ORDER[self.severity]

    def is_blocking(self) -> bool:
        return self.severity_rank >= _SEVERITY_ORDER["high"]


class RolloutState(BaseModel):
    """Blue/green rollout bookkeeping owned by Vector and observed by Sentry."""

    active_color: Literal["blue", "green", "none"] = "none"
    candidate_color: Optional[Literal["blue", "green"]] = None
    image_tag: Optional[str] = None
    project_base: Optional[str] = None
    rolled_back: bool = False

    def next_candidate_color(self) -> Literal["blue", "green"]:
        if self.active_color == "blue":
            return "green"
        return "blue"


class TeamContext(BaseModel):
    """Per-run shared state threaded through every agent and tool."""

    run_id: str
    user_id: str = "anonymous"
    task: str
    project_path: str

    branch: Optional[str] = None
    commit_sha: Optional[str] = None
    pr_ref: Optional[str] = None

    findings: List[SecurityFinding] = Field(default_factory=list)
    rollout: RolloutState = Field(default_factory=RolloutState)
    health_samples: List[dict] = Field(default_factory=list)

    status: TeamRunStatus = TeamRunStatus.planning
    approvals: Dict[str, bool] = Field(default_factory=dict)
    blocking_reason: Optional[str] = None
    notes: List[str] = Field(default_factory=list)

    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)

    # ----------------------------------------------------------------- helpers
    def set_status(self, status: TeamRunStatus, note: Optional[str] = None) -> None:
        self.status = status
        self.updated_at = time.time()
        if note:
            self.notes.append(f"[{status.value}] {note}")

    def add_note(self, note: str) -> None:
        self.notes.append(note)
        self.updated_at = time.time()

    def record_finding(self, finding: SecurityFinding) -> None:
        self.findings.append(finding)
        self.updated_at = time.time()

    def record_findings(self, findings: List[SecurityFinding]) -> None:
        self.findings.extend(findings)
        self.updated_at = time.time()

    def has_blocking_findings(self) -> bool:
        return any(f.is_blocking() for f in self.findings)

    def highest_severity(self) -> Optional[str]:
        if not self.findings:
            return None
        return max(self.findings, key=lambda f: f.severity_rank).severity

    def summary(self) -> dict:
        return {
            "run_id": self.run_id,
            "status": self.status.value,
            "task": self.task,
            "project_path": self.project_path,
            "branch": self.branch,
            "commit_sha": self.commit_sha,
            "pr_ref": self.pr_ref,
            "finding_count": len(self.findings),
            "highest_severity": self.highest_severity(),
            "rollout": self.rollout.model_dump(),
            "approvals": dict(self.approvals),
            "blocking_reason": self.blocking_reason,
            "notes": list(self.notes),
            "updated_at": self.updated_at,
        }
