"""QA validation and assessment endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, Query, Request

from ...services.access_policy import KB, Action, ReadScope
from ...services.qa_service import QAService
from ..api import (
    get_qa_service,
    limiter,
)
from ..authz import authorize

router = APIRouter(tags=["QA"])


@router.get("/qa/status")
@limiter.limit("60/minute")
def get_qa_status(
    request: Request,
    kb: str | None = Query(None, description="Filter to specific KB"),
    svc: QAService = Depends(get_qa_service),
    scope: ReadScope = Depends(authorize(Action.KB_READ, KB)),
) -> dict[str, Any]:
    """Get QA status summary with issue counts by severity and rule.

    Without ``kb`` this sweeps every KB, so the readable set is pushed
    into the sweep: ``total_entries`` and ``total_issues`` are sums over
    the KBs swept, and one the caller cannot read must contribute to
    neither.
    """
    return svc.get_status(kb_name=kb, kb_names=None if kb else scope.as_set())


@router.get("/qa/validate/{entry_id}", dependencies=[Depends(authorize(Action.KB_READ, KB))])
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
    kb: str | None = Query(None, description="KB name; omit for all readable KBs"),
    svc: QAService = Depends(get_qa_service),
    scope: ReadScope = Depends(authorize(Action.KB_READ, KB)),
) -> dict[str, Any]:
    """Validate a KB (or every readable KB) and return issues.

    The all-KBs form returns one block per KB, each naming the KB and
    every entry id in it -- a full inventory. It now covers only the KBs
    the caller may read.
    """
    if kb:
        return svc.validate_kb(kb)
    return svc.validate_all(kb_names=scope.as_set())


@router.get("/qa/coverage", dependencies=[Depends(authorize(Action.KB_READ, KB))])
@limiter.limit("60/minute")
def get_qa_coverage(
    request: Request,
    kb: str = Query(..., description="KB name (required)"),
    svc: QAService = Depends(get_qa_service),
) -> dict[str, Any]:
    """Get assessment coverage stats for a KB."""
    return svc.get_coverage(kb)
