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


@router.get("/tasks")
@limiter.limit("120/minute")
def list_tasks(
    request: Request,
    kb: str | None = Query(None, description="KB name; omit to span all KBs"),
    status: str | None = Query(None, description="Filter by status ('open' also matches unset)"),
    assignee: str | None = Query(None, description="Filter by assignee, e.g. 'mark'"),
    parent: str | None = Query(None, description="Filter by parent task id"),
    svc: TaskService = Depends(get_task_service),
):
    """List tasks across one KB or all of them.

    Exists so the human worklist board can ask one question -- "what is
    assigned to Mark, everywhere?" -- in a single call. TaskService.list_tasks
    already did this for the CLI; only the REST surface was missing.
    """
    tasks = svc.list_tasks(kb_name=kb, status=status, assignee=assignee, parent=parent)
    return {"count": len(tasks), "tasks": tasks}


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
