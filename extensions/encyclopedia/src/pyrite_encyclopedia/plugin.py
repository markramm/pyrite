"""Encyclopedia plugin — Wikipedia-inspired collaborative knowledge base for pyrite."""

from collections.abc import Callable
from typing import Any

from .entry_types import ArticleEntry, TalkPageEntry
from .preset import ENCYCLOPEDIA_PRESET
from .tables import ENCYCLOPEDIA_TABLES
from .validators import validate_encyclopedia
from .workflows import ARTICLE_REVIEW_WORKFLOW


class EncyclopediaPlugin:
    """Encyclopedia plugin for pyrite.

    Provides collaborative article editing with quality assessment,
    review workflows, protection levels, and talk pages.
    """

    name = "encyclopedia"

    def get_entry_types(self) -> dict[str, type]:
        return {
            "article": ArticleEntry,
            "talk_page": TalkPageEntry,
        }

    def get_kb_types(self) -> list[str]:
        return ["encyclopedia"]

    def get_cli_commands(self) -> list[tuple[str, Any]]:
        from .cli import wiki_app

        return [("wiki", wiki_app)]

    def get_mcp_tools(self, tier: str) -> dict[str, dict]:
        tools = {}

        # Read-tier tools
        if tier in ("read", "write", "admin"):
            tools["wiki_quality_stats"] = {
                "description": "Get quality distribution and review queue stats for encyclopedia articles",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "kb_name": {"type": "string", "description": "KB name (optional)"},
                    },
                    "required": [],
                },
                "handler": self._mcp_quality_stats,
            }
            tools["wiki_review_queue"] = {
                "description": "Get articles currently under review",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "kb_name": {"type": "string", "description": "KB name (optional)"},
                        "limit": {"type": "integer", "description": "Max results (default 20)"},
                    },
                    "required": [],
                },
                "handler": self._mcp_review_queue,
            }
            tools["wiki_stubs"] = {
                "description": "List stub articles needing expansion",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "kb_name": {"type": "string", "description": "KB name (optional)"},
                        "limit": {"type": "integer", "description": "Max results (default 20)"},
                    },
                    "required": [],
                },
                "handler": self._mcp_stubs,
            }

        # Write-tier tools
        if tier in ("write", "admin"):
            tools["wiki_submit_review"] = {
                "description": "Submit a review for an article (approve, reject, or comment)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "entry_id": {"type": "string", "description": "Article entry ID"},
                        "kb_name": {"type": "string", "description": "KB name"},
                        "reviewer_id": {"type": "string", "description": "Reviewer user ID"},
                        "action": {
                            "type": "string",
                            "enum": ["approve", "reject", "comment"],
                            "description": "Review action",
                        },
                        "comments": {"type": "string", "description": "Review comments"},
                    },
                    "required": ["entry_id", "kb_name", "reviewer_id", "action"],
                },
                "handler": self._mcp_submit_review,
            }
            tools["wiki_assess_quality"] = {
                "description": "Assess or change an article's quality level",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "entry_id": {"type": "string", "description": "Article entry ID"},
                        "kb_name": {"type": "string", "description": "KB name"},
                        "quality": {
                            "type": "string",
                            "enum": ["stub", "start", "C", "B", "GA", "FA"],
                            "description": "New quality level",
                        },
                    },
                    "required": ["entry_id", "kb_name", "quality"],
                },
                "handler": self._mcp_assess_quality,
            }

        # Admin-tier tools
        if tier == "admin":
            tools["wiki_protect"] = {
                "description": "Set protection level on an article",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "entry_id": {"type": "string", "description": "Article entry ID"},
                        "kb_name": {"type": "string", "description": "KB name"},
                        "level": {
                            "type": "string",
                            "enum": ["none", "semi", "full"],
                            "description": "Protection level",
                        },
                    },
                    "required": ["entry_id", "kb_name", "level"],
                },
                "handler": self._mcp_protect,
            }

        return tools

    def get_db_tables(self) -> list[dict]:
        return ENCYCLOPEDIA_TABLES

    def get_workflows(self) -> dict[str, dict]:
        return {"article_review": ARTICLE_REVIEW_WORKFLOW}

    def get_validators(self) -> list[Callable]:
        return [validate_encyclopedia]

    def get_kb_presets(self) -> dict[str, dict]:
        return {"encyclopedia": ENCYCLOPEDIA_PRESET}

    # =========================================================================
    # MCP tool handlers
    # =========================================================================

    def _mcp_quality_stats(self, args: dict[str, Any]) -> dict[str, Any]:
        """Get quality distribution and review queue stats."""
        import json

        from pyrite.config import load_config
        from pyrite.storage.database import PyriteDB

        config = load_config()
        db = PyriteDB(config.settings.index_path)
        kb_name = args.get("kb_name")

        try:
            query = "SELECT * FROM entry WHERE entry_type = 'article'"
            params: list = []
            if kb_name:
                query += " AND kb_name = ?"
                params.append(kb_name)

            rows = db._raw_conn.execute(query, params).fetchall()

            quality_counts: dict[str, int] = {}
            review_counts: dict[str, int] = {}

            for row in rows:
                meta = {}
                if row["metadata"]:
                    try:
                        meta = json.loads(row["metadata"])
                    except (json.JSONDecodeError, TypeError):
                        pass
                q = meta.get("quality", "stub")
                r = meta.get("review_status", "draft")
                quality_counts[q] = quality_counts.get(q, 0) + 1
                review_counts[r] = review_counts.get(r, 0) + 1

            return {
                "total_articles": len(rows),
                "quality_distribution": quality_counts,
                "review_status_distribution": review_counts,
                "review_queue_size": review_counts.get("under_review", 0),
            }
        finally:
            db.close()

    def _mcp_review_queue(self, args: dict[str, Any]) -> dict[str, Any]:
        """Get articles under review."""
        import json

        from pyrite.config import load_config
        from pyrite.storage.database import PyriteDB

        config = load_config()
        db = PyriteDB(config.settings.index_path)
        kb_name = args.get("kb_name")
        limit = args.get("limit", 20)

        try:
            query = "SELECT * FROM entry WHERE entry_type = 'article'"
            params: list = []
            if kb_name:
                query += " AND kb_name = ?"
                params.append(kb_name)
            query += " ORDER BY updated_at DESC"

            rows = db._raw_conn.execute(query, params).fetchall()

            queue = []
            for row in rows:
                meta = {}
                if row["metadata"]:
                    try:
                        meta = json.loads(row["metadata"])
                    except (json.JSONDecodeError, TypeError):
                        pass
                if meta.get("review_status") == "under_review":
                    queue.append(
                        {
                            "id": row["id"],
                            "title": row["title"],
                            "kb_name": row["kb_name"],
                            "quality": meta.get("quality", "stub"),
                        }
                    )
                if len(queue) >= limit:
                    break

            return {"count": len(queue), "queue": queue}
        finally:
            db.close()

    def _mcp_stubs(self, args: dict[str, Any]) -> dict[str, Any]:
        """List stub articles."""
        import json

        from pyrite.config import load_config
        from pyrite.storage.database import PyriteDB

        config = load_config()
        db = PyriteDB(config.settings.index_path)
        kb_name = args.get("kb_name")
        limit = args.get("limit", 20)

        try:
            query = "SELECT * FROM entry WHERE entry_type = 'article'"
            params: list = []
            if kb_name:
                query += " AND kb_name = ?"
                params.append(kb_name)
            query += " ORDER BY created_at ASC"

            rows = db._raw_conn.execute(query, params).fetchall()

            stubs = []
            for row in rows:
                meta = {}
                if row["metadata"]:
                    try:
                        meta = json.loads(row["metadata"])
                    except (json.JSONDecodeError, TypeError):
                        pass
                if meta.get("quality", "stub") == "stub":
                    stubs.append(
                        {
                            "id": row["id"],
                            "title": row["title"],
                            "kb_name": row["kb_name"],
                        }
                    )
                if len(stubs) >= limit:
                    break

            return {"count": len(stubs), "stubs": stubs}
        finally:
            db.close()

    def _mcp_submit_review(self, args: dict[str, Any]) -> dict[str, Any]:
        """Submit a review."""
        from datetime import UTC, datetime

        from pyrite.config import load_config
        from pyrite.storage.database import PyriteDB

        config = load_config()
        db = PyriteDB(config.settings.index_path)

        try:
            now = datetime.now(UTC).isoformat()
            db._raw_conn.execute(
                """INSERT INTO encyclopedia_review
                   (entry_id, kb_name, reviewer_id, status, comments, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    args["entry_id"],
                    args["kb_name"],
                    args["reviewer_id"],
                    args["action"],
                    args.get("comments", ""),
                    now,
                ),
            )
            db._raw_conn.commit()
            return {
                "reviewed": True,
                "entry_id": args["entry_id"],
                "action": args["action"],
            }
        finally:
            db.close()

    def _mcp_assess_quality(self, args: dict[str, Any]) -> dict[str, Any]:
        """Assess article quality."""
        from .entry_types import QUALITY_LEVELS

        quality = args["quality"]
        if quality not in QUALITY_LEVELS:
            return {"error": f"Invalid quality: {quality}"}

        return {
            "assessed": True,
            "entry_id": args["entry_id"],
            "quality": quality,
            "note": "Update the article's frontmatter to apply the quality change.",
        }

    def _mcp_protect(self, args: dict[str, Any]) -> dict[str, Any]:
        """Set article protection level."""
        from .entry_types import PROTECTION_LEVELS

        level = args["level"]
        if level not in PROTECTION_LEVELS:
            return {"error": f"Invalid protection level: {level}"}

        return {
            "protected": True,
            "entry_id": args["entry_id"],
            "level": level,
            "note": "Update the article's frontmatter to apply protection.",
        }
