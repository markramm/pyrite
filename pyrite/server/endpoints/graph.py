"""Graph visualization endpoint."""

from collections import deque
from typing import Any

from fastapi import APIRouter, Depends, Query, Request

from ...services.kb_service import KBService
from ..api import get_kb_service, limiter
from ..schemas import GraphEdge, GraphNode, GraphResponse

router = APIRouter(tags=["Graph"])


def compute_betweenness_centrality(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
) -> dict[tuple[str, str], float]:
    """Compute betweenness centrality using Brandes' algorithm with BFS.

    Treats the graph as undirected. Returns a dict mapping (id, kb_name) to
    a normalized centrality score in [0.0, 1.0].
    """
    # Build node keys and adjacency list
    node_keys = [(n["id"], n["kb_name"]) for n in nodes]
    node_set = set(node_keys)
    n = len(node_keys)

    if n < 3:
        return {k: 0.0 for k in node_keys}

    adj: dict[tuple[str, str], list[tuple[str, str]]] = {k: [] for k in node_keys}
    for e in edges:
        src = (e["source_id"], e["source_kb"])
        tgt = (e["target_id"], e["target_kb"])
        if src in node_set and tgt in node_set:
            adj[src].append(tgt)
            adj[tgt].append(src)

    centrality: dict[tuple[str, str], float] = {k: 0.0 for k in node_keys}

    # Brandes' algorithm: BFS from each source
    for s in node_keys:
        # BFS
        stack: list[tuple[str, str]] = []
        pred: dict[tuple[str, str], list[tuple[str, str]]] = {k: [] for k in node_keys}
        sigma: dict[tuple[str, str], int] = {k: 0 for k in node_keys}
        sigma[s] = 1
        dist: dict[tuple[str, str], int] = {k: -1 for k in node_keys}
        dist[s] = 0

        queue: deque[tuple[str, str]] = deque([s])
        while queue:
            v = queue.popleft()
            stack.append(v)
            for w in adj[v]:
                # w found for the first time?
                if dist[w] < 0:
                    dist[w] = dist[v] + 1
                    queue.append(w)
                # shortest path to w via v?
                if dist[w] == dist[v] + 1:
                    sigma[w] += sigma[v]
                    pred[w].append(v)

        # Accumulation
        delta: dict[tuple[str, str], float] = {k: 0.0 for k in node_keys}
        while stack:
            w = stack.pop()
            for v in pred[w]:
                delta[v] += (sigma[v] / sigma[w]) * (1.0 + delta[w])
            if w != s:
                centrality[w] += delta[w]

    # Normalize: undirected graph — each pair (s,t) contributes from both
    # s-BFS and t-BFS, so normalization is (n-1)*(n-2) not divided by 2.
    norm = float((n - 1) * (n - 2))
    if norm > 0:
        for k in centrality:
            centrality[k] /= norm

    return centrality


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
    include_centrality: bool = Query(False, description="Compute betweenness centrality"),
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

    if include_centrality:
        bc = compute_betweenness_centrality(data["nodes"], data["edges"])
        for n in data["nodes"]:
            n["centrality"] = bc.get((n["id"], n["kb_name"]), 0.0)

    nodes = [GraphNode(**n) for n in data["nodes"]]
    edges = [GraphEdge(**e) for e in data["edges"]]
    return GraphResponse(nodes=nodes, edges=edges)
