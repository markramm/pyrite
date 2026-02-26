"""Block reference endpoints — list blocks for an entry."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from ...services.kb_service import KBService
from ...storage.models import Block
from ..api import get_kb_service, limiter, negotiate_response
from ..schemas import BlockListResponse, BlockResponse

router = APIRouter(tags=["Blocks"])


@router.get("/entries/{entry_id}/blocks", response_model=BlockListResponse)
@limiter.limit("100/minute")
def get_entry_blocks(
    request: Request,
    entry_id: str,
    kb: str = Query(..., description="KB name"),
    heading: str | None = Query(None, description="Filter by heading"),
    block_type: str | None = Query(None, description="Filter by block type"),
    block_id: str | None = Query(None, description="Filter by block ID"),
    svc: KBService = Depends(get_kb_service),
):
    """Get blocks extracted from an entry."""
    entry = svc.get_entry(entry_id, kb_name=kb)
    if not entry:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": f"Entry '{entry_id}' not found"},
        )

    # Query blocks from database
    blocks_query = svc.db.session.query(Block).filter_by(entry_id=entry_id, kb_name=kb)

    if heading:
        blocks_query = blocks_query.filter(Block.heading == heading)
    if block_type:
        blocks_query = blocks_query.filter(Block.block_type == block_type)
    if block_id:
        blocks_query = blocks_query.filter(Block.block_id == block_id)

    blocks_query = blocks_query.order_by(Block.position)
    block_rows = blocks_query.all()

    blocks = [
        BlockResponse(
            block_id=b.block_id,
            heading=b.heading,
            content=b.content,
            position=b.position,
            block_type=b.block_type,
        )
        for b in block_rows
    ]

    resp_data = {
        "entry_id": entry_id,
        "kb_name": kb,
        "blocks": [b.model_dump() for b in blocks],
        "total": len(blocks),
    }
    neg = negotiate_response(request, resp_data)
    if neg is not None:
        return neg
    return BlockListResponse(
        entry_id=entry_id, kb_name=kb, blocks=blocks, total=len(blocks)
    )
