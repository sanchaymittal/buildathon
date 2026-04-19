"""
API Package - FastAPI HTTP layer for Agentic DevOps.

This package provides HTTP endpoints for deploying repositories,
managing containers, and integrating with GitHub.
"""

from .app import app, run

__all__ = ["app", "run"]