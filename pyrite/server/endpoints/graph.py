"""Graph visualization endpoint."""

from fastapi import APIRouter, Depends, Query, Request

from ...services.kb_service import KBService
from ..api import get_kb_service, limiter
from ..schemas import GraphEdge, GraphNode, GraphResponse

router = APIRouter(tags=["Graph"])


@router.get("/graph", response_model=GraphResponse)
@limiter.limit("60/minute")
def get_graph(
    request: Request,
    center: str | None = Query(None, description="Center entry ID for BFS"),
    center_kb: str | None = Query(None, description="KB of center entry"),
    kb: str | None = Query(None, description="Filter to KB"),
    entry_type: str | None = Query(None, alias="type", description="Filter by entry type"),
    depth: int = Query(2, ge=1, le=3, description="Max hops from center"),
    limit: int = Query(500, ge=1, le=2000, description="Max nodes"),
    svc: KBService = Depends(get_kb_service),
):
    """Get graph data for knowledge graph visualization."""
    data = svc.get_graph(
        center=center,
        center_kb=center_kb,
        kb_name=kb,
        entry_type=entry_type,
        depth=depth,
        limit=limit,
    )
    nodes = [GraphNode(**n) for n in data["nodes"]]
    edges = [GraphEdge(**e) for e in data["edges"]]
    return GraphResponse(nodes=nodes, edges=edges)
