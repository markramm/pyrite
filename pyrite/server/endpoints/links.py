"""Cross-KB link discovery endpoints.

mcp-rest-tool-parity: ports kb_discover_neighbors and kb_batch_suggest
from MCP-only (pyrite/server/mcp_server.py) to REST. Both share the
same LinkDiscoveryService methods the MCP handlers already call --
no service-layer duplication.
"""

from fastapi import APIRouter, Depends, Query, Request

from ...services.link_discovery_service import LinkDiscoveryService
from ..api import get_link_discovery_service, limiter

router = APIRouter(tags=["Links"])


@router.get("/links/discover-neighbors")
@limiter.limit("60/minute")
def discover_neighbors(
    request: Request,
    entry_id: str = Query(..., description="Entry to find neighbors for"),
    kb: str = Query(..., description="KB the entry belongs to"),
    target_kb: str | None = Query(None, description="Limit candidates to this KB"),
    limit: int = Query(10, ge=1, le=100),
    mode: str = Query("hybrid", description="Search mode: keyword, semantic, hybrid"),
    exclude_linked: bool = Query(True, description="Exclude entries already linked"),
    svc: LinkDiscoveryService = Depends(get_link_discovery_service),
):
    """Find semantically similar but unlinked entries across KBs."""
    candidates = svc.discover_neighbors(
        entry_id=entry_id,
        kb_name=kb,
        target_kb=target_kb,
        limit=limit,
        mode=mode,
        exclude_linked=exclude_linked,
    )

    return {
        "entry_id": entry_id,
        "kb_name": kb,
        "count": len(candidates),
        "discoveries": candidates,
    }


@router.get("/links/batch-suggest")
@limiter.limit("20/minute")
def batch_suggest(
    request: Request,
    source_kb: str = Query(..., description="Source KB"),
    target_kb: str = Query(..., description="Target KB to compare against"),
    limit_per_entry: int = Query(3, ge=1, le=20),
    mode: str = Query("keyword", description="Search mode: keyword, semantic, hybrid"),
    exclude_linked: bool = Query(True, description="Exclude entries already linked"),
    svc: LinkDiscoveryService = Depends(get_link_discovery_service),
):
    """Batch-compare two KBs to find potential cross-KB links."""
    pairs = svc.batch_suggest(
        source_kb=source_kb,
        target_kb=target_kb,
        limit_per_entry=limit_per_entry,
        mode=mode,
        exclude_linked=exclude_linked,
    )

    return {
        "source_kb": source_kb,
        "target_kb": target_kb,
        "count": len(pairs),
        "pairs": pairs,
    }
