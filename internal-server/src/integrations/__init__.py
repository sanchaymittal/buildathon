"""External integration adapters for the DevOps team.

MVP ships only :class:`NullAdapter` implementations that write to the
shared audit log. Real adapters can drop in later without touching the
agents that depend on them.
"""

from .base import IntegrationAdapter, NullAdapter
from .linear import LinearAdapter, NullLinearAdapter, linear_create_issue
from .slack import SlackAdapter, NullSlackAdapter, slack_post
from .pagerduty import (
    NullPagerDutyAdapter,
    PagerDutyAdapter,
    pagerduty_trigger,
)
from .github_pr import NullGitHubPRAdapter, GitHubPRAdapter, github_comment

__all__ = [
    "IntegrationAdapter",
    "NullAdapter",
    "LinearAdapter",
    "NullLinearAdapter",
    "linear_create_issue",
    "SlackAdapter",
    "NullSlackAdapter",
    "slack_post",
    "PagerDutyAdapter",
    "NullPagerDutyAdapter",
    "pagerduty_trigger",
    "GitHubPRAdapter",
    "NullGitHubPRAdapter",
    "github_comment",
]
