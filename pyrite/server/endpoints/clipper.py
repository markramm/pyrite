"""Web Clipper endpoint — POST /api/clip to fetch URL and create entry."""

from fastapi import APIRouter, Depends, HTTPException, Request

from ...services.clipper import ClipperService
from ...services.kb_service import KBService
from ..api import get_kb_service, limiter, requires_tier
from ..schemas import ClipRequest, ClipResponse

router = APIRouter(tags=["Clipper"])


@router.post("/clip", response_model=ClipResponse, dependencies=[Depends(requires_tier("write"))])
@limiter.limit("20/minute")
async def clip_url(
    request: Request,
    req: ClipRequest,
    svc: KBService = Depends(get_kb_service),
):
    """Clip a URL: fetch, convert to Markdown, and create an entry."""
    if not svc.get_kb(req.kb):
        raise HTTPException(
            status_code=404,
            detail={"code": "KB_NOT_FOUND", "message": f"KB '{req.kb}' not found"},
        )

    # Validate URL
    if not req.url.startswith(("http://", "https://")):
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_URL", "message": "URL must start with http:// or https://"},
        )

    # Clip the URL
    clipper = ClipperService()
    try:
        result = await clipper.clip_url(req.url, title=req.title)
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail={"code": "CLIP_FAILED", "message": f"Failed to fetch URL: {e}"},
        )

    # Build entry body with source attribution
    source_header = f"> Clipped from [{result.title}]({result.source_url})\n\n"
    body = source_header + result.body

    # Create the entry
    from ...schema import generate_entry_id

    entry_id = generate_entry_id(result.title)

    try:
        entry = svc.create_entry(
            req.kb,
            entry_id,
            result.title,
            req.entry_type or "note",
            body,
            tags=req.tags or [],
            metadata={"source_url": result.source_url, "clipped": True},
        )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"code": "CREATE_FAILED", "message": f"Entry creation failed: {e}"},
        )

    # Broadcast WebSocket event
    import asyncio

    from ..websocket import manager

    try:
        loop = asyncio.get_event_loop()
        loop.create_task(
            manager.broadcast(
                {"type": "entry_created", "entry_id": entry.id, "kb_name": req.kb}
            )
        )
    except RuntimeError:
        pass

    return ClipResponse(
        created=True,
        id=entry.id,
        kb_name=req.kb,
        title=result.title,
        source_url=result.source_url,
    )
