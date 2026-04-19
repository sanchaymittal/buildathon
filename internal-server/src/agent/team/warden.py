"""Warden - security engineer.

Runs SAST / secrets / deps scans on every PR. Deterministic-first: the
final block/approve decision is a pure function of ``TeamContext.findings``.
"""

from __future__ import annotations

from typing import Any, List

from ...gemini_agents import Agent, function_tool, RunContextWrapper
from ...tooling import scanners as scanner_tools
from .context import SecurityFinding, TeamContext, TeamRunStatus

WARDEN_SYSTEM_PROMPT = """\
You are Warden, the security engineer.

You run scanners on the current project and feed their findings into the
shared TeamContext. Your final decision is deterministic: any finding at
severity >= high triggers a block and requests a human approval gate.

Workflow:
  1. run_semgrep, run_gitleaks, run_trivy (in any order).
  2. record_findings (converts scanner JSON into TeamContext.findings).
  3. block_or_approve makes the final call. If blocking, it pauses the run
     by setting status = waiting_for_approval.

Never invent findings. Never rewrite severities. Trust the scanners; your
job is triage and escalation.
"""


def _ensure_path(ctx: RunContextWrapper[TeamContext]) -> str:
    team = ctx.context
    if team is None or not team.project_path:
        raise RuntimeError("Warden requires TeamContext.project_path to be set")
    return team.project_path


def _run_semgrep_tool():
    @function_tool()
    async def run_semgrep(ctx: RunContextWrapper[TeamContext]) -> dict:
        """Run semgrep (or the deterministic stub) on the project."""
        path = _ensure_path(ctx)
        findings = scanner_tools.run_semgrep(path)
        return {
            "scanner": "semgrep",
            "findings": findings,
            "summary": scanner_tools.summarise(findings),
        }

    return run_semgrep


def _run_trivy_tool():
    @function_tool()
    async def run_trivy(ctx: RunContextWrapper[TeamContext]) -> dict:
        """Run trivy (or the deterministic stub) on the project."""
        path = _ensure_path(ctx)
        findings = scanner_tools.run_trivy(path)
        return {
            "scanner": "trivy",
            "findings": findings,
            "summary": scanner_tools.summarise(findings),
        }

    return run_trivy


def _run_gitleaks_tool():
    @function_tool()
    async def run_gitleaks(ctx: RunContextWrapper[TeamContext]) -> dict:
        """Run gitleaks (or the deterministic stub) on the project."""
        path = _ensure_path(ctx)
        findings = scanner_tools.run_gitleaks(path)
        return {
            "scanner": "gitleaks",
            "findings": findings,
            "summary": scanner_tools.summarise(findings),
        }

    return run_gitleaks


def _record_findings_tool():
    @function_tool()
    async def record_findings(
        ctx: RunContextWrapper[TeamContext], findings: List[dict]
    ) -> dict:
        """Append findings to the shared TeamContext."""
        team = ctx.context
        kept: List[SecurityFinding] = []
        for item in findings or []:
            try:
                kept.append(SecurityFinding.model_validate(item))
            except Exception as exc:  # noqa: BLE001 - surface invalid findings
                team.add_note(f"Warden dropped malformed finding: {exc}")
                continue
        team.record_findings(kept)
        return {
            "added": len(kept),
            "total": len(team.findings),
            "highest_severity": team.highest_severity(),
        }

    return record_findings


def _block_or_approve_tool():
    @function_tool()
    async def block_or_approve(ctx: RunContextWrapper[TeamContext]) -> dict:
        """Deterministic decision based on the current TeamContext.findings.

        If there is any finding with severity >= high, the run is paused at
        the ``pre_deploy`` gate. Otherwise security review is marked
        successful.
        """
        team = ctx.context
        if team.has_blocking_findings():
            team.blocking_reason = (
                f"Warden found {sum(1 for f in team.findings if f.is_blocking())} "
                f"blocking finding(s); highest severity={team.highest_severity()}"
            )
            team.set_status(
                TeamRunStatus.waiting_for_approval,
                note=team.blocking_reason,
            )
            return {
                "decision": "block",
                "gate": "pre_deploy",
                "blocking_count": sum(1 for f in team.findings if f.is_blocking()),
                "highest_severity": team.highest_severity(),
            }
        team.set_status(
            TeamRunStatus.security_review,
            note="Warden approved the change (no blocking findings).",
        )
        return {
            "decision": "approve",
            "blocking_count": 0,
            "highest_severity": team.highest_severity(),
        }

    return block_or_approve


def build_warden(*, model: str = "gemini-2.5-pro") -> Agent:
    tools: List[Any] = [
        _run_semgrep_tool(),
        _run_trivy_tool(),
        _run_gitleaks_tool(),
        _record_findings_tool(),
        _block_or_approve_tool(),
    ]
    return Agent(
        name="Warden",
        instructions=WARDEN_SYSTEM_PROMPT,
        tools=tools,
        model=model,
    )
