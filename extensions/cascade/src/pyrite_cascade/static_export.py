"""Static JSON export for Cascade timeline viewer consumption.

Generates timeline.json, actors.json, tags.json, and stats.json files
compatible with the capturecascade.org React viewer.
"""

import json
import logging
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def export_timeline(
    db: Any,
    kb_name: str,
    from_date: str = "",
    to_date: str = "",
    min_importance: int = 0,
    event_types: list[str] | None = None,
) -> dict[str, Any]:
    """Export timeline data as structured dicts ready for JSON serialization.

    Returns dict with keys: timeline, actors, tags, stats.
    """
    if event_types is None:
        event_types = ["timeline_event"]

    # Collect all events
    events: list[dict[str, Any]] = []
    actor_counter: Counter = Counter()
    tag_counter: Counter = Counter()
    total_sources = 0

    for etype in event_types:
        results = db.list_entries(kb_name=kb_name, entry_type=etype, limit=10000)
        for r in results:
            imp = int(r.get("importance", 5))
            if min_importance and imp < min_importance:
                continue

            meta = r.get("metadata") or {}
            if isinstance(meta, str):
                try:
                    meta = json.loads(meta)
                except (json.JSONDecodeError, TypeError):
                    meta = {}

            date = str(r.get("date", meta.get("date", "")))
            if from_date and date < from_date:
                continue
            if to_date and date > to_date:
                continue

            actors = meta.get("actors") or []
            tags = r.get("tags") or []
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(",") if t.strip()]

            sources = r.get("sources") or meta.get("sources") or []

            event = {
                "id": r.get("id", ""),
                "title": r.get("title", ""),
                "date": date,
                "actors": actors,
                "tags": tags,
                "sources": sources if isinstance(sources, list) else [],
                "body": r.get("body", ""),
                "importance": imp,
            }

            # Include extra metadata fields
            for key in ("capture_lanes", "capture_type", "status", "location"):
                val = meta.get(key) or r.get(key)
                if val:
                    event[key] = val

            events.append(event)

            for actor in actors:
                if actor and isinstance(actor, str):
                    actor_counter[actor] += 1
            for tag in tags:
                if tag and isinstance(tag, str):
                    tag_counter[tag] += 1
            total_sources += len(sources) if isinstance(sources, list) else 0

    # Sort events by date
    events.sort(key=lambda e: e.get("date", ""))

    # Build actors list sorted by count descending
    actors_list = [
        {"name": name, "count": count}
        for name, count in actor_counter.most_common()
    ]

    # Build tags list sorted by count descending
    tags_list = [
        {"name": name, "count": count}
        for name, count in tag_counter.most_common()
    ]

    # Build stats
    dates = [e["date"] for e in events if e.get("date")]
    stats = {
        "total_events": len(events),
        "total_actors": len(actor_counter),
        "total_tags": len(tag_counter),
        "total_sources": total_sources,
        "date_range": {
            "start": min(dates) if dates else "",
            "end": max(dates) if dates else "",
        },
        "top_actors": actors_list[:20],
        "top_tags": tags_list[:20],
        "generated": datetime.now(timezone.utc).isoformat(),
    }

    return {
        "timeline": events,
        "actors": actors_list,
        "tags": tags_list,
        "stats": stats,
    }


def write_export(result: dict[str, Any], output_dir: Path) -> None:
    """Write export results to JSON files in the output directory."""
    output_dir.mkdir(parents=True, exist_ok=True)

    (output_dir / "timeline.json").write_text(
        json.dumps(result["timeline"], indent=2, ensure_ascii=False)
    )
    (output_dir / "actors.json").write_text(
        json.dumps(result["actors"], indent=2, ensure_ascii=False)
    )
    (output_dir / "tags.json").write_text(
        json.dumps(result["tags"], indent=2, ensure_ascii=False)
    )
    (output_dir / "stats.json").write_text(
        json.dumps(result["stats"], indent=2, ensure_ascii=False)
    )
