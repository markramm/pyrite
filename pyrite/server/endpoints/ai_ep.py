"""AI endpoints: summarize, auto-tag, suggest-links, chat."""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from ...services.kb_service import KBService
from ...services.llm_service import LLMService
from ..api import get_config, get_db, get_kb_service, get_llm_service, limiter, requires_tier
from ..schemas import (
    AIAutoTagResponse,
    AIChatRequest,
    AIEntryRequest,
    AILinkSuggestion,
    AILinkSuggestResponse,
    AISummarizeResponse,
    AITagSuggestion,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI"], dependencies=[Depends(requires_tier("write"))])


def _require_configured(llm: LLMService) -> None:
    """Raise 503 if AI provider is not configured."""
    status = llm.status()
    if not status["configured"]:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "AI_NOT_CONFIGURED",
                "message": "AI provider is not configured",
                "hint": "Configure an AI provider in Settings → AI Provider",
            },
        )


def _get_entry(svc: KBService, entry_id: str, kb_name: str) -> dict:
    """Fetch an entry or raise 404."""
    entry = svc.get_entry(entry_id, kb_name=kb_name)
    if not entry:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": f"Entry '{entry_id}' not found"},
        )
    return entry


@router.post("/summarize", response_model=AISummarizeResponse)
@limiter.limit("30/minute")
async def ai_summarize(
    request: Request,
    req: AIEntryRequest,
    llm: LLMService = Depends(get_llm_service),
    svc: KBService = Depends(get_kb_service),
):
    """Generate an AI summary for an entry."""
    _require_configured(llm)
    entry = _get_entry(svc, req.entry_id, req.kb_name)

    body = entry.get("body", "") or ""
    title = entry.get("title", "")
    if not body.strip():
        return AISummarizeResponse(summary="(No content to summarize)")

    system = "You are a knowledge management assistant. Summarize the following entry concisely in 2-3 sentences. Focus on the key points and purpose."
    prompt = f"Title: {title}\n\n{body}"

    try:
        summary = await llm.complete(prompt, system=system, max_tokens=256)
        return AISummarizeResponse(summary=summary.strip())
    except Exception as e:
        logger.exception("AI summarize failed")
        raise HTTPException(status_code=500, detail={"code": "AI_ERROR", "message": str(e)})


@router.post("/auto-tag", response_model=AIAutoTagResponse)
@limiter.limit("30/minute")
async def ai_auto_tag(
    request: Request,
    req: AIEntryRequest,
    llm: LLMService = Depends(get_llm_service),
    svc: KBService = Depends(get_kb_service),
):
    """Suggest tags for an entry using AI."""
    _require_configured(llm)
    entry = _get_entry(svc, req.entry_id, req.kb_name)

    body = entry.get("body", "") or ""
    title = entry.get("title", "")
    existing_tags = entry.get("tags", [])

    # Get the tag vocabulary
    all_tags_raw = svc.get_all_tags(kb_name=req.kb_name)
    tag_vocab = [t["name"] for t in all_tags_raw][:200]  # limit to 200 tags

    system = """You are a knowledge management assistant. Suggest relevant tags for the entry.
Return a JSON array of objects with keys: "name" (string), "is_new" (boolean), "reason" (string).
- Prefer existing tags from the vocabulary when they fit.
- Mark tags not in the vocabulary as is_new=true.
- Suggest 3-7 tags total.
- Do not suggest tags the entry already has.
Return ONLY the JSON array, no other text."""

    prompt = f"""Title: {title}

Content:
{body[:3000]}

Existing tags on this entry: {json.dumps(existing_tags)}
Tag vocabulary: {json.dumps(tag_vocab[:100])}"""

    try:
        result = await llm.complete(prompt, system=system, max_tokens=512)
        # Parse JSON from response
        result = result.strip()
        if result.startswith("```"):
            result = result.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        suggestions = json.loads(result)
        tags = [AITagSuggestion(**s) for s in suggestions if isinstance(s, dict)]
        return AIAutoTagResponse(suggested_tags=tags)
    except (json.JSONDecodeError, TypeError):
        logger.warning("AI auto-tag returned non-JSON: %s", result[:200])
        return AIAutoTagResponse(suggested_tags=[])
    except Exception as e:
        logger.exception("AI auto-tag failed")
        raise HTTPException(status_code=500, detail={"code": "AI_ERROR", "message": str(e)})


