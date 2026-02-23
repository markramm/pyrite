"""Template endpoints."""

from fastapi import APIRouter, HTTPException, Request

from ..api import get_config, limiter
from ..schemas import (
    RenderedTemplate,
    RenderTemplateRequest,
    TemplateDetail,
    TemplateListResponse,
    TemplateSummary,
)

router = APIRouter(tags=["Templates"])

_template_svc = None


def get_template_svc():
    """Get or create TemplateService singleton."""
    global _template_svc
    if _template_svc is None:
        from ...services.template_service import TemplateService

        _template_svc = TemplateService(get_config())
    return _template_svc


@router.get(
    "/kbs/{kb_name}/templates",
    response_model=TemplateListResponse,
)
@limiter.limit("100/minute")
def list_templates(request: Request, kb_name: str):
    """List available templates for a KB."""
    svc = get_template_svc()
    try:
        templates = svc.list_templates(kb_name)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail={"code": "KB_NOT_FOUND", "message": f"KB '{kb_name}' not found"},
        )
    return TemplateListResponse(
        templates=[TemplateSummary(**t) for t in templates],
        total=len(templates),
    )


@router.get(
    "/kbs/{kb_name}/templates/{template_name}",
    response_model=TemplateDetail,
)
@limiter.limit("100/minute")
def get_template_detail(request: Request, kb_name: str, template_name: str):
    """Get a template by name."""
    svc = get_template_svc()
    try:
        tpl = svc.get_template(kb_name, template_name)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail={"code": "KB_NOT_FOUND", "message": f"KB '{kb_name}' not found"},
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "TEMPLATE_NOT_FOUND",
                "message": f"Template '{template_name}' not found in KB '{kb_name}'",
            },
        )
    return TemplateDetail(**tpl)


@router.post(
    "/kbs/{kb_name}/templates/{template_name}/render",
    response_model=RenderedTemplate,
)
@limiter.limit("30/minute")
def render_template(
    request: Request,
    kb_name: str,
    template_name: str,
    req: RenderTemplateRequest,
):
    """Render a template with variables."""
    svc = get_template_svc()
    try:
        result = svc.render_template(kb_name, template_name, req.variables)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail={"code": "KB_NOT_FOUND", "message": f"KB '{kb_name}' not found"},
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "TEMPLATE_NOT_FOUND",
                "message": f"Template '{template_name}' not found in KB '{kb_name}'",
            },
        )
    return RenderedTemplate(**result)
