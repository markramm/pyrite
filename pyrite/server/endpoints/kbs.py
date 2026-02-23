"""KB listing and schema endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Request

from ...config import PyriteConfig
from ...services.kb_service import KBService
from ..api import get_config, get_kb_service, limiter, negotiate_response
from ..schemas import KBInfo, KBListResponse

router = APIRouter(tags=["Knowledge Bases"])


@router.get("/kbs", response_model=KBListResponse)
@limiter.limit("100/minute")
def list_kbs(
    request: Request,
    svc: KBService = Depends(get_kb_service),
):
    """List all configured knowledge bases."""
    kbs_data = svc.list_kbs()
    kbs = [
        KBInfo(
            name=kb["name"],
            type=kb["type"],
            path=kb["path"],
            entries=kb["entries"],
            indexed=kb["indexed"],
        )
        for kb in kbs_data
    ]
    resp_data = {"kbs": [kb.model_dump() for kb in kbs], "total": len(kbs)}
    neg = negotiate_response(request, resp_data)
    if neg is not None:
        return neg
    return KBListResponse(kbs=kbs, total=len(kbs))


@router.get("/kbs/{kb_name}/schema")
@limiter.limit("100/minute")
def get_kb_schema(
    kb_name: str,
    request: Request,
    config: PyriteConfig = Depends(get_config),
):
    """Get the schema for a knowledge base including type metadata."""
    from ...schema import KBSchema

    kb_config = config.get_kb(kb_name)
    if not kb_config:
        raise HTTPException(status_code=404, detail=f"KB '{kb_name}' not found")

    schema = KBSchema.from_yaml(kb_config.path / "kb.yaml")
    return schema.to_agent_schema()
