"""Admin endpoints: stats, index sync, AI status, KB management, plugins."""

import logging

from fastapi import APIRouter, Body, Depends, HTTPException, Request

from ...config import KBConfig, PyriteConfig, save_config
from ...services.auth_service import AuthService
from ...services.kb_service import KBService
from ...services.llm_service import LLMService
from ...storage.database import PyriteDB
from ...storage.index import IndexManager
from ..api import (
    get_config,
    get_db,
    get_index_mgr,
    get_kb_service,
    get_llm_service,
    limiter,
    requires_tier,
)
from ..schemas import AIStatusResponse, StatsResponse, SyncResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Admin"])


@router.get("/stats", response_model=StatsResponse)
@limiter.limit("100/minute")
def get_stats(request: Request, index_mgr: IndexManager = Depends(get_index_mgr)):
    """Get index statistics."""
    stats = index_mgr.get_index_stats()
    return StatsResponse(**stats)


@router.post(
    "/index/sync", response_model=SyncResponse, dependencies=[Depends(requires_tier("admin"))]
)
@limiter.limit("30/minute")
def sync_index(request: Request, index_mgr: IndexManager = Depends(get_index_mgr)):
    """Trigger incremental index sync."""
    result = index_mgr.sync_incremental()
    # Broadcast WebSocket event
    import asyncio

    from ..websocket import manager

    try:
        loop = asyncio.get_event_loop()
        loop.create_task(manager.broadcast({"type": "kb_synced", "entry_id": "", "kb_name": ""}))
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


@router.delete("/kbs/{name}", dependencies=[Depends(requires_tier("admin"))])
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
        raise HTTPException(
            status_code=404, detail={"code": "NOT_FOUND", "message": f"KB '{name}' not found"}
        )
    svc.db.unregister_kb(name)
    config.remove_kb(name)
    save_config(config)
    return {"deleted": True, "name": name}


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

    if global_role != "admin":
        # Check if user has KB-level admin
        if not auth_user:
            raise HTTPException(status_code=403, detail="Admin access required")
        auth_service = AuthService(db, config.settings.auth)
        kb_config = config.get_kb(name)
        kb_default_role = kb_config.default_role if kb_config else None
        effective = auth_service.get_kb_role(auth_user["id"], name, kb_default_role)
        if effective != "admin":
            raise HTTPException(status_code=403, detail="Admin access required for this KB")

    auth_service = AuthService(db, config.settings.auth)
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

    if global_role != "admin":
        if not auth_user:
            raise HTTPException(status_code=403, detail="Admin access required")
        auth_service = AuthService(db, config.settings.auth)
        kb_config = config.get_kb(name)
        kb_default_role = kb_config.default_role if kb_config else None
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