@router.post("/suggest-links", response_model=AILinkSuggestResponse)
@limiter.limit("30/minute")
async def ai_suggest_links(
    request: Request,
    req: AIEntryRequest,
    llm: LLMService = Depends(get_llm_service),
    svc: KBService = Depends(get_kb_service),
):
    """Suggest wikilinks for an entry using AI + search."""
    _require_configured(llm)
    entry = _get_entry(svc, req.entry_id, req.kb_name)

    body = entry.get("body", "") or ""
    title = entry.get("title", "")

    # Search for related entries
    from ...services.search_service import SearchService

    cfg = get_config()
    db = get_db()
    search_svc = SearchService(db, settings=cfg.settings)

    try:
        related = search_svc.search(
            query=title,
            kb_name=req.kb_name,
            limit=15,
            mode="hybrid",
        )
    except Exception:
        related = search_svc.search(
            query=title,
            kb_name=req.kb_name,
            limit=15,
            mode="keyword",
        )

    # Filter out self
    related = [r for r in related if r.get("id") != req.entry_id][:10]

    if not related:
        return AILinkSuggestResponse(suggestions=[])

    candidates = "\n".join(
        f"- [{r['id']}] {r.get('title', '')} ({r.get('entry_type', '')}): {(r.get('snippet') or '')[:100]}"
        for r in related
    )

    system = """You are a knowledge management assistant. Given an entry and a list of candidate entries, suggest which ones should be linked using [[wikilinks]].
Return a JSON array of objects with keys: "target_id" (string), "target_title" (string), "reason" (string).
Only suggest links that are genuinely relevant. Return ONLY the JSON array."""

    prompt = f"""Entry: {title}
Content:
{body[:2000]}

Candidate entries to link:
{candidates}"""

    try:
        result = await llm.complete(prompt, system=system, max_tokens=512)
        result = result.strip()
        if result.startswith("```"):
            result = result.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        suggestions_raw = json.loads(result)
        suggestions = []
        for s in suggestions_raw:
            if isinstance(s, dict) and "target_id" in s:
                suggestions.append(
                    AILinkSuggestion(
                        target_id=s["target_id"],
                        target_kb=req.kb_name,
                        target_title=s.get("target_title", ""),
                        reason=s.get("reason", ""),
                    )
                )
        return AILinkSuggestResponse(suggestions=suggestions)
    except (json.JSONDecodeError, TypeError):
        logger.warning("AI suggest-links returned non-JSON: %s", result[:200])
        return AILinkSuggestResponse(suggestions=[])
    except Exception as e:
        logger.exception("AI suggest-links failed")
        raise HTTPException(status_code=500, detail={"code": "AI_ERROR", "message": str(e)})


@router.post("/chat")
@limiter.limit("30/minute")
async def ai_chat(
    request: Request,
    req: AIChatRequest,
    llm: LLMService = Depends(get_llm_service),
    svc: KBService = Depends(get_kb_service),
):
    """Chat with your knowledge base using RAG. Returns SSE stream."""
    _require_configured(llm)

    if not req.messages:
        raise HTTPException(
            status_code=400, detail={"code": "INVALID_REQUEST", "message": "No messages provided"}
        )

    last_msg = req.messages[-1].content

    # RAG: search KB for context
    sources = []
    context_text = ""
    try:
        from ...services.search_service import SearchService

        cfg = get_config()
        db = get_db()
        search_svc = SearchService(db, settings=cfg.settings)

        try:
            results = search_svc.search(
                query=last_msg,
                kb_name=req.kb,
                limit=5,
                mode="hybrid",
            )
        except Exception:
            results = search_svc.search(
                query=last_msg,
                kb_name=req.kb,
                limit=5,
                mode="keyword",
            )

        for r in results:
            sources.append(
                {
                    "id": r.get("id", ""),
                    "kb_name": r.get("kb_name", ""),
                    "title": r.get("title", ""),
                    "snippet": (r.get("snippet") or "")[:200],
                }
            )
            # Fetch full entry for richer context
            full = svc.get_entry(r["id"], kb_name=r.get("kb_name"))
            if full:
                body_preview = (full.get("body") or "")[:500]
                context_text += f"\n---\n[[{r['id']}]] {r.get('title', '')}\n{body_preview}\n"
    except Exception:
        logger.exception("RAG search failed, proceeding without context")

    # If chatting about a specific entry, include it
    if req.entry_id and req.kb:
        entry = svc.get_entry(req.entry_id, kb_name=req.kb)
        if entry:
            entry_body = (entry.get("body") or "")[:1500]
            context_text = (
                f"\n---\nCurrent entry [[{req.entry_id}]] {entry.get('title', '')}\n{entry_body}\n"
                + context_text
            )

    system = f"""You are a research assistant for a knowledge base. Answer the user's question using the provided context from the KB.
Cite entries using [[entry-id]] notation. Be concise and helpful.
If the context doesn't contain enough information to fully answer, say so.

KB Context:
{context_text}"""

    # Build full prompt from message history
    history = ""
    for msg in req.messages[:-1]:
        role_label = "User" if msg.role == "user" else "Assistant"
        history += f"{role_label}: {msg.content}\n\n"
    prompt = f"{history}User: {last_msg}" if history else last_msg

    async def event_stream():
        try:
            async for token in llm.stream(prompt, system=system):
                data = json.dumps({"type": "token", "content": token})
                yield f"data: {data}\n\n"

            if sources:
                data = json.dumps({"type": "sources", "entries": sources})
                yield f"data: {data}\n\n"

            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        except Exception as e:
            logger.exception("AI chat stream error")
            data = json.dumps({"type": "error", "message": str(e)})
            yield f"data: {data}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
