"""Template endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Request

from ...config import PyriteConfig
from ..api import get_config, limiter
from ..schemas import (
    RenderedTemplate,
    RenderTemplateRequest,
    TemplateDetail,
    TemplateListResponse,
    TemplateSummary,
)

router = APIRouter(tags=["Templates"])


def get_template_svc(config: PyriteConfig = Depends(get_config)):
    """Get TemplateService via DI."""
    from ...services.template_service import TemplateService

    return TemplateService(config)


@router.get(
    "/kbs/{kb_name}/templates",
    response_model=TemplateListResponse,
)
@limiter.limit("100/minute")
def list_templates(request: Request, kb_name: str, svc=Depends(get_template_svc)):
    """List available templates for a KB."""
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
def get_template_detail(request: Request, kb_name: str, template_name: str, svc=Depends(get_template_svc)):
    """Get a template by name."""
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
    svc=Depends(get_template_svc),
):
    """Render a template with variables."""
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
