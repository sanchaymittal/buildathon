"""
TeamExecutor - coordinates a single :class:`TeamRun`.

Responsibilities:

- Build the five-agent team.
- Kick off an Axiom run in the background.
- Record structured events on the ``TeamRunStore`` as the run progresses.
- Pause cleanly when Axiom (or a peer) flips the run to
  ``waiting_for_approval``; resume when the HTTP layer records an approval.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Optional

from ...gemini_agents import Agent
from ...gemini_agents.runner import GeminiRunner, RunResult
from ..audit import AuditLogger, get_default_audit_logger
from .build import Team, build_team
from .context import TeamRunStatus
from .runs import TeamRun, TeamRunStore

logger = logging.getLogger(__name__)


RunnerFactory = Callable[[], Any]
TeamFactory = Callable[[], Team]


class TeamExecutor:
    """Drives the Axiom -> peers pipeline for a single run."""

    def __init__(
        self,
        store: TeamRunStore,
        *,
        team_factory: Optional[TeamFactory] = None,
        runner_factory: Optional[RunnerFactory] = None,
        audit_logger: Optional[AuditLogger] = None,
    ) -> None:
        self._store = store
        self._team_factory = team_factory or (
            lambda: build_team(runner_factory=runner_factory)
        )
        self._runner_factory = runner_factory or (
            lambda: GeminiRunner(max_tool_calls=24)
        )
        self._audit = audit_logger or get_default_audit_logger()
        self._resumptions: dict[str, asyncio.Event] = {}

    # ------------------------------------------------------------------ public
    async def drive(self, run: TeamRun) -> RunResult:
        """Run the Axiom-driven pipeline to completion (or pause)."""
        async with run.lock:
            self._store.record_event(run, "team_run_started", {})
            team = self._team_factory()
            runner = self._runner_factory()
            prompt = self._axiom_prompt(run)
            return await self._run_axiom(run, team.axiom, runner, prompt)

    async def resume(self, run: TeamRun) -> RunResult:
        """Resume after an approval has been recorded on the run."""
        async with run.lock:
            self._store.record_event(run, "team_run_resumed", {})
            team = self._team_factory()
            runner = self._runner_factory()
            prompt = self._axiom_resume_prompt(run)
            return await self._run_axiom(run, team.axiom, runner, prompt)

    # ----------------------------------------------------------------- helpers
    async def _run_axiom(
        self, run: TeamRun, axiom: Agent, runner: Any, prompt: str
    ) -> RunResult:
        try:
            result = await runner.run(axiom, prompt, context=run.context)
        except Exception as exc:  # noqa: BLE001
            run.context.set_status(
                TeamRunStatus.failed, note=f"Axiom crashed: {type(exc).__name__}: {exc}"
            )
            self._store.record_event(
                run,
                "team_run_failed",
                {"error": f"{type(exc).__name__}: {exc}"},
            )
            raise

        self._store.record_event(
            run,
            "team_run_finished",
            {
                "status": run.context.status.value,
                "finish_reason": result.finish_reason,
                "tool_calls": len(result.tool_calls),
                "output_chars": len(result.output),
            },
        )
        # If Axiom's run ended without pausing and without flipping to
        # a terminal state, promote to ``succeeded`` as the default.
        if run.context.status not in (
            TeamRunStatus.waiting_for_approval,
            TeamRunStatus.succeeded,
            TeamRunStatus.rolled_back,
            TeamRunStatus.failed,
        ):
            run.context.set_status(
                TeamRunStatus.succeeded, note="Axiom concluded without blocking"
            )
        return result

    @staticmethod
    def _axiom_prompt(run: TeamRun) -> str:
        ctx = run.context
        return (
            f"Task: {ctx.task}\n"
            f"Project path: {ctx.project_path}\n"
            f"Run id: {ctx.run_id}\n\n"
            "Decompose the task and drive the team. Start with a Forge "
            "handoff unless the task is purely operational. Stop and call "
            "request_approval if Warden records blocking findings."
        )

    @staticmethod
    def _axiom_resume_prompt(run: TeamRun) -> str:
        ctx = run.context
        approved_gates = [g for g, ok in ctx.approvals.items() if ok]
        rejected_gates = [g for g, ok in ctx.approvals.items() if not ok]
        return (
            f"The run '{ctx.run_id}' was previously paused at "
            f"'{ctx.blocking_reason or 'unknown'}' and has now resumed.\n"
            f"Approved gates: {approved_gates or 'none'}\n"
            f"Rejected gates: {rejected_gates or 'none'}\n\n"
            "Continue the pipeline. Delegate to Vector and Sentry if you "
            "had not already done so. Respect any rejections by finalising "
            "the run as failed with a short summary."
        )


async def execute_in_background(
    executor: TeamExecutor,
    run: TeamRun,
    *,
    on_done: Optional[Callable[[TeamRun], None]] = None,
) -> asyncio.Task:
    """Schedule ``executor.drive(run)`` as a background task."""

    async def _runner():
        try:
            await executor.drive(run)
        finally:
            if on_done:
                try:
                    on_done(run)
                except Exception as exc:  # pragma: no cover
                    logger.debug("on_done hook raised: %s", exc)

    task = asyncio.create_task(_runner())
    run.task_handle = task
    return task
