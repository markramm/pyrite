"""Admin endpoints: stats, index sync, AI status, plugins."""

from fastapi import APIRouter, Depends, HTTPException, Request

from ...config import PyriteConfig
from ...storage.index import IndexManager
from ..api import get_config, get_index_mgr, limiter
from ..schemas import StatsResponse, SyncResponse

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


@router.get("/ai/status")
@limiter.limit("100/minute")
def ai_status(request: Request, config: PyriteConfig = Depends(get_config)):
    """Return AI/LLM configuration status."""
    from ...services.llm_service import LLMService

    svc = LLMService(config.settings)
    return svc.status()


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
            pass
        try:
            if hasattr(plugin, "get_kb_types"):
                kb_types = plugin.get_kb_types()
                if kb_types:
                    info["kb_types"] = kb_types
        except Exception:
            pass
        try:
            if hasattr(plugin, "get_cli_commands"):
                cmds = plugin.get_cli_commands()
                if cmds:
                    info["has_cli"] = True
        except Exception:
            pass
        try:
            if hasattr(plugin, "get_hooks"):
                hooks = plugin.get_hooks()
                if hooks:
                    info["hooks"] = list(hooks.keys())
        except Exception:
            pass
        try:
            for tier in ("read", "write", "admin"):
                if hasattr(plugin, "get_mcp_tools"):
                    tools = plugin.get_mcp_tools(tier)
                    if tools:
                        info["tools"].extend(list(tools.keys()))
        except Exception:
            pass
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
        raise HTTPException(status_code=404, detail=f"Plugin '{name}' not found")

    info: dict = {"name": name}

    try:
        if hasattr(plugin, "get_entry_types"):
            types = plugin.get_entry_types()
            info["entry_types"] = {k: str(v) for k, v in types.items()} if types else {}
    except Exception:
        info["entry_types"] = {}

    try:
        if hasattr(plugin, "get_kb_types"):
            info["kb_types"] = plugin.get_kb_types() or []
    except Exception:
        info["kb_types"] = []

    try:
        if hasattr(plugin, "get_hooks"):
            hooks = plugin.get_hooks()
            info["hooks"] = {k: len(v) for k, v in hooks.items()} if hooks else {}
    except Exception:
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
        pass
    info["tools"] = tools_all

    return info
