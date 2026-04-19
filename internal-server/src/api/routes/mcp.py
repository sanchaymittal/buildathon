"""MCP Routes - Minimal Model Context Protocol adapter."""

import uuid

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, Field

from ...docker_svc import DeployRequest, DeployUserRequest, Deployment, DeploymentTicket
from ...docker_svc.base import DockerServiceError
from ...core.credentials import get_credential_manager
from ..dependencies import get_deploy_service


router = APIRouter(prefix="/mcp", tags=["mcp"])


class ToolCallRequest(BaseModel):
    """MCP tool call payload."""

    name: str = Field(description="Tool name")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Tool arguments")


class ToolCallResponse(BaseModel):
    """MCP tool call response payload."""

    result: Any
    is_error: bool = False


class DeploymentIdInput(BaseModel):
    deploy_id: str = Field(description="Deployment identifier")
    user_id: str = Field(description="User identifier for access validation")


class DeploymentLogsInput(DeploymentIdInput):
    tail: int = Field(default=100, description="Number of log lines")


def _ensure_user_access(deployment: Deployment, user_id: str) -> None:
    if deployment.user_id and deployment.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Deployment does not belong to the provided user_id",
        )


def _get_github_token() -> Optional[str]:
    try:
        cred_manager = get_credential_manager()
        creds = cred_manager.get_github_credentials()
        return creds.token
    except Exception:
        return None


def _tool_schemas() -> List[Dict[str, Any]]:
    deploy_input_schema = DeployUserRequest.model_json_schema()
    deployment_output_schema = Deployment.model_json_schema()
    ticket_output_schema = DeploymentTicket.model_json_schema()

    return [
        {
            "name": "deploy_quick",
            "description": "Deploy a GitHub repo with user_id segregation.",
            "input_schema": deploy_input_schema,
            "output_schema": deployment_output_schema,
        },
        {
            "name": "deploy_replace",
            "description": "Delete prior repo+user deployment and deploy again.",
            "input_schema": deploy_input_schema,
            "output_schema": ticket_output_schema,
        },
        {
            "name": "deploy_status",
            "description": "Get deployment status by deploy_id.",
            "input_schema": DeploymentIdInput.model_json_schema(),
            "output_schema": deployment_output_schema,
        },
        {
            "name": "deploy_logs",
            "description": "Fetch deployment logs by deploy_id.",
            "input_schema": DeploymentLogsInput.model_json_schema(),
            "output_schema": {
                "type": "object",
                "properties": {
                    "deploy_id": {"type": "string"},
                    "logs": {"type": "string"},
                },
                "required": ["deploy_id", "logs"],
            },
        },
        {
            "name": "deploy_down",
            "description": "Remove a deployment by deploy_id.",
            "input_schema": DeploymentIdInput.model_json_schema(),
            "output_schema": {
                "type": "object",
                "properties": {
                    "status": {"type": "string"},
                    "deployment_id": {"type": "string"},
                },
                "required": ["status", "deployment_id"],
            },
        },
    ]


@router.post("/tools/list")
def list_tools() -> Dict[str, Any]:
    """List MCP tools exposed by this service."""

    return {"tools": _tool_schemas()}


@router.post("/tools/call", response_model=ToolCallResponse)
def call_tool(
    payload: ToolCallRequest,
    background_tasks: BackgroundTasks,
    deploy_service=Depends(get_deploy_service),
) -> ToolCallResponse:
    """Invoke an MCP tool call."""

    try:
        if payload.name == "deploy_quick":
            request = DeployUserRequest(**payload.arguments)
            deploy_request = DeployRequest(
                repository=request.repository,
                branch=request.branch,
            )
            deployment = deploy_service.deploy_from_github(
                deploy_request,
                github_token=request.github_token or _get_github_token(),
                user_id=request.user_id,
            )
            return ToolCallResponse(result=deployment)

        if payload.name == "deploy_status":
            request = DeploymentIdInput(**payload.arguments)
            deployment = deploy_service.get_deployment(request.deploy_id)
            _ensure_user_access(deployment, request.user_id)
            return ToolCallResponse(result=deployment)

        if payload.name == "deploy_replace":
            request = DeployUserRequest(**payload.arguments)
            deploy_request = DeployRequest(
                repository=request.repository,
                branch=request.branch,
            )
            token = request.github_token or _get_github_token()

            existing = [
                deployment
                for deployment in deploy_service.deployments.values()
                if deployment.repository == request.repository
                and deployment.user_id == request.user_id
            ]
            for deployment in existing:
                try:
                    deploy_service.remove_deployment(deployment.id)
                except Exception:
                    pass

            deploy_id = str(uuid.uuid4())[:8]
            pending = deploy_service.create_pending_deployment(
                deploy_request,
                user_id=request.user_id,
                deploy_id=deploy_id,
            )

            background_tasks.add_task(
                deploy_service.finalize_pending_deployment,
                deploy_request,
                request.user_id,
                pending.id,
                token,
                pending.host_port,
            )

            ticket = DeploymentTicket(
                id=pending.id,
                user_id=pending.user_id,
                repository=pending.repository,
                branch=pending.branch,
                status=pending.status,
                url=pending.url,
            )
            return ToolCallResponse(result=ticket)

        if payload.name == "deploy_logs":
            request = DeploymentLogsInput(**payload.arguments)
            deployment = deploy_service.get_deployment(request.deploy_id)
            _ensure_user_access(deployment, request.user_id)
            logs = deploy_service.get_deployment_logs(request.deploy_id, request.tail)
            return ToolCallResponse(result={"deploy_id": request.deploy_id, "logs": logs})

        if payload.name == "deploy_down":
            request = DeploymentIdInput(**payload.arguments)
            deployment = deploy_service.get_deployment(request.deploy_id)
            _ensure_user_access(deployment, request.user_id)
            result = deploy_service.remove_deployment(request.deploy_id)
            return ToolCallResponse(result=result)

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown tool: {payload.name}",
        )
    except DockerServiceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
