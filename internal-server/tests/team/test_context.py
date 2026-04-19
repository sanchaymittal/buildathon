"""Tests for TeamContext."""

from __future__ import annotations

import pytest

from src.agent.team.context import (
    RolloutState,
    SecurityFinding,
    TeamContext,
    TeamRunStatus,
)


pytestmark = pytest.mark.agent


def _ctx(**overrides) -> TeamContext:
    return TeamContext(
        run_id=overrides.pop("run_id", "r-1"),
        task=overrides.pop("task", "deploy sample-app"),
        project_path=overrides.pop("project_path", "/tmp/app"),
        **overrides,
    )


class TestStatusTransitions:
    def test_default_status_is_planning(self):
        assert _ctx().status == TeamRunStatus.planning

    def test_set_status_records_note(self):
        c = _ctx()
        c.set_status(TeamRunStatus.engineering, note="Forge kicked off")
        assert c.status == TeamRunStatus.engineering
        assert any("engineering" in n for n in c.notes)

    def test_terminal_states(self):
        assert TeamRunStatus.succeeded.is_terminal
        assert TeamRunStatus.rolled_back.is_terminal
        assert TeamRunStatus.failed.is_terminal
        assert not TeamRunStatus.planning.is_terminal
        assert not TeamRunStatus.waiting_for_approval.is_terminal


class TestFindings:
    def test_record_finding_increments(self):
        c = _ctx()
        c.record_finding(SecurityFinding(scanner="stub", severity="medium", title="hi"))
        assert len(c.findings) == 1

    def test_blocking_detection(self):
        c = _ctx()
        c.record_findings(
            [
                SecurityFinding(scanner="stub", severity="low", title="1"),
                SecurityFinding(scanner="stub", severity="high", title="2"),
            ]
        )
        assert c.has_blocking_findings() is True
        assert c.highest_severity() == "high"

    def test_no_findings_no_severity(self):
        c = _ctx()
        assert c.highest_severity() is None
        assert c.has_blocking_findings() is False


class TestRolloutState:
    def test_next_candidate_defaults_to_blue(self):
        s = RolloutState()
        assert s.next_candidate_color() == "blue"

    def test_next_candidate_flips_from_blue_to_green(self):
        s = RolloutState(active_color="blue")
        assert s.next_candidate_color() == "green"

    def test_next_candidate_flips_from_green_to_blue(self):
        s = RolloutState(active_color="green")
        assert s.next_candidate_color() == "blue"


class TestSummary:
    def test_summary_shape(self):
        c = _ctx()
        c.set_status(TeamRunStatus.engineering, note="hi")
        c.record_finding(SecurityFinding(scanner="stub", severity="high", title="oops"))
        s = c.summary()
        assert s["run_id"] == "r-1"
        assert s["status"] == "engineering"
        assert s["finding_count"] == 1
        assert s["highest_severity"] == "high"
