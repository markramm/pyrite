"""Task claim endpoint.

mcp-rest-tool-parity: ports task_claim (atomic task claim used by the
conductor pattern) from MCP-only (pyrite/server/mcp_server.py) to
REST. Shares the same TaskService.claim_task call the MCP handler
already uses -- no service-layer duplication.
"""

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel

from ...services.task_service import TaskService
from ..api import get_task_service, limiter, requires_kb_tier

router = APIRouter(tags=["Tasks"])


class TaskClaimRequest(BaseModel):
    """Request body for claiming a task."""

    assignee: str


@router.post("/tasks/{task_id}/claim", dependencies=[Depends(requires_kb_tier("write"))])
@limiter.limit("60/minute")
def claim_task(
    request: Request,
    task_id: str,
    req: TaskClaimRequest,
    kb: str = Query(..., description="KB the task belongs to"),
    svc: TaskService = Depends(get_task_service),
):
    """Atomically claim an open task. Returns claimed=False (not an HTTP
    error) for expected non-claim outcomes -- already claimed, or the
    task doesn't exist -- matching the underlying CAS's own contract
    (see KBService.claim_entry)."""
    return svc.claim_task(task_id=task_id, kb_name=kb, assignee=req.assignee)
