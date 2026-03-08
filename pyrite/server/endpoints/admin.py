"""Admin endpoints: stats, index sync, AI status, KB management, plugins."""

import logging

from fastapi import APIRouter, Body, Depends, HTTPException, Request

from ...config import PyriteConfig
from ...exceptions import KBNotFoundError, KBProtectedError
from ...services.auth_service import AuthService
from ...services.index_worker import IndexWorker
from ...services.kb_registry_service import KBRegistryService
from ...services.kb_service import KBService
from ...services.llm_service import LLMService
from ...storage.database import PyriteDB
from ...storage.index import IndexManager
from ..api import (
    get_config,
    get_db,
    get_index_mgr,
    get_index_worker,
    get_kb_registry,
    get_kb_service,
    get_llm_service,
    limiter,
    requires_tier,
    resolve_kb_default_role,
)
from ..schemas import (
    AIStatusResponse,
    KBReindexResponse,
    StatsResponse,
    SyncResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Admin"])


@router.get("/stats", response_model=StatsResponse)
@limiter.limit("100/minute")
def get_stats(request: Request, index_mgr: IndexManager = Depends(get_index_mgr)):
    """Get index statistics."""
    stats = index_mgr.get_index_stats()
    return StatsResponse(**stats)


@router.post("/index/sync", dependencies=[Depends(requires_tier("admin"))])
@limiter.limit("30/minute")
def sync_index(
    request: Request,
    wait: bool = False,
    worker: IndexWorker = Depends(get_index_worker),
    index_mgr: IndexManager = Depends(get_index_mgr),
):
    """Sync the search index.

    By default submits a background job and returns immediately with a job_id.
    Pass ?wait=true to block until completion and return the legacy SyncResponse
    format with counts.
    """
    if wait:
        result = index_mgr.sync_incremental()
        # Broadcast WebSocket event
        import asyncio

        from ..websocket import manager

        try:
            loop = asyncio.get_running_loop()
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

    job_id = worker.submit_sync()
    return {"job_id": job_id, "status": "submitted"}


@router.get("/index/jobs/{job_id}", dependencies=[Depends(requires_tier("admin"))])
@limiter.limit("100/minute")
def get_index_job(request: Request, job_id: str, worker: IndexWorker = Depends(get_index_worker)):
    """Get status of an index job."""
    job = worker.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=404, detail={"code": "NOT_FOUND", "message": f"Job '{job_id}' not found"}
        )
    return job


@router.get("/index/jobs", dependencies=[Depends(requires_tier("admin"))])
@limiter.limit("100/minute")
def list_index_jobs(request: Request, worker: IndexWorker = Depends(get_index_worker)):
    """List active index jobs."""
    return {"jobs": worker.get_active_jobs()}


@router.get("/ai/status", response_model=AIStatusResponse)
@limiter.limit("100/minute")
def ai_status(request: Request, llm: LLMService = Depends(get_llm_service)):
    """Return AI/LLM configuration status."""
    status = llm.status()
    return AIStatusResponse(**status)


@router.get("/index/embed-status")
@limiter.limit("100/minute")
def embed_status(request: Request, db: PyriteDB = Depends(get_db)):
    """Return embedding queue status."""
    from ...services.embedding_worker import EmbeddingWorker

    worker = EmbeddingWorker(db)
    return worker.get_status()


# =========================================================================
# KB Management
# =========================================================================


@router.post("/kbs", dependencies=[Depends(requires_tier("admin"))])
@limiter.limit("30/minute")
def create_kb(
    request: Request,
    name: str = Body(...),
    path: str = Body(...),
    kb_type: str = Body("generic"),
    description: str = Body(""),
    ephemeral: bool = Body(False),
    ttl: int | None = Body(None),
    svc: KBService = Depends(get_kb_service),
    registry: KBRegistryService = Depends(get_kb_registry),
):
    """Create a new knowledge base."""
    if ephemeral:
        kb = svc.create_ephemeral_kb(name, ttl=ttl or 3600, description=description)
        return {"created": True, "name": kb.name, "path": str(kb.path), "ephemeral": True}

    try:
        result = registry.add_kb(name=name, path=path, kb_type=kb_type, description=description)
    except ValueError as e:
        raise HTTPException(status_code=409, detail={"code": "CONFLICT", "message": str(e)})
    return {"created": True, **result}


@router.put("/kbs/{name}", dependencies=[Depends(requires_tier("admin"))])
@limiter.limit("30/minute")
def update_kb(
    request: Request,
    name: str,
    description: str | None = Body(None),
    kb_type: str | None = Body(None),
    registry: KBRegistryService = Depends(get_kb_registry),
):
    """Update a knowledge base's metadata."""
    try:
        result = registry.update_kb(name, description=description, kb_type=kb_type)
    except KBNotFoundError:
        raise HTTPException(
            status_code=404, detail={"code": "NOT_FOUND", "message": f"KB '{name}' not found"}
        )
    return {"updated": True, **result}


