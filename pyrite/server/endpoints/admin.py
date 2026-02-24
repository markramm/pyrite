"""Admin endpoints: stats, index sync, AI status, KB management."""

from fastapi import APIRouter, Body, Depends, HTTPException, Request

from ...config import KBConfig, save_config
from ...services.kb_service import KBService
from ...services.llm_service import LLMService
from ...storage.index import IndexManager
from ..api import get_index_mgr, get_kb_service, get_llm_service, limiter
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
    # Broadcast WebSocket event
    import asyncio

    from ..websocket import manager

    try:
        loop = asyncio.get_event_loop()
        loop.create_task(
            manager.broadcast({"type": "kb_synced", "entry_id": "", "kb_name": ""})
        )
    except RuntimeError:
        pass

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


# =========================================================================
# KB Management
# =========================================================================


@router.post("/kbs")
@limiter.limit("30/minute")
def create_kb(
    request: Request,
    name: str = Body(...),
    path: str = Body(...),
    kb_type: str = Body("generic"),
    description: str = Body(""),
    shortname: str | None = Body(None),
    ephemeral: bool = Body(False),
    ttl: int | None = Body(None),
    svc: KBService = Depends(get_kb_service),
):
    """Create a new knowledge base."""
    from pathlib import Path as PathLib

    kb_path = PathLib(path).expanduser().resolve()
    kb_path.mkdir(parents=True, exist_ok=True)

    if ephemeral:
        kb = svc.create_ephemeral_kb(name, ttl=ttl or 3600, description=description)
        return {"created": True, "name": kb.name, "path": str(kb.path), "ephemeral": True}

    kb = KBConfig(
        name=name,
        path=kb_path,
        kb_type=kb_type,
        description=description,
        shortname=shortname,
    )
    config = svc.config
    config.add_kb(kb)
    save_config(config)
    svc.db.register_kb(name=name, kb_type=kb_type, path=str(kb_path), description=description)
    return {"created": True, "name": name, "path": str(kb_path)}


@router.delete("/kbs/{name}")
@limiter.limit("30/minute")
def delete_kb(
    request: Request,
    name: str,
    svc: KBService = Depends(get_kb_service),
):
    """Delete a knowledge base from the registry."""
    config = svc.config
    kb = config.get_kb(name)
    if not kb:
        raise HTTPException(status_code=404, detail=f"KB '{name}' not found")
    svc.db.unregister_kb(name)
    config.remove_kb(name)
    save_config(config)
    return {"deleted": True, "name": name}


@router.post("/kbs/gc")
@limiter.limit("30/minute")
def gc_ephemeral_kbs(
    request: Request,
    svc: KBService = Depends(get_kb_service),
):
    """Garbage-collect expired ephemeral KBs."""
    removed = svc.gc_ephemeral_kbs()
    return {"removed": removed, "count": len(removed)}
