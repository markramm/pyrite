"""Software KB plugin — ADRs, design docs, standards, components, backlog, runbooks for pyrite."""

from collections.abc import Callable
from typing import Any

from .entry_types import (
    ADREntry,
    BacklogItemEntry,
    ComponentEntry,
    DesignDocEntry,
    RunbookEntry,
    StandardEntry,
)
from .preset import SOFTWARE_KB_PRESET
from .validators import validate_software_kb
from .workflows import ADR_LIFECYCLE, BACKLOG_WORKFLOW


class SoftwareKBPlugin:
    """Software KB plugin for pyrite.

    Provides architecture decision records, design docs, coding standards,
    component documentation, backlog tracking, and runbooks.
    """

    name = "software_kb"

    def get_entry_types(self) -> dict[str, type]:
        return {
            "adr": ADREntry,
            "design_doc": DesignDocEntry,
            "standard": StandardEntry,
            "component": ComponentEntry,
            "backlog_item": BacklogItemEntry,
            "runbook": RunbookEntry,
        }

    def get_kb_types(self) -> list[str]:
        return ["software"]

    def get_cli_commands(self) -> list[tuple[str, Any]]:
        from .cli import sw_app

        return [("sw", sw_app)]

    def get_mcp_tools(self, tier: str) -> dict[str, dict]:
        tools = {}

        if tier in ("read", "write", "admin"):
            tools["sw_adrs"] = {
                "description": "List Architecture Decision Records, filter by status. Check before making architectural changes.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "kb_name": {"type": "string", "description": "KB name (optional)"},
                        "status": {
                            "type": "string",
                            "enum": ["proposed", "accepted", "deprecated", "superseded"],
                            "description": "Filter by ADR status",
                        },
                    },
                    "required": [],
                },
                "handler": self._mcp_adrs,
            }
            tools["sw_component"] = {
                "description": "Find component documentation by code path or name",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "kb_name": {"type": "string", "description": "KB name (optional)"},
                        "path": {"type": "string", "description": "Code path to search for"},
                        "name": {"type": "string", "description": "Component name to search for"},
                    },
                    "required": [],
                },
                "handler": self._mcp_component,
            }
            tools["sw_standards"] = {
                "description": "List coding standards and conventions. Check before writing code.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "kb_name": {"type": "string", "description": "KB name (optional)"},
                        "category": {
                            "type": "string",
                            "enum": [
                                "coding",
                                "testing",
                                "api",
                                "git",
                                "documentation",
                                "security",
                                "deployment",
                            ],
                            "description": "Filter by category",
                        },
                    },
                    "required": [],
                },
                "handler": self._mcp_standards,
            }
            tools["sw_backlog"] = {
                "description": "List backlog items (features, bugs, tech debt), filter by status/priority/kind",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "kb_name": {"type": "string", "description": "KB name (optional)"},
                        "status": {
                            "type": "string",
                            "enum": ["proposed", "accepted", "in_progress", "done", "wont_do"],
                            "description": "Filter by status",
                        },
                        "priority": {
                            "type": "string",
                            "enum": ["critical", "high", "medium", "low"],
                            "description": "Filter by priority",
                        },
                        "kind": {
                            "type": "string",
                            "enum": ["feature", "bug", "tech_debt", "improvement", "spike"],
                            "description": "Filter by kind",
                        },
                    },
                    "required": [],
                },
                "handler": self._mcp_backlog,
            }

        if tier in ("write", "admin"):
            tools["sw_create_adr"] = {
                "description": "Create a new ADR with auto-numbered ID and structured body",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "kb_name": {"type": "string", "description": "KB name"},
                        "title": {"type": "string", "description": "ADR title"},
                        "context": {"type": "string", "description": "Context section"},
                        "decision": {"type": "string", "description": "Decision section"},
                        "consequences": {"type": "string", "description": "Consequences section"},
                        "status": {
                            "type": "string",
                            "enum": ["proposed", "accepted"],
                            "description": "Initial status (default: proposed)",
                        },
                        "deciders": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of deciders",
                        },
                    },
                    "required": ["title"],
                },
                "handler": self._mcp_create_adr,
            }
            tools["sw_create_backlog_item"] = {
                "description": "Create a new backlog item (feature, bug, tech debt)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "kb_name": {"type": "string", "description": "KB name"},
                        "title": {"type": "string", "description": "Item title"},
                        "kind": {
                            "type": "string",
                            "enum": ["feature", "bug", "tech_debt", "improvement", "spike"],
                            "description": "Item kind",
                        },
                        "priority": {
                            "type": "string",
                            "enum": ["critical", "high", "medium", "low"],
                            "description": "Priority level",
                        },
                        "body": {"type": "string", "description": "Item description"},
                    },
                    "required": ["title", "kind"],
                },
                "handler": self._mcp_create_backlog_item,
            }

        return tools

    def get_relationship_types(self) -> dict[str, dict]:
        return {
            "implements": {
                "inverse": "implemented_by",
                "description": "Design doc implemented by a component",
            },
            "implemented_by": {
                "inverse": "implements",
                "description": "Component implements a design doc",
            },
            "supersedes": {
                "inverse": "superseded_by",
                "description": "New ADR supersedes an old one",
            },
            "superseded_by": {
                "inverse": "supersedes",
                "description": "Old ADR superseded by a new one",
            },
            "documents": {
                "inverse": "documented_by",
                "description": "Runbook documents a component",
            },
            "documented_by": {
                "inverse": "documents",
                "description": "Component documented by a runbook",
            },
            "depends_on": {
                "inverse": "depended_on_by",
                "description": "Component depends on another component",
            },
            "depended_on_by": {
                "inverse": "depends_on",
                "description": "Component depended on by another",
            },
            "tracks": {
                "inverse": "tracked_by",
                "description": "Backlog item tracks an ADR or design doc",
            },
            "tracked_by": {
                "inverse": "tracks",
                "description": "ADR/design doc tracked by a backlog item",
            },
        }

    def get_db_tables(self) -> list[dict]:
        return []

    def get_workflows(self) -> dict[str, dict]:
        return {
            "adr_lifecycle": ADR_LIFECYCLE,
            "backlog_workflow": BACKLOG_WORKFLOW,
        }

    def get_validators(self) -> list[Callable]:
        return [validate_software_kb]

    def get_kb_presets(self) -> dict[str, dict]:
        return {"software": SOFTWARE_KB_PRESET}

    # =========================================================================
    # MCP tool handlers
    # =========================================================================

    def _mcp_adrs(self, args: dict[str, Any]) -> dict[str, Any]:
        """List ADRs."""
        import json

        from pyrite.config import load_config
        from pyrite.storage.database import PyriteDB

        config = load_config()
        db = PyriteDB(config.settings.index_path)
        kb_name = args.get("kb_name")
        status_filter = args.get("status")

        try:
            query = "SELECT * FROM entry WHERE entry_type = 'adr'"
            params: list = []
            if kb_name:
                query += " AND kb_name = ?"
                params.append(kb_name)
            query += " ORDER BY created_at DESC"

            rows = db._raw_conn.execute(query, params).fetchall()
            adrs = []
            for row in rows:
                meta = {}
                if row["metadata"]:
                    try:
                        meta = json.loads(row["metadata"])
                    except (json.JSONDecodeError, TypeError):
                        pass
                status = meta.get("status", "proposed")
                if status_filter and status != status_filter:
                    continue
                adrs.append(
                    {
                        "id": row["id"],
                        "title": row["title"],
                        "adr_number": meta.get("adr_number", 0),
                        "status": status,
                        "date": meta.get("date", ""),
                        "kb_name": row["kb_name"],
                    }
                )

            return {"count": len(adrs), "adrs": adrs}
        finally:
            db.close()

    def _mcp_component(self, args: dict[str, Any]) -> dict[str, Any]:
        """Find component docs."""
        import json

        from pyrite.config import load_config
        from pyrite.storage.database import PyriteDB

        config = load_config()
        db = PyriteDB(config.settings.index_path)
        kb_name = args.get("kb_name")
        search_path = args.get("path", "")
        search_name = args.get("name", "")

        try:
            query = "SELECT * FROM entry WHERE entry_type = 'component'"
            params: list = []
            if kb_name:
                query += " AND kb_name = ?"
                params.append(kb_name)

            rows = db._raw_conn.execute(query, params).fetchall()
            results = []
            for row in rows:
                meta = {}
                if row["metadata"]:
                    try:
                        meta = json.loads(row["metadata"])
                    except (json.JSONDecodeError, TypeError):
                        pass
                comp_path = meta.get("path", "")
                comp_title = row["title"]

                match = False
                if search_path and comp_path and search_path in comp_path:
                    match = True
                if search_name and search_name.lower() in comp_title.lower():
                    match = True
                if not search_path and not search_name:
                    match = True

                if match:
                    results.append(
                        {
                            "id": row["id"],
                            "title": comp_title,
                            "kind": meta.get("kind", ""),
                            "path": comp_path,
                            "owner": meta.get("owner", ""),
                            "kb_name": row["kb_name"],
                        }
                    )

            return {"count": len(results), "components": results}
        finally:
            db.close()

    def _mcp_standards(self, args: dict[str, Any]) -> dict[str, Any]:
        """List standards."""
        import json

        from pyrite.config import load_config
        from pyrite.storage.database import PyriteDB

        config = load_config()
        db = PyriteDB(config.settings.index_path)
        kb_name = args.get("kb_name")
        category_filter = args.get("category")

        try:
            query = "SELECT * FROM entry WHERE entry_type = 'standard'"
            params: list = []
            if kb_name:
                query += " AND kb_name = ?"
                params.append(kb_name)

            rows = db._raw_conn.execute(query, params).fetchall()
            standards = []
            for row in rows:
                meta = {}
                if row["metadata"]:
                    try:
                        meta = json.loads(row["metadata"])
                    except (json.JSONDecodeError, TypeError):
                        pass
                category = meta.get("category", "")
                if category_filter and category != category_filter:
                    continue
                standards.append(
                    {
                        "id": row["id"],
                        "title": row["title"],
                        "category": category,
                        "enforced": meta.get("enforced", False),
                        "kb_name": row["kb_name"],
                    }
                )

            return {"count": len(standards), "standards": standards}
        finally:
            db.close()

    def _mcp_backlog(self, args: dict[str, Any]) -> dict[str, Any]:
        """List backlog items."""
        import json

        from pyrite.config import load_config
        from pyrite.storage.database import PyriteDB

        config = load_config()
        db = PyriteDB(config.settings.index_path)
        kb_name = args.get("kb_name")
        status_filter = args.get("status")
        priority_filter = args.get("priority")
        kind_filter = args.get("kind")

        try:
            query = "SELECT * FROM entry WHERE entry_type = 'backlog_item'"
            params: list = []
            if kb_name:
                query += " AND kb_name = ?"
                params.append(kb_name)
            query += " ORDER BY created_at DESC"

            rows = db._raw_conn.execute(query, params).fetchall()
            items = []
            for row in rows:
                meta = {}
                if row["metadata"]:
                    try:
                        meta = json.loads(row["metadata"])
                    except (json.JSONDecodeError, TypeError):
                        pass
                status = meta.get("status", "proposed")
                priority = meta.get("priority", "medium")
                kind = meta.get("kind", "")
                if status_filter and status != status_filter:
                    continue
                if priority_filter and priority != priority_filter:
                    continue
                if kind_filter and kind != kind_filter:
                    continue
                items.append(
                    {
                        "id": row["id"],
                        "title": row["title"],
                        "kind": kind,
                        "status": status,
                        "priority": priority,
                        "effort": meta.get("effort", ""),
                        "assignee": meta.get("assignee", ""),
                        "kb_name": row["kb_name"],
                    }
                )

            return {"count": len(items), "items": items}
        finally:
            db.close()

    def _mcp_create_adr(self, args: dict[str, Any]) -> dict[str, Any]:
        """Create a new ADR with auto-numbering."""
        import json

        from pyrite.config import load_config
        from pyrite.storage.database import PyriteDB

        config = load_config()
        db = PyriteDB(config.settings.index_path)
        kb_name = args.get("kb_name")

        try:
            # Find next ADR number
            query = "SELECT * FROM entry WHERE entry_type = 'adr'"
            params: list = []
            if kb_name:
                query += " AND kb_name = ?"
                params.append(kb_name)
            rows = db._raw_conn.execute(query, params).fetchall()

            max_num = 0
            for row in rows:
                meta = {}
                if row["metadata"]:
                    try:
                        meta = json.loads(row["metadata"])
                    except (json.JSONDecodeError, TypeError):
                        pass
                num = meta.get("adr_number", 0)
                if isinstance(num, int) and num > max_num:
                    max_num = num

            next_num = max_num + 1
            title = args["title"]
            slug = title.lower().replace(" ", "-")
            status = args.get("status", "proposed")

            # Build structured body
            context = args.get("context", "")
            decision = args.get("decision", "")
            consequences = args.get("consequences", "")
            body_parts = []
            body_parts.append(f"## Context\n\n{context or 'TODO'}")
            body_parts.append(f"## Decision\n\n{decision or 'TODO'}")
            body_parts.append(f"## Consequences\n\n{consequences or 'TODO'}")
            body = "\n\n".join(body_parts)

            return {
                "created": True,
                "adr_number": next_num,
                "title": title,
                "status": status,
                "filename": f"adrs/{next_num:04d}-{slug}.md",
                "body": body,
                "deciders": args.get("deciders", []),
                "note": "Create the markdown file with this frontmatter and body to complete.",
            }
        finally:
            db.close()

    def _mcp_create_backlog_item(self, args: dict[str, Any]) -> dict[str, Any]:
        """Create a new backlog item."""
        title = args["title"]
        kind = args["kind"]
        priority = args.get("priority", "medium")
        body = args.get("body", "")
        slug = title.lower().replace(" ", "-")

        return {
            "created": True,
            "title": title,
            "kind": kind,
            "priority": priority,
            "status": "proposed",
            "filename": f"backlog/{slug}.md",
            "body": body,
            "note": "Create the markdown file with this frontmatter and body to complete.",
        }