@router.delete("/kbs/{name}", dependencies=[Depends(requires_tier("admin"))])
@limiter.limit("30/minute")
def delete_kb(
    request: Request,
    name: str,
    registry: KBRegistryService = Depends(get_kb_registry),
):
    """Delete a knowledge base from the registry."""
    try:
        registry.remove_kb(name)
    except KBNotFoundError:
        raise HTTPException(
            status_code=404, detail={"code": "NOT_FOUND", "message": f"KB '{name}' not found"}
        )
    except KBProtectedError as e:
        raise HTTPException(status_code=403, detail={"code": "PROTECTED", "message": str(e)})
    return {"deleted": True, "name": name}


@router.post("/kbs/{name}/reindex", dependencies=[Depends(requires_tier("admin"))])
@limiter.limit("10/minute")
def reindex_kb(
    request: Request,
    name: str,
    registry: KBRegistryService = Depends(get_kb_registry),
):
    """Reindex a specific knowledge base."""
    try:
        result = registry.reindex_kb(name)
    except KBNotFoundError:
        raise HTTPException(
            status_code=404, detail={"code": "NOT_FOUND", "message": f"KB '{name}' not found"}
        )
    return KBReindexResponse(name=name, **result)


@router.post("/kbs/gc", dependencies=[Depends(requires_tier("admin"))])
@limiter.limit("30/minute")
def gc_ephemeral_kbs(
    request: Request,
    svc: KBService = Depends(get_kb_service),
):
    """Garbage-collect expired ephemeral KBs."""
    removed = svc.gc_ephemeral_kbs()
    return {"removed": removed, "count": len(removed)}


# =============================================================================
# Ephemeral KB Admin
# =============================================================================


@router.get("/kbs/ephemeral", dependencies=[Depends(requires_tier("admin"))])
@limiter.limit("30/minute")
def list_ephemeral_kbs(
    request: Request,
    svc: KBService = Depends(get_kb_service),
):
    """List all active ephemeral KBs. Requires admin."""
    kbs = svc.list_ephemeral_kbs()
    return {"ephemeral_kbs": kbs, "count": len(kbs)}


@router.delete("/kbs/ephemeral/{name}", dependencies=[Depends(requires_tier("admin"))])
@limiter.limit("30/minute")
def force_expire_ephemeral_kb(
    request: Request,
    name: str,
    svc: KBService = Depends(get_kb_service),
):
    """Force-expire a specific ephemeral KB. Requires admin."""
    ok = svc.force_expire_kb(name)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Ephemeral KB '{name}' not found")
    return {"expired": True, "name": name}


# =============================================================================
# Ephemeral KB creation (authenticated users, not admin-only)
# =============================================================================


@router.post("/kbs/ephemeral")
@limiter.limit("10/minute")
def create_ephemeral_kb(
    request: Request,
    name: str | None = Body(None, embed=True),
    config: PyriteConfig = Depends(get_config),
    db: PyriteDB = Depends(get_db),
    svc: KBService = Depends(get_kb_service),
):
    """Create an ephemeral KB for the current user."""
    auth_user = getattr(request.state, "auth_user", None)
    if not auth_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    auth_service = AuthService(db, config.settings.auth)
    try:
        result = auth_service.create_user_ephemeral_kb(auth_user["id"], svc, name=name)
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))

    return {"created": True, **result}


# =============================================================================
# Per-KB Permission CRUD
# =============================================================================


@router.get("/kbs/{name}/permissions")
@limiter.limit("30/minute")
def list_kb_permissions(
    request: Request,
    name: str,
    config: PyriteConfig = Depends(get_config),
    db: PyriteDB = Depends(get_db),
):
    """List permission grants for a KB. Requires global admin or KB admin."""
    auth_user = getattr(request.state, "auth_user", None)
    global_role = getattr(request.state, "api_role", None)
    auth_service = AuthService(db, config.settings.auth)

    if global_role != "admin":
        if not auth_user:
            raise HTTPException(status_code=403, detail="Admin access required")
        kb_default_role = resolve_kb_default_role(config, db, name)
        effective = auth_service.get_kb_role(auth_user["id"], name, kb_default_role)
        if effective != "admin":
            raise HTTPException(status_code=403, detail="Admin access required for this KB")

    grants = auth_service.list_kb_permissions(name)
    return {"kb_name": name, "permissions": grants}


@router.post("/kbs/{name}/permissions")
@limiter.limit("30/minute")
def manage_kb_permission(
    request: Request,
    name: str,
    user_id: int = Body(...),
    role: str | None = Body(None),
    revoke: bool = Body(False),
    config: PyriteConfig = Depends(get_config),
    db: PyriteDB = Depends(get_db),
):
    """Grant or revoke a per-KB permission. Requires global admin or KB admin."""
    auth_user = getattr(request.state, "auth_user", None)
    global_role = getattr(request.state, "api_role", None)
    auth_service = AuthService(db, config.settings.auth)

    if global_role != "admin":
        if not auth_user:
            raise HTTPException(status_code=403, detail="Admin access required")
        kb_default_role = resolve_kb_default_role(config, db, name)
        effective = auth_service.get_kb_role(auth_user["id"], name, kb_default_role)
        if effective != "admin":
            raise HTTPException(status_code=403, detail="Admin access required for this KB")

    auth_service = AuthService(db, config.settings.auth)
    granted_by = auth_user["id"] if auth_user else None

    if revoke:
        ok = auth_service.revoke_kb_permission(user_id, name)
        if not ok:
            raise HTTPException(status_code=404, detail="Permission not found")
        return {"revoked": True, "user_id": user_id, "kb_name": name}

    if not role:
        raise HTTPException(status_code=400, detail="role is required when not revoking")

    try:
        auth_service.grant_kb_permission(user_id, name, role, granted_by)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"granted": True, "user_id": user_id, "kb_name": name, "role": role}


