"""Git operations endpoints: commit and push for KBs."""

from fastapi import APIRouter, Body, Depends, HTTPException, Request

from ...exceptions import KBNotFoundError, PyriteError
from ...services.kb_service import KBService
from ..api import get_kb_service, limiter, requires_tier

router = APIRouter(tags=["Git Operations"], dependencies=[Depends(requires_tier("admin"))])


@router.post("/kbs/{kb_name}/commit")
@limiter.limit("30/minute")
def commit_kb(
    request: Request,
    kb_name: str,
    message: str = Body(..., embed=True),
    paths: list[str] | None = Body(None, embed=True),
    sign_off: bool = Body(False, embed=True),
    svc: KBService = Depends(get_kb_service),
):
    """Commit changes in a KB's git repository."""
    try:
        result = svc.commit_kb(kb_name, message=message, paths=paths, sign_off=sign_off)
        return result
    except KBNotFoundError:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": f"KB '{kb_name}' not found"})
    except PyriteError as e:
        raise HTTPException(status_code=400, detail={"code": "COMMIT_FAILED", "message": str(e)})


@router.post("/kbs/{kb_name}/push")
@limiter.limit("30/minute")
def push_kb(
    request: Request,
    kb_name: str,
    remote: str = Body("origin", embed=True),
    branch: str | None = Body(None, embed=True),
    svc: KBService = Depends(get_kb_service),
):
    """Push KB commits to a remote repository."""
    try:
        result = svc.push_kb(kb_name, remote=remote, branch=branch)
        return result
    except KBNotFoundError:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": f"KB '{kb_name}' not found"})
    except PyriteError as e:
        raise HTTPException(status_code=400, detail={"code": "PUSH_FAILED", "message": str(e)})
