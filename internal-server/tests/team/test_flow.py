"""End-to-end team flow tests with a scripted fake model.

The fake model replays pre-computed responses per agent name so we can
exercise the full Axiom -> Forge -> Warden -> Vector -> Sentry chain
without any real Gemini traffic or Docker daemon.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import pytest

from src.agent.team import (
    TeamExecutor,
    TeamRunStore,
    build_team,
)
from src.agent.team.context import TeamRunStatus
from src.gemini_agents.runner import GeminiRunner


pytestmark = pytest.mark.agent


# ---------------------------------------------------------------- Fake Gemini
@dataclass
class _FC:
    name: str
    args: Dict[str, Any]


@dataclass
class _Part:
    text: Optional[str] = None
    function_call: Optional[_FC] = None


@dataclass
class _Content:
    parts: List[_Part]


@dataclass
class _Candidate:
    content: _Content


@dataclass
class _Response:
    candidates: List[_Candidate]

    @property
    def text(self) -> str:
        for c in self.candidates:
            for p in c.content.parts:
                if p.text:
                    return p.text
        return ""


def _text(text: str) -> _Response:
    return _Response(
        candidates=[_Candidate(content=_Content(parts=[_Part(text=text)]))]
    )


def _fc(name: str, args: Dict[str, Any]) -> _Response:
    return _Response(
        candidates=[
            _Candidate(
                content=_Content(parts=[_Part(function_call=_FC(name=name, args=args))])
            )
        ]
    )


class _ScriptedModel:
    def __init__(self, script: List[_Response]) -> None:
        self._script = list(script)
        self.conversations: List[Any] = []

    def generate_content(self, conversation):
        self.conversations.append(conversation)
        if not self._script:
            raise AssertionError("Scripted model ran out of responses")
        return self._script.pop(0)


class _ScriptedRunner(GeminiRunner):
    """Runner that uses different scripts depending on the agent name."""

    def __init__(self, scripts: Dict[str, List[_Response]]):
        super().__init__(
            credentials=_FakeCreds(),
            max_tool_calls=32,
            model_factory=self._factory,
        )
        self._scripts = {k: list(v) for k, v in scripts.items()}

    def _factory(self, creds, model_override, tools, system_instruction):
        # Identify the agent by the first line of system_instruction which
        # always starts with "You are <Name>,".
        name = _agent_name_from_instruction(system_instruction)
        if name not in self._scripts:
            raise AssertionError(f"No script for agent '{name}'")
        return _ScriptedModel(self._scripts[name])


@dataclass
class _FakeCreds:
    api_key: str = "k"
    model: str = "gemini-2.5-pro"
    api_base: Optional[str] = None


def _agent_name_from_instruction(text: Optional[str]) -> str:
    if not text:
        return "?"
    first = text.strip().splitlines()[0]
    # "You are Axiom, the orchestrator..."
    for candidate in ("Axiom", "Forge", "Warden", "Vector", "Sentry"):
        if candidate in first:
            return candidate
    return "?"


# ---------------------------------------------------------------- Flows
@pytest.mark.asyncio
async def test_clean_pipeline_runs_to_success(tmp_path, mocker):
    # Avoid touching the real Docker daemon when peers reach for ComposeDeployService.
    mocker.patch(
        "src.docker_svc.compose_service.subprocess.run",
        return_value=_fake_compose_run(),
    )

    scripts = {
        "Axiom": [
            _fc("handoff_to_forge", {"task_spec": "Implement hello world"}),
            _fc("handoff_to_warden", {"task_spec": "Scan the diff"}),
            _fc("update_team_state", {"status": "deploying", "note": "post-security"}),
            _fc("handoff_to_vector", {"task_spec": "Roll out image abc123"}),
            _fc("handoff_to_sentry", {"task_spec": "Watch for 10s"}),
            _text("Pipeline complete; succeeded."),
        ],
        "Forge": [
            _fc("record_commit", {"sha": "abc123def456", "branch": "feature/hello"}),
            _text("Implemented hello world."),
        ],
        "Warden": [
            _fc("run_semgrep", {}),
            _fc("block_or_approve", {}),
            _text("No blocking findings."),
        ],
        "Vector": [
            _fc("build_image", {"tag": "abc123"}),
            _fc("rollout_bluegreen", {"color": "blue"}),
            _fc("switch_active", {"color": "blue"}),
            _text("Blue is active."),
        ],
        "Sentry": [
            _fc(
                "watch",
                {"window_s": 1, "interval_s": 1},
            ),
            _text("promote"),
        ],
    }
    runner = _ScriptedRunner(scripts)
    store = TeamRunStore()
    executor = TeamExecutor(
        store,
        team_factory=lambda: build_team(runner_factory=lambda: runner),
        runner_factory=lambda: runner,
    )

    run = store.create(task="Ship hello world", project_path=str(tmp_path), user_id="u")
    await executor.drive(run)

    assert run.context.commit_sha == "abc123def456"
    assert run.context.branch == "feature/hello"
    assert run.context.rollout.active_color == "blue"
    assert run.context.status in (
        TeamRunStatus.succeeded,
        TeamRunStatus.watching,
    )  # Axiom may finalise; either is acceptable given the last event.
    events = [e.event for e in run.events]
    assert "team_run_started" in events
    assert "team_run_finished" in events


@pytest.mark.asyncio
async def test_warden_blocking_pauses_run(tmp_path):
    # Plant a file with a high-severity pattern so the stub scanner fires.
    (tmp_path / "bad.py").write_text(
        'import subprocess\nsubprocess.run("ls", shell=True)\n'
    )

    scripts = {
        "Axiom": [
            _fc("handoff_to_forge", {"task_spec": "stub"}),
            _fc("handoff_to_warden", {"task_spec": "scan"}),
            # Axiom should detect block and request approval.
            _fc(
                "request_approval",
                {"gate": "pre_deploy", "reason": "Warden flagged high-severity"},
            ),
            _text("Paused for human approval."),
        ],
        "Forge": [_text("Forge stub: no-op")],
        "Warden": [
            # Call run_semgrep, then record_findings on its output, then decide.
            _fc("run_semgrep", {}),
            # The runner serialises the tool result into the following call
            # by way of the conversation history, so we can simply call
            # record_findings with a synthetic high-severity finding here.
            _fc(
                "record_findings",
                {
                    "findings": [
                        {
                            "scanner": "stub",
                            "severity": "high",
                            "title": "subprocess shell=True",
                        }
                    ]
                },
            ),
            _fc("block_or_approve", {}),
            _text("Blocking finding recorded."),
        ],
        # Peers below should never be called because Axiom's script stops.
        "Vector": [],
        "Sentry": [],
    }
    runner = _ScriptedRunner(scripts)
    store = TeamRunStore()
    executor = TeamExecutor(
        store,
        team_factory=lambda: build_team(runner_factory=lambda: runner),
        runner_factory=lambda: runner,
    )

    run = store.create(
        task="Ship risky change", project_path=str(tmp_path), user_id="u"
    )
    await executor.drive(run)

    assert run.context.status == TeamRunStatus.waiting_for_approval
    assert run.context.has_blocking_findings()
    assert any(
        "blocking" in n.lower() or "block" in n.lower() for n in run.context.notes
    )


@pytest.mark.asyncio
async def test_sentry_rolls_back_on_unhealthy_watch(tmp_path, mocker):
    # Force every compose ps to return an "unhealthy" snapshot.
    def _fake_run(cmd, *args, **kwargs):
        import subprocess

        stdout = ""
        if isinstance(cmd, list) and "ps" in cmd:
            stdout = '[{"Service": "web", "State": "exited", "Status": "Exit 1"}]'
        return subprocess.CompletedProcess(
            args=cmd, returncode=0, stdout=stdout, stderr=""
        )

    mocker.patch("src.docker_svc.compose_service.subprocess.run", side_effect=_fake_run)

    scripts = {
        "Axiom": [
            _fc("handoff_to_vector", {"task_spec": "Deploy"}),
            _fc("handoff_to_sentry", {"task_spec": "Watch quickly"}),
            _text("Sentry reported rollback."),
        ],
        "Vector": [
            _fc("build_image", {"tag": "xyz"}),
            _fc("rollout_bluegreen", {"color": "green"}),
            _text("Candidate deployed."),
        ],
        "Sentry": [
            _fc(
                "watch",
                {"window_s": 1, "interval_s": 1, "color": "green"},
            ),
            _fc(
                "trigger_rollback",
                {"reason": "unhealthy"},
            ),
            _text("Rolled back."),
        ],
        "Forge": [],
        "Warden": [],
    }
    runner = _ScriptedRunner(scripts)
    store = TeamRunStore()
    executor = TeamExecutor(
        store,
        team_factory=lambda: build_team(runner_factory=lambda: runner),
        runner_factory=lambda: runner,
    )

    run = store.create(
        task="Deploy unstable change", project_path=str(tmp_path), user_id="u"
    )
    await executor.drive(run)

    assert run.context.rollout.rolled_back is True
    assert run.context.status == TeamRunStatus.rolled_back


# ---------------------------------------------------------------- helpers
def _fake_compose_run():
    """Default compose.run() stub: everything succeeds with empty JSON ps."""
    import subprocess

    return subprocess.CompletedProcess(args=[], returncode=0, stdout="[]", stderr="")
