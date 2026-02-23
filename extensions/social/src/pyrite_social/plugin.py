"""Social KB plugin — Everything2-inspired community knowledge base for pyrite."""

from collections.abc import Callable
from typing import Any

from .entry_types import UserProfileEntry, WriteupEntry
from .hooks import (
    after_delete_adjust_reputation,
    after_save_update_counts,
    before_save_author_check,
)
from .preset import SOCIAL_PRESET
from .tables import SOCIAL_TABLES
from .validators import validate_social


class SocialPlugin:
    """Social KB plugin for pyrite.

    Provides community-driven knowledge management with user-authored writeups,
    voting, reputation tracking, and author-only editing enforcement.
    """

    name = "social"

    def get_entry_types(self) -> dict[str, type]:
        return {
            "writeup": WriteupEntry,
            "user_profile": UserProfileEntry,
        }

    def get_kb_types(self) -> list[str]:
        return ["social"]

    def get_cli_commands(self) -> list[tuple[str, Any]]:
        from .cli import social_app

        return [("social", social_app)]

    def get_mcp_tools(self, tier: str) -> dict[str, dict]:
        tools = {}

        # Read-tier tools
        if tier in ("read", "write", "admin"):
            tools["social_top"] = {
                "description": "Get highest-voted writeups in a social KB",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "kb_name": {"type": "string", "description": "KB name (optional)"},
                        "period": {
                            "type": "string",
                            "enum": ["week", "month", "all"],
                            "description": "Time period (default: all)",
                        },
                        "limit": {"type": "integer", "description": "Max results (default 10)"},
                    },
                    "required": [],
                },
                "handler": self._mcp_top,
            }
            tools["social_newest"] = {
                "description": "Get most recent writeups in a social KB",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "kb_name": {"type": "string", "description": "KB name (optional)"},
                        "limit": {"type": "integer", "description": "Max results (default 10)"},
                    },
                    "required": [],
                },
                "handler": self._mcp_newest,
            }
            tools["social_reputation"] = {
                "description": "Get reputation score for a user",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string", "description": "User ID"},
                    },
                    "required": ["user_id"],
                },
                "handler": self._mcp_reputation,
            }

        # Write-tier tools
        if tier in ("write", "admin"):
            tools["social_vote"] = {
                "description": "Vote on a writeup (up or down)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "entry_id": {"type": "string", "description": "Entry ID to vote on"},
                        "kb_name": {"type": "string", "description": "KB name"},
                        "user_id": {"type": "string", "description": "Voter user ID"},
                        "value": {
                            "type": "integer",
                            "enum": [1, -1],
                            "description": "Vote value: 1 (up) or -1 (down)",
                        },
                    },
                    "required": ["entry_id", "kb_name", "user_id", "value"],
                },
                "handler": self._mcp_vote,
            }
            tools["social_post"] = {
                "description": "Create a new writeup in a social KB",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "kb_name": {"type": "string", "description": "Target KB"},
                        "title": {"type": "string", "description": "Writeup title"},
                        "body": {"type": "string", "description": "Writeup body (markdown)"},
                        "author_id": {"type": "string", "description": "Author user ID"},
                        "writeup_type": {
                            "type": "string",
                            "enum": ["essay", "story", "review", "howto", "opinion"],
                            "description": "Writeup type (default: essay)",
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Tags",
                        },
                    },
                    "required": ["kb_name", "title", "body", "author_id"],
                },
                "handler": self._mcp_post,
            }

        return tools

    def get_db_tables(self) -> list[dict]:
        return SOCIAL_TABLES

    def get_hooks(self) -> dict[str, list[Callable]]:
        return {
            "before_save": [before_save_author_check],
            "after_save": [after_save_update_counts],
            "after_delete": [after_delete_adjust_reputation],
        }

    def get_validators(self) -> list[Callable]:
        return [validate_social]

    def get_kb_presets(self) -> dict[str, dict]:
        return {"social": SOCIAL_PRESET}

    # =========================================================================
    # MCP tool handlers
    # =========================================================================

    def _mcp_top(self, args: dict[str, Any]) -> dict[str, Any]:
        """Get highest-voted writeups."""
        import json

        from pyrite.config import load_config
        from pyrite.storage.database import PyriteDB

        config = load_config()
        db = PyriteDB(config.settings.index_path)
        kb_name = args.get("kb_name")
        period = args.get("period", "all")
        limit = args.get("limit", 10)

        try:
            query = """
                SELECT e.id, e.title, e.kb_name, e.metadata,
                       COALESCE(SUM(v.value), 0) as score
                FROM entry e
                LEFT JOIN social_vote v ON e.id = v.entry_id AND e.kb_name = v.kb_name
                WHERE e.entry_type = 'writeup'
            """
            params: list = []
            if kb_name:
                query += " AND e.kb_name = ?"
                params.append(kb_name)
            if period == "week":
                query += " AND v.created_at >= datetime('now', '-7 days')"
            elif period == "month":
                query += " AND v.created_at >= datetime('now', '-30 days')"
            query += " GROUP BY e.id, e.kb_name ORDER BY score DESC LIMIT ?"
            params.append(limit)

            rows = db._raw_conn.execute(query, params).fetchall()
            results = []
            for row in rows:
                meta = {}
                if row["metadata"]:
                    try:
                        meta = json.loads(row["metadata"])
                    except (json.JSONDecodeError, TypeError):
                        pass
                results.append(
                    {
                        "id": row["id"],
                        "title": row["title"],
                        "kb_name": row["kb_name"],
                        "score": row["score"],
                        "author_id": meta.get("author_id", ""),
                    }
                )
            return {"count": len(results), "top": results}
        finally:
            db.close()

    def _mcp_newest(self, args: dict[str, Any]) -> dict[str, Any]:
        """Get most recent writeups."""
        import json

        from pyrite.config import load_config
        from pyrite.storage.database import PyriteDB

        config = load_config()
        db = PyriteDB(config.settings.index_path)
        kb_name = args.get("kb_name")
        limit = args.get("limit", 10)

        try:
            query = "SELECT * FROM entry WHERE entry_type = 'writeup'"
            params: list = []
            if kb_name:
                query += " AND kb_name = ?"
                params.append(kb_name)
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)

            rows = db._raw_conn.execute(query, params).fetchall()
            results = []
            for row in rows:
                meta = {}
                if row["metadata"]:
                    try:
                        meta = json.loads(row["metadata"])
                    except (json.JSONDecodeError, TypeError):
                        pass
                results.append(
                    {
                        "id": row["id"],
                        "title": row["title"],
                        "kb_name": row["kb_name"],
                        "author_id": meta.get("author_id", ""),
                        "writeup_type": meta.get("writeup_type", "essay"),
                        "created_at": str(row["created_at"] or ""),
                    }
                )
            return {"count": len(results), "newest": results}
        finally:
            db.close()

    def _mcp_reputation(self, args: dict[str, Any]) -> dict[str, Any]:
        """Get user reputation."""
        from pyrite.config import load_config
        from pyrite.storage.database import PyriteDB

        config = load_config()
        db = PyriteDB(config.settings.index_path)
        user_id = args["user_id"]

        try:
            row = db._raw_conn.execute(
                """SELECT COALESCE(SUM(v.value), 0) as total
                   FROM social_vote v
                   JOIN entry e ON v.entry_id = e.id AND v.kb_name = e.kb_name
                   WHERE json_extract(e.metadata, '$.author_id') = ?""",
                (user_id,),
            ).fetchone()
            vote_rep = row["total"] if row else 0

            log_row = db._raw_conn.execute(
                "SELECT COALESCE(SUM(delta), 0) as total FROM social_reputation_log WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            log_rep = log_row["total"] if log_row else 0

            return {
                "user_id": user_id,
                "reputation": vote_rep + log_rep,
                "from_votes": vote_rep,
                "from_adjustments": log_rep,
            }
        finally:
            db.close()

    def _mcp_vote(self, args: dict[str, Any]) -> dict[str, Any]:
        """Cast a vote on a writeup."""
        from datetime import UTC, datetime

        from pyrite.config import load_config
        from pyrite.storage.database import PyriteDB

        config = load_config()
        db = PyriteDB(config.settings.index_path)

        try:
            now = datetime.now(UTC).isoformat()
            db._raw_conn.execute(
                """INSERT INTO social_vote (entry_id, kb_name, user_id, value, created_at)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(entry_id, kb_name, user_id)
                   DO UPDATE SET value = ?, created_at = ?""",
                (
                    args["entry_id"],
                    args["kb_name"],
                    args["user_id"],
                    args["value"],
                    now,
                    args["value"],
                    now,
                ),
            )
            db._raw_conn.commit()
            return {"voted": True, "entry_id": args["entry_id"], "value": args["value"]}
        finally:
            db.close()

    def _mcp_post(self, args: dict[str, Any]) -> dict[str, Any]:
        """Create a new writeup."""
        from pyrite.config import load_config
        from pyrite.schema import generate_entry_id
        from pyrite.storage.database import PyriteDB
        from pyrite.storage.index import IndexManager
        from pyrite.storage.repository import KBRepository

        config = load_config()
        kb_name = args["kb_name"]
        kb_config = config.get_kb(kb_name)
        if not kb_config:
            return {"error": f"KB '{kb_name}' not found"}

        entry = WriteupEntry(
            id=generate_entry_id(args["title"]),
            title=args["title"],
            body=args["body"],
            author_id=args["author_id"],
            writeup_type=args.get("writeup_type", "essay"),
            tags=args.get("tags", []),
        )

        repo = KBRepository(kb_config)
        file_path = repo.save(entry)

        db = PyriteDB(config.settings.index_path)
        try:
            index_mgr = IndexManager(db, config)
            index_mgr.index_entry(entry, kb_name, file_path)
            return {"created": True, "entry_id": entry.id, "file_path": str(file_path)}
        finally:
            db.close()
