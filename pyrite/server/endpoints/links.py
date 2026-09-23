"""Cross-KB link discovery endpoints.

mcp-rest-tool-parity: ports kb_discover_neighbors and kb_batch_suggest
from MCP-only (pyrite/server/mcp_server.py) to REST. Both share the
same LinkDiscoveryService methods the MCP handlers already call --
no service-layer duplication.
"""

from fastapi import APIRouter, Depends, Query, Request

from ...services.link_discovery_service import LinkDiscoveryService
from ..api import get_link_discovery_service, get_readable_kbs, limiter, requires_kb_read

router = APIRouter(tags=["Links"])


@router.get("/links/discover-neighbors", dependencies=[Depends(requires_kb_read())])
@limiter.limit("60/minute")
def discover_neighbors(
    request: Request,
    entry_id: str = Query(..., description="Entry to find neighbors for"),
    kb: str = Query(..., description="KB the entry belongs to"),
    target_kb: str | None = Query(
        None, description="Limit candidates to this KB; omit to include the source KB and others"
    ),
    limit: int = Query(10, ge=1, le=100),
    mode: str = Query("hybrid", description="Search mode: keyword, semantic, hybrid"),
    exclude_linked: bool = Query(True, description="Exclude entries already linked"),
    svc: LinkDiscoveryService = Depends(get_link_discovery_service),
    readable: set[str] | None = Depends(get_readable_kbs),
):
    """Find related entries across all KBs, including the source KB by default.

    Excludes the source entry and, by default, already-linked entries.

    `requires_kb_read()` refuses any KB this call names that the caller may
    not read; `readable` keeps the *candidates* to readable KBs as well.
    With `target_kb` omitted the search spans the index, so the second half
    is what stops a readable KB's entry being matched against a private
    KB's entry and handed back as a suggestion (#186).
    """
    candidates = svc.discover_neighbors(
        entry_id=entry_id,
        kb_name=kb,
        target_kb=target_kb,
        limit=limit,
        mode=mode,
        exclude_linked=exclude_linked,
        readable_kbs=readable,
    )

    return {
        "entry_id": entry_id,
        "kb_name": kb,
        "count": len(candidates),
        "discoveries": candidates,
    }


@router.get("/links/batch-suggest", dependencies=[Depends(requires_kb_read())])
@limiter.limit("20/minute")
def batch_suggest(
    request: Request,
    source_kb: str = Query(..., description="Source KB"),
    target_kb: str = Query(..., description="Target KB to compare against"),
    limit_per_entry: int = Query(3, ge=1, le=20),
    mode: str = Query("keyword", description="Search mode: keyword, semantic, hybrid"),
    exclude_linked: bool = Query(True, description="Exclude entries already linked"),
    svc: LinkDiscoveryService = Depends(get_link_discovery_service),
    readable: set[str] | None = Depends(get_readable_kbs),
):
    """Batch-compare two KBs to find potential cross-KB links."""
    pairs = svc.batch_suggest(
        source_kb=source_kb,
        target_kb=target_kb,
        limit_per_entry=limit_per_entry,
        mode=mode,
        exclude_linked=exclude_linked,
        readable_kbs=readable,
    )

    return {
        "source_kb": source_kb,
        "target_kb": target_kb,
        "count": len(pairs),
        "pairs": pairs,
    }
