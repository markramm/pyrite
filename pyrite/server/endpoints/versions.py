"""Entry version history endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from ...services.version_service import VersionService
from ..api import get_version_service, limiter
from ..schemas import EntryVersionResponse, VersionListResponse

router = APIRouter(tags=["Versions"])


@router.get("/entries/{entry_id}/versions", response_model=VersionListResponse)
@limiter.limit("100/minute")
def get_entry_versions(
    request: Request,
    entry_id: str,
    kb: str = Query(..., description="KB name"),
    limit: int = Query(50, ge=1, le=200),
    version_svc: VersionService = Depends(get_version_service),
):
    """Get version history for an entry."""
    versions = version_svc.get_entry_versions(entry_id, kb, limit=limit)
    version_models = [EntryVersionResponse(**v) for v in versions]
    return VersionListResponse(
        entry_id=entry_id,
        kb_name=kb,
        count=len(version_models),
        versions=version_models,
    )


@router.get("/entries/{entry_id}/versions/{commit_hash}")
@limiter.limit("100/minute")
def get_entry_at_version(
    request: Request,
    entry_id: str,
    commit_hash: str,
    kb: str = Query(..., description="KB name"),
    version_svc: VersionService = Depends(get_version_service),
):
    """Get entry content at a specific git commit."""
    content = version_svc.get_entry_at_version(entry_id, kb, commit_hash)
    if content is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "NOT_FOUND",
                "message": f"Version {commit_hash} not found for entry '{entry_id}'",
            },
        )
    return {
        "entry_id": entry_id,
        "kb_name": kb,
        "commit_hash": commit_hash,
        "content": content,
    }
