"""Zettelkasten plugin — personal knowledge management for pyrite."""

from collections.abc import Callable
from typing import Any

from .entry_types import LiteratureNoteEntry, ZettelEntry
from .preset import ZETTELKASTEN_PRESET
from .validators import validate_zettel


class ZettelkastenPlugin:
    """Zettelkasten plugin for pyrite.

    Provides atomic note-taking with CEQRC workflow,
    maturity tracking, and literature note management.
    """

    name = "zettelkasten"

    def get_entry_types(self) -> dict[str, type]:
        return {
            "zettel": ZettelEntry,
            "literature_note": LiteratureNoteEntry,
        }

    def get_kb_types(self) -> list[str]:
        return ["zettelkasten"]

    def get_cli_commands(self) -> list[tuple[str, Any]]:
        from .cli import zettel_app

        return [("zettel", zettel_app)]

    def get_mcp_tools(self, tier: str) -> dict[str, dict]:
        tools = {}
        if tier in ("read", "write", "admin"):
            tools["zettel_inbox"] = {
                "description": "List unprocessed fleeting notes in the Zettelkasten inbox",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "kb_name": {
                            "type": "string",
                            "description": "KB to search (optional)",
                        },
                    },
                    "required": [],
                },
                "handler": self._mcp_inbox,
            }
            tools["zettel_graph"] = {
                "description": "Get link structure for a note and its neighbors",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "entry_id": {
                            "type": "string",
                            "description": "Entry ID to get graph for",
                        },
                        "kb_name": {
                            "type": "string",
                            "description": "KB name",
                        },
                        "depth": {
                            "type": "integer",
                            "description": "Link traversal depth (default 1)",
                        },
                    },
                    "required": ["entry_id", "kb_name"],
                },
                "handler": self._mcp_graph,
            }
        return tools

    def get_relationship_types(self) -> dict[str, dict]:
        return {
            "elaborates": {
                "inverse": "elaborated_by",
                "description": "Elaborates on another note",
            },
            "elaborated_by": {
                "inverse": "elaborates",
                "description": "Elaborated by another note",
            },
            "branches_from": {
                "inverse": "has_branch",
                "description": "Branches from a parent note",
            },
            "has_branch": {
                "inverse": "branches_from",
                "description": "Has a branch note",
            },
            "synthesizes": {
                "inverse": "synthesized_from",
                "description": "Synthesizes multiple notes into a permanent note",
            },
            "synthesized_from": {
                "inverse": "synthesizes",
                "description": "Was synthesized from into a permanent note",
            },
        }

    def get_validators(self) -> list[Callable]:
        return [validate_zettel]

    def get_kb_presets(self) -> dict[str, dict]:
        return {"zettelkasten": ZETTELKASTEN_PRESET}

    # =========================================================================
    # MCP tool handlers
    # =========================================================================

    def _mcp_inbox(self, args: dict[str, Any]) -> dict[str, Any]:
        """List unprocessed fleeting notes."""
        import json

        from pyrite.config import load_config
        from pyrite.storage.database import PyriteDB

        config = load_config()
        db = PyriteDB(config.settings.index_path)
        kb_name = args.get("kb_name")

        try:
            results = db.search("*", limit=500)
            inbox = []
            for r in results:
                if r.get("entry_type") != "zettel":
                    continue
                if kb_name and r.get("kb_name") != kb_name:
                    continue
                meta = r.get("metadata") or {}
                if isinstance(meta, str):
                    try:
                        meta = json.loads(meta)
                    except (json.JSONDecodeError, TypeError):
                        meta = {}
                zt = meta.get("zettel_type", "")
                stage = meta.get("processing_stage", "")
                if zt == "fleeting" and stage != "connect":
                    inbox.append(
                        {
                            "id": r.get("id"),
                            "title": r.get("title"),
                            "processing_stage": stage or "capture",
                            "kb_name": r.get("kb_name"),
                        }
                    )

            return {"count": len(inbox), "inbox": inbox}
        finally:
            db.close()

    def _mcp_graph(self, args: dict[str, Any]) -> dict[str, Any]:
        """Get link graph around a note."""
        from pyrite.config import load_config
        from pyrite.storage.database import PyriteDB

        config = load_config()
        db = PyriteDB(config.settings.index_path)
        entry_id = args["entry_id"]
        kb_name = args["kb_name"]
        depth = args.get("depth", 1)

        try:
            entry = db.get_entry(entry_id, kb_name)
            if not entry:
                return {"error": f"Entry '{entry_id}' not found"}

            outlinks = db.get_outlinks(entry_id, kb_name)
            backlinks = db.get_backlinks(entry_id, kb_name)

            graph = {
                "center": {"id": entry_id, "title": entry.get("title", "")},
                "outlinks": outlinks,
                "backlinks": backlinks,
            }

            # If depth > 1, get neighbors' links too
            if depth > 1:
                neighbor_links = {}
                for link in outlinks + backlinks:
                    nid = link.get("target_id") or link.get("source_id", "")
                    nkb = link.get("target_kb") or link.get("source_kb", kb_name)
                    if nid and nid != entry_id:
                        neighbor_links[nid] = {
                            "outlinks": db.get_outlinks(nid, nkb),
                            "backlinks": db.get_backlinks(nid, nkb),
                        }
                graph["neighbors"] = neighbor_links

            return graph
        finally:
            db.close()
