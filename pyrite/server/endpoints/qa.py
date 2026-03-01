"""QA validation and assessment endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, Query, Request

from ...config import PyriteConfig
from ...services.qa_service import QAService
from ...storage.database import PyriteDB
from ..api import get_config, get_db, limiter

router = APIRouter(tags=["QA"])


def get_qa_service(
    config: PyriteConfig = Depends(get_config),
    db: PyriteDB = Depends(get_db),
) -> QAService:
    """Get QA service instance."""
    return QAService(config, db)


@router.get("/qa/status")
@limiter.limit("60/minute")
def get_qa_status(
    request: Request,
    kb: str | None = Query(None, description="Filter to specific KB"),
    svc: QAService = Depends(get_qa_service),
) -> dict[str, Any]:
    """Get QA status summary with issue counts by severity and rule."""
    return svc.get_status(kb_name=kb)


@router.get("/qa/validate/{entry_id}")
@limiter.limit("60/minute")
def validate_entry(
    request: Request,
    entry_id: str,
    kb: str = Query(..., description="KB name (required)"),
    svc: QAService = Depends(get_qa_service),
) -> dict[str, Any]:
    """Validate a single entry and return issues."""
    return svc.validate_entry(entry_id, kb)


@router.get("/qa/validate")
@limiter.limit("60/minute")
def validate_kb(
    request: Request,
    kb: str | None = Query(None, description="KB name; omit for all KBs"),
    svc: QAService = Depends(get_qa_service),
) -> dict[str, Any]:
    """Validate a KB (or all KBs) and return issues."""
    if kb:
        return svc.validate_kb(kb)
    return svc.validate_all()


@router.get("/qa/coverage")
@limiter.limit("60/minute")
def get_qa_coverage(
    request: Request,
    kb: str = Query(..., description="KB name (required)"),
    svc: QAService = Depends(get_qa_service),
) -> dict[str, Any]:
    """Get assessment coverage stats for a KB."""
    return svc.get_coverage(kb)
