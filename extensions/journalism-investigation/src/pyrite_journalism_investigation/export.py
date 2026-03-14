"""Investigation pack export — build and serialize a self-contained investigation pack."""

import json
from typing import Any

from .queries import query_evidence_chain
from .utils import parse_meta

# Entry types for each section
ENTITY_TYPES = ["person", "organization", "asset", "account"]
EVENT_TYPES = ["investigation_event", "transaction", "legal_action"]
CONNECTION_TYPES = ["ownership", "membership", "funding"]


def build_investigation_pack(
    db: Any,
    kb_name: str,
    *,
    redact_sources: bool = False,
    min_importance: int = 0,
) -> dict[str, Any]:
    """Build a complete investigation pack from the KB.

    Returns a dict with sections: summary, timeline, entities, connections,
    claims, sources, evidence_chains.
    """

    def _passes_importance(entry: dict) -> bool:
        if not min_importance:
            return True
        return int(entry.get("importance", 5)) >= min_importance

    # --- Collect all entries by type ---
    counts: dict[str, int] = {}

    # Entities grouped by type
    entities: dict[str, list[dict]] = {}
    for etype in ENTITY_TYPES:
        results = db.list_entries(kb_name=kb_name, entry_type=etype, limit=5000)
        filtered = [r for r in results if _passes_importance(r)]
        counts[etype] = len(filtered)
        entities[etype] = [
            {
                "id": r.get("id"),
                "title": r.get("title"),
                "type": etype,
                "importance": int(r.get("importance", 5)),
            }
            for r in filtered
        ]

    # Timeline events
    timeline: list[dict] = []
    for etype in EVENT_TYPES:
        results = db.list_entries(kb_name=kb_name, entry_type=etype, limit=5000)
        for r in results:
            if not _passes_importance(r):
                continue
            meta = parse_meta(r)
            actors = meta.get("actors") or meta.get("parties") or []
            timeline.append({
                "id": r.get("id"),
                "title": r.get("title"),
                "type": etype,
                "date": str(r.get("date", "")),
                "importance": int(r.get("importance", 5)),
                "actors": actors,
            })
        counts[etype] = len([e for e in timeline if e["type"] == etype])
    timeline.sort(key=lambda e: e.get("date", ""))

    # Date range from timeline
    dates = [e["date"] for e in timeline if e["date"]]
    date_range = {"from": min(dates) if dates else None, "to": max(dates) if dates else None}

    # Connections
    connections: list[dict] = []
    for ctype in CONNECTION_TYPES:
        results = db.list_entries(kb_name=kb_name, entry_type=ctype, limit=5000)
        for r in results:
            if not _passes_importance(r):
                continue
            connections.append({
                "id": r.get("id"),
                "title": r.get("title"),
                "type": ctype,
                "importance": int(r.get("importance", 5)),
            })
        counts[ctype] = len([c for c in connections if c["type"] == ctype])

    # Claims
    claim_results = db.list_entries(kb_name=kb_name, entry_type="claim", limit=5000)
    claims: list[dict] = []
    for r in claim_results:
        if not _passes_importance(r):
            continue
        meta = parse_meta(r)
        evidence_refs = meta.get("evidence_refs", []) or []
        claims.append({
            "id": r.get("id"),
            "title": r.get("title"),
            "assertion": meta.get("assertion", ""),
            "claim_status": meta.get("claim_status", "unverified"),
            "confidence": meta.get("confidence", "low"),
            "importance": int(r.get("importance", 5)),
            "evidence_count": len(evidence_refs),
        })
    counts["claim"] = len(claims)

    # Sources
    source_results = db.list_entries(kb_name=kb_name, entry_type="document_source", limit=5000)
    sources: list[dict] = []
    for r in source_results:
        if not _passes_importance(r):
            continue
        meta = parse_meta(r)
        title = "[REDACTED]" if redact_sources else r.get("title", "")
        url = "[REDACTED]" if redact_sources else meta.get("url", "")
        sources.append({
            "id": r.get("id"),
            "title": title,
            "reliability": meta.get("reliability", "unknown"),
            "classification": meta.get("classification", ""),
            "url": url,
        })
    counts["document_source"] = len(sources)

    # Evidence chains for each claim
    evidence_chains: list[dict] = []
    for claim in claims:
        chain = query_evidence_chain(db, kb_name, claim["id"])
        if redact_sources:
            for ev in chain.get("evidence_chain", []):
                src = ev.get("source_document")
                if src:
                    src["title"] = "[REDACTED]"
        evidence_chains.append(chain)

    # Summary
    summary = {
        "kb_name": kb_name,
        "counts": counts,
        "date_range": date_range,
    }

    return {
        "summary": summary,
        "timeline": timeline,
        "entities": entities,
        "connections": connections,
        "claims": claims,
        "sources": sources,
        "evidence_chains": evidence_chains,
    }


