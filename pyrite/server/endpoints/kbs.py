"""KB listing, schema, health, reindex, and export endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from ...config import PyriteConfig
from ...exceptions import KBNotFoundError
from ...services.export_service import ExportService
from ...services.kb_registry_service import KBRegistryService
from ...services.kb_service import KBService
from ..api import (
    get_config,
    get_export_service,
    get_kb_registry,
    get_kb_service,
    limiter,
    negotiate_response,
)
from ..schemas import KBHealthResponse, KBInfo, KBListResponse

router = APIRouter(tags=["Knowledge Bases"])


class ExportRequest(BaseModel):
    """Request body for KB export."""

    repo_url: str
    branch: str = "main"
    commit_message: str | None = None


def _kb_to_info(kb: dict) -> KBInfo:
    """Build a KBInfo from a registry KB dict."""
    return KBInfo(
        name=kb["name"],
        type=kb["type"],
        path=kb["path"],
        entries=kb["entries"],
        indexed=kb["indexed"],
        source=kb.get("source", "user"),
        description=kb.get("description", ""),
        read_only=kb.get("read_only", False),
        last_indexed=kb.get("last_indexed"),
        shortname=kb.get("shortname"),
        default_role=kb.get("default_role"),
    )


@router.get("/kbs", response_model=KBListResponse)
@limiter.limit("100/minute")
def list_kbs(
    request: Request,
    registry: KBRegistryService = Depends(get_kb_registry),
):
    """List all knowledge bases."""
    kbs_data = registry.list_kbs()
    kbs = [_kb_to_info(kb) for kb in kbs_data]
    resp_data = {"kbs": [kb.model_dump() for kb in kbs], "total": len(kbs)}
    neg = negotiate_response(request, resp_data)
    if neg is not None:
        return neg
    return KBListResponse(kbs=kbs, total=len(kbs))


@router.get("/kbs/{kb_name}", response_model=KBInfo)
@limiter.limit("100/minute")
def get_kb(
    kb_name: str,
    request: Request,
    registry: KBRegistryService = Depends(get_kb_registry),
):
    """Get a single KB by name."""
    kb = registry.get_kb(kb_name)
    if not kb:
        raise HTTPException(
            status_code=404, detail={"code": "NOT_FOUND", "message": f"KB '{kb_name}' not found"}
        )
    return _kb_to_info(kb)


@router.get("/kbs/{kb_name}/health", response_model=KBHealthResponse)
@limiter.limit("100/minute")
def kb_health(
    kb_name: str,
    request: Request,
    registry: KBRegistryService = Depends(get_kb_registry),
):
    """Check KB health: path, file count vs index count."""
    try:
        result = registry.health_kb(kb_name)
    except KBNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={"code": "KB_NOT_FOUND", "message": f"KB '{kb_name}' not found"},
        )
    return KBHealthResponse(**result)


@router.get("/kbs/{kb_name}/schema")
@limiter.limit("100/minute")
def get_kb_schema(
    kb_name: str,
    request: Request,
    config: PyriteConfig = Depends(get_config),
):
    """Get the schema for a knowledge base including type metadata."""
    kb_config = config.get_kb(kb_name)
    if not kb_config:
        raise HTTPException(
            status_code=404, detail={"code": "NOT_FOUND", "message": f"KB '{kb_name}' not found"}
        )

    schema = kb_config.kb_schema
    return schema.to_agent_schema()


@router.get("/kbs/{kb_name}/orient")
@limiter.limit("60/minute")
def orient_kb(
    kb_name: str,
    request: Request,
    recent: int = 5,
    svc: KBService = Depends(get_kb_service),
):
    """One-shot KB orientation summary — types, tags, recent changes, and schema."""
    try:
        result = svc.orient(kb_name, recent_limit=recent)
    except KBNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={"code": "KB_NOT_FOUND", "message": f"KB '{kb_name}' not found"},
        )
    neg = negotiate_response(request, result)
    if neg is not None:
        return neg
    return result


@router.post("/kbs/{kb_name}/export")
@limiter.limit("5/minute")
def export_kb_to_repo(
    kb_name: str,
    body: ExportRequest,
    request: Request,
    export_svc: ExportService = Depends(get_export_service),
):
    """Export a KB's entries to a GitHub repo (clone, export, commit, push)."""
    # Get GitHub token from authenticated user if available
    github_token = None
    auth_user = getattr(request.state, "auth_user", None)
    if auth_user:
        from ...services.auth_service import AuthService

        config = request.app.state.pyrite_config
        db = request.app.state.pyrite_db
        if db:
            auth_service = AuthService(db, config.settings.auth)
            github_token, _ = auth_service.get_github_token_for_user(auth_user["id"])

    try:
        result = export_svc.export_kb_to_repo(
            kb_name,
            body.repo_url,
            github_token=github_token,
            branch=body.branch,
            commit_message=body.commit_message,
        )
        result["kb_name"] = kb_name
        result["repo_url"] = body.repo_url
        return result
    except KBNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={"code": "KB_NOT_FOUND", "message": f"KB '{kb_name}' not found"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"code": "EXPORT_FAILED", "message": str(e)},
        )
