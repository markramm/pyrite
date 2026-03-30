"""Git operations endpoints: commit, push, pending changes, and publish for KBs."""

from fastapi import APIRouter, Body, Depends, HTTPException, Request

from ...exceptions import KBNotFoundError, PyriteError
from ...services.export_service import ExportService
from ...services.kb_service import KBService
from ..api import get_export_service, get_kb_service, limiter, requires_tier

router = APIRouter(tags=["Git Operations"])


@router.get("/kbs/{kb_name}/changes", dependencies=[Depends(requires_tier("read"))])
@limiter.limit("60/minute")
def get_pending_changes(
    request: Request,
    kb_name: str,
    svc: KBService = Depends(get_kb_service),
):
    """Get uncommitted changes in a KB as entry-level diffs."""
    try:
        return svc.get_pending_changes(kb_name)
    except KBNotFoundError:
        raise HTTPException(
            status_code=404, detail={"code": "NOT_FOUND", "message": f"KB '{kb_name}' not found"}
        )


@router.post("/kbs/{kb_name}/publish", dependencies=[Depends(requires_tier("admin"))])
@limiter.limit("30/minute")
def publish_changes(
    request: Request,
    kb_name: str,
    summary: str | None = Body(None, embed=True),
    svc: KBService = Depends(get_kb_service),
):
    """Commit and push all pending changes in a KB."""
    try:
        return svc.publish_changes(kb_name, summary=summary)
    except KBNotFoundError:
        raise HTTPException(
            status_code=404, detail={"code": "NOT_FOUND", "message": f"KB '{kb_name}' not found"}
        )
    except PyriteError as e:
        raise HTTPException(status_code=400, detail={"code": "PUBLISH_FAILED", "message": str(e)})


@router.post("/kbs/{kb_name}/commit", dependencies=[Depends(requires_tier("admin"))])
@limiter.limit("30/minute")
def commit_kb(
    request: Request,
    kb_name: str,
    message: str = Body(..., embed=True),
    paths: list[str] | None = Body(None, embed=True),
    sign_off: bool = Body(False, embed=True),
    export_svc: ExportService = Depends(get_export_service),
):
    """Commit changes in a KB's git repository."""
    try:
        result = export_svc.commit_kb(kb_name, message=message, paths=paths, sign_off=sign_off)
        return result
    except KBNotFoundError:
        raise HTTPException(
            status_code=404, detail={"code": "NOT_FOUND", "message": f"KB '{kb_name}' not found"}
        )
    except PyriteError as e:
        raise HTTPException(status_code=400, detail={"code": "COMMIT_FAILED", "message": str(e)})


@router.post("/kbs/{kb_name}/push", dependencies=[Depends(requires_tier("admin"))])
@limiter.limit("30/minute")
def push_kb(
    request: Request,
    kb_name: str,
    remote: str = Body("origin", embed=True),
    branch: str | None = Body(None, embed=True),
    export_svc: ExportService = Depends(get_export_service),
):
    """Push KB commits to a remote repository."""
    try:
        result = export_svc.push_kb(kb_name, remote=remote, branch=branch)
        return result
    except KBNotFoundError:
        raise HTTPException(
            status_code=404, detail={"code": "NOT_FOUND", "message": f"KB '{kb_name}' not found"}
        )
    except PyriteError as e:
        raise HTTPException(status_code=400, detail={"code": "PUSH_FAILED", "message": str(e)})
