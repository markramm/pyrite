"""Admin endpoints: stats, index sync, AI status."""

from fastapi import APIRouter, Depends, Request

from ...services.llm_service import LLMService
from ...storage.index import IndexManager
from ..api import get_index_mgr, get_llm_service, limiter
from ..schemas import AIStatusResponse, StatsResponse, SyncResponse

router = APIRouter(tags=["Admin"])


@router.get("/stats", response_model=StatsResponse)
@limiter.limit("100/minute")
def get_stats(request: Request, index_mgr: IndexManager = Depends(get_index_mgr)):
    """Get index statistics."""
    stats = index_mgr.get_index_stats()
    return StatsResponse(**stats)


@router.post("/index/sync", response_model=SyncResponse)
@limiter.limit("30/minute")
def sync_index(request: Request, index_mgr: IndexManager = Depends(get_index_mgr)):
    """Trigger incremental index sync."""
    result = index_mgr.sync_incremental()
    return SyncResponse(
        synced=True,
        added=result.get("added", 0),
        updated=result.get("updated", 0),
        removed=result.get("removed", 0),
    )


@router.get("/ai/status", response_model=AIStatusResponse)
@limiter.limit("100/minute")
def ai_status(request: Request, llm: LLMService = Depends(get_llm_service)):
    """Return AI/LLM configuration status."""
    status = llm.status()
    return AIStatusResponse(**status)