@router.put(
    "/kbs/{name}/default-role", dependencies=[Depends(requires_tier("admin"))]
)
@limiter.limit("30/minute")
def update_kb_default_role(
    request: Request,
    name: str,
    role: str | None = Body(..., embed=True),
    registry: KBRegistryService = Depends(get_kb_registry),
):
    """Update a KB's default access role. Requires admin."""
    if role is not None and role not in ("none", "read", "write"):
        raise HTTPException(status_code=400, detail="role must be 'none', 'read', 'write', or null")
    try:
        registry.update_kb(name, default_role=role)
    except KBNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"ok": True, "kb_name": name, "default_role": role}


# =============================================================================
# Plugin UI
# =============================================================================


@router.get("/plugins")
@limiter.limit("100/minute")
def list_plugins(request: Request):
    """List installed plugins with capabilities."""
    from ...plugins import get_registry

    registry = get_registry()
    plugins = []
    for name in registry.list_plugins():
        plugin = registry.get_plugin(name)
        if not plugin:
            continue
        info: dict = {
            "name": name,
            "entry_types": [],
            "kb_types": [],
            "tools": [],
            "hooks": [],
            "has_cli": False,
        }
        try:
            if hasattr(plugin, "get_entry_types"):
                types = plugin.get_entry_types()
                if types:
                    info["entry_types"] = list(types.keys())
        except Exception:
            logger.warning("Failed to get entry types for plugin %s", name, exc_info=True)
        try:
            if hasattr(plugin, "get_kb_types"):
                kb_types = plugin.get_kb_types()
                if kb_types:
                    info["kb_types"] = kb_types
        except Exception:
            logger.warning("Failed to get kb types for plugin %s", name, exc_info=True)
        try:
            if hasattr(plugin, "get_cli_commands"):
                cmds = plugin.get_cli_commands()
                if cmds:
                    info["has_cli"] = True
        except Exception:
            logger.warning("Failed to get CLI commands for plugin %s", name, exc_info=True)
        try:
            if hasattr(plugin, "get_hooks"):
                hooks = plugin.get_hooks()
                if hooks:
                    info["hooks"] = list(hooks.keys())
        except Exception:
            logger.warning("Failed to get hooks for plugin %s", name, exc_info=True)
        try:
            for tier in ("read", "write", "admin"):
                if hasattr(plugin, "get_mcp_tools"):
                    tools = plugin.get_mcp_tools(tier)
                    if tools:
                        info["tools"].extend(list(tools.keys()))
        except Exception:
            logger.warning("Failed to get MCP tools for plugin %s", name, exc_info=True)
        plugins.append(info)
    return {"plugins": plugins, "total": len(plugins)}


@router.get("/plugins/{name}")
@limiter.limit("100/minute")
def get_plugin_detail(request: Request, name: str):
    """Get detailed plugin information."""
    from ...plugins import get_registry

    registry = get_registry()
    plugin = registry.get_plugin(name)
    if not plugin:
        raise HTTPException(
            status_code=404, detail={"code": "NOT_FOUND", "message": f"Plugin '{name}' not found"}
        )

    info: dict = {"name": name}

    try:
        if hasattr(plugin, "get_entry_types"):
            types = plugin.get_entry_types()
            info["entry_types"] = {k: str(v) for k, v in types.items()} if types else {}
    except Exception:
        logger.warning("Failed to get entry types for plugin %s", name, exc_info=True)
        info["entry_types"] = {}

    try:
        if hasattr(plugin, "get_kb_types"):
            info["kb_types"] = plugin.get_kb_types() or []
    except Exception:
        logger.warning("Failed to get kb types for plugin %s", name, exc_info=True)
        info["kb_types"] = []

    try:
        if hasattr(plugin, "get_hooks"):
            hooks = plugin.get_hooks()
            info["hooks"] = {k: len(v) for k, v in hooks.items()} if hooks else {}
    except Exception:
        logger.warning("Failed to get hooks for plugin %s", name, exc_info=True)
        info["hooks"] = {}

    tools_all: dict = {}
    try:
        for tier in ("read", "write", "admin"):
            if hasattr(plugin, "get_mcp_tools"):
                tools = plugin.get_mcp_tools(tier)
                if tools:
                    for tool_name, tool_def in tools.items():
                        tools_all[tool_name] = {
                            "tier": tier,
                            "description": tool_def.get("description", ""),
                        }
    except Exception:
        logger.warning("Failed to get MCP tools for plugin %s", name, exc_info=True)
    info["tools"] = tools_all

    return info
