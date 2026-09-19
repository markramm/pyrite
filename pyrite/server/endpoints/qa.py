"""QA validation and assessment endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, Query, Request

from ...config import PyriteConfig
from ...services.llm_service import LLMService
from ...services.qa_service import QAService
from ...storage.database import PyriteDB
from ..api import (
    get_config,
    get_db,
    get_llm_service,
    get_readable_kbs,
    limiter,
    requires_kb_read,
)

router = APIRouter(tags=["QA"])


def get_qa_service(
    config: PyriteConfig = Depends(get_config),
    db: PyriteDB = Depends(get_db),
    llm_service: LLMService = Depends(get_llm_service),
) -> QAService:
    """Get QA service instance."""
    return QAService(config, db, llm_service=llm_service)


@router.get("/qa/status", dependencies=[Depends(requires_kb_read())])
@limiter.limit("60/minute")
def get_qa_status(
    request: Request,
    kb: str | None = Query(None, description="Filter to specific KB"),
    svc: QAService = Depends(get_qa_service),
    readable: set[str] | None = Depends(get_readable_kbs),
) -> dict[str, Any]:
    """Get QA status summary with issue counts by severity and rule.

    Without ``kb`` this sweeps every KB, so the readable set is pushed
    into the sweep: ``total_entries`` and ``total_issues`` are sums over
    the KBs swept, and one the caller cannot read must contribute to
    neither.
    """
    return svc.get_status(kb_name=kb, kb_names=None if kb else readable)


@router.get("/qa/validate/{entry_id}", dependencies=[Depends(requires_kb_read())])
@limiter.limit("60/minute")
def validate_entry(
    request: Request,
    entry_id: str,
    kb: str = Query(..., description="KB name (required)"),
    svc: QAService = Depends(get_qa_service),
) -> dict[str, Any]:
    """Validate a single entry and return issues."""
    return svc.validate_entry(entry_id, kb)


@router.get("/qa/validate", dependencies=[Depends(requires_kb_read())])
@limiter.limit("60/minute")
def validate_kb(
    request: Request,
    kb: str | None = Query(None, description="KB name; omit for all readable KBs"),
    svc: QAService = Depends(get_qa_service),
    readable: set[str] | None = Depends(get_readable_kbs),
) -> dict[str, Any]:
    """Validate a KB (or every readable KB) and return issues.

    The all-KBs form returns one block per KB, each naming the KB and
    every entry id in it -- a full inventory. It now covers only the KBs
    the caller may read.
    """
    if kb:
        return svc.validate_kb(kb)
    return svc.validate_all(kb_names=readable)


@router.get("/qa/coverage", dependencies=[Depends(requires_kb_read())])
@limiter.limit("60/minute")
def get_qa_coverage(
    request: Request,
    kb: str = Query(..., description="KB name (required)"),
    svc: QAService = Depends(get_qa_service),
) -> dict[str, Any]:
    """Get assessment coverage stats for a KB."""
    return svc.get_coverage(kb)