def export_as_json(pack: dict) -> str:
    """Serialize pack to formatted JSON string."""
    return json.dumps(pack, indent=2, ensure_ascii=False)


def export_as_markdown(pack: dict) -> str:
    """Render pack as a readable Markdown document."""
    lines: list[str] = []
    kb_name = pack["summary"]["kb_name"]
    lines.append(f"# Investigation Pack: {kb_name}")
    lines.append("")

    # Summary
    lines.append("## Summary")
    lines.append("")
    counts = pack["summary"]["counts"]
    for type_name, count in sorted(counts.items()):
        lines.append(f"- **{type_name}**: {count}")
    dr = pack["summary"].get("date_range", {})
    if dr.get("from") or dr.get("to"):
        lines.append(f"- **Date range**: {dr.get('from', '?')} to {dr.get('to', '?')}")
    lines.append("")

    # Timeline
    lines.append("## Timeline")
    lines.append("")
    if pack["timeline"]:
        lines.append("| Date | Title | Type | Actors |")
        lines.append("|------|-------|------|--------|")
        for e in pack["timeline"]:
            actors = ", ".join(e.get("actors", []))
            lines.append(f"| {e['date']} | {e['title']} | {e['type']} | {actors} |")
    else:
        lines.append("No events.")
    lines.append("")

    # Entities
    lines.append("## Entities")
    lines.append("")
    for etype, elist in pack["entities"].items():
        lines.append(f"### {etype}")
        lines.append("")
        if elist:
            for ent in elist:
                lines.append(f"- {ent['title']} (`{ent['id']}`, importance: {ent['importance']})")
        else:
            lines.append("None.")
        lines.append("")

    # Connections
    lines.append("## Connections")
    lines.append("")
    if pack["connections"]:
        for c in pack["connections"]:
            lines.append(f"- [{c['type']}] {c['title']} (`{c['id']}`)")
    else:
        lines.append("No connections.")
    lines.append("")

    # Claims
    lines.append("## Claims")
    lines.append("")
    if pack["claims"]:
        lines.append("| Title | Status | Confidence | Evidence Count |")
        lines.append("|-------|--------|------------|----------------|")
        for c in pack["claims"]:
            lines.append(f"| {c['title']} | {c['claim_status']} | {c['confidence']} | {c['evidence_count']} |")
    else:
        lines.append("No claims.")
    lines.append("")

    # Sources
    lines.append("## Sources")
    lines.append("")
    if pack["sources"]:
        lines.append("| Title | Reliability | Classification | URL |")
        lines.append("|-------|-------------|----------------|-----|")
        for s in pack["sources"]:
            lines.append(f"| {s['title']} | {s['reliability']} | {s.get('classification', '')} | {s.get('url', '')} |")
    else:
        lines.append("No sources.")
    lines.append("")

    # Evidence Chains
    lines.append("## Evidence Chains")
    lines.append("")
    if pack["evidence_chains"]:
        for chain_data in pack["evidence_chains"]:
            claim = chain_data.get("claim", {})
            lines.append(f"### {claim.get('title', 'Unknown claim')}")
            lines.append(f"- Status: {claim.get('claim_status', '?')}, Confidence: {claim.get('confidence', '?')}")
            chain_items = chain_data.get("evidence_chain", [])
            if chain_items:
                for ev in chain_items:
                    src = ev.get("source_document")
                    src_label = f" -> {src['title']} ({src['reliability']})" if src else ""
                    lines.append(f"  - {ev.get('title', ev.get('evidence_id', '?'))}{src_label}")
            gaps = chain_data.get("gaps", [])
            if gaps:
                lines.append("- **Gaps**:")
                for g in gaps:
                    lines.append(f"  - {g}")
            lines.append("")
    else:
        lines.append("No evidence chains.")
        lines.append("")

    return "\n".join(lines)
