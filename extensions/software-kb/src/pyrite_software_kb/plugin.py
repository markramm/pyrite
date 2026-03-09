"""Software KB plugin — ADRs, design docs, standards, components, backlog, runbooks for pyrite."""

from collections.abc import Callable
from typing import Any

from .entry_types import (
    ADREntry,
    BacklogItemEntry,
    ComponentEntry,
    DesignDocEntry,
    DevelopmentConventionEntry,
    MilestoneEntry,
    ProgrammaticValidationEntry,
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

    def __init__(self):
        self.ctx = None

    def set_context(self, ctx) -> None:
        """Receive shared dependencies from the plugin infrastructure."""
        self.ctx = ctx

    def _get_db(self):
        """Get DB from injected context, falling back to self-bootstrap."""
        if self.ctx is not None:
            return self.ctx.db, False
        from pyrite.config import load_config
        from pyrite.storage.database import PyriteDB

        config = load_config()
        return PyriteDB(config.settings.index_path), True

    def get_entry_types(self) -> dict[str, type]:
        return {
            "adr": ADREntry,
            "design_doc": DesignDocEntry,
            "standard": StandardEntry,
            "programmatic_validation": ProgrammaticValidationEntry,
            "development_convention": DevelopmentConventionEntry,
            "component": ComponentEntry,
            "backlog_item": BacklogItemEntry,
            "runbook": RunbookEntry,
            "milestone": MilestoneEntry,
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
                "description": "List all standards (includes standard, programmatic_validation, and development_convention types). Check before writing code.",
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
            tools["sw_validations"] = {
                "description": "List programmatic validations (automated checks). These define verifiable pass/fail criteria.",
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
                "handler": self._mcp_validations,
            }
            tools["sw_conventions"] = {
                "description": "List development conventions (judgment-based guidance). These are carried as context during work.",
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
                "handler": self._mcp_conventions,
            }
            tools["sw_milestones"] = {
                "description": "List milestones with completion stats from linked backlog items",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "kb_name": {"type": "string", "description": "KB name (optional)"},
                        "status": {
                            "type": "string",
                            "enum": ["open", "closed"],
                            "description": "Filter by milestone status",
                        },
                    },
                    "required": [],
                },
                "handler": self._mcp_milestones,
            }
            tools["sw_board"] = {
                "description": "View kanban board with backlog items grouped into lanes by status",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "kb_name": {"type": "string", "description": "KB name (optional)"},
                    },
                    "required": [],
                },
                "handler": self._mcp_board,
            }
            tools["sw_review_queue"] = {
                "description": "View items in review status, sorted by wait time. Shows WIP limit info.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "kb_name": {"type": "string", "description": "KB name (optional)"},
                    },
                    "required": [],
                },
                "handler": self._mcp_review_queue,
            }
            tools["sw_context_for_item"] = {
                "description": "Assemble full context bundle for a backlog item: linked ADRs, components, validations, conventions, milestones",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "item_id": {"type": "string", "description": "Backlog item ID"},
                        "kb_name": {"type": "string", "description": "KB name"},
                    },
                    "required": ["item_id", "kb_name"],
                },
                "handler": self._mcp_context_for_item,
            }
            tools["sw_pull_next"] = {
                "description": "Recommend next work item based on priority and WIP limits",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "kb_name": {"type": "string", "description": "KB name (optional)"},
                    },
                    "required": [],
                },
                "handler": self._mcp_pull_next,
            }
            tools["sw_backlog"] = {
                "description": "List backlog items (features, bugs, tech debt), filter by status/priority/kind",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "kb_name": {"type": "string", "description": "KB name (optional)"},
                        "status": {
                            "type": "string",
                            "enum": ["proposed", "accepted", "in_progress", "review", "done", "wont_do"],
                            "description": "Filter by status",
                        },
                        "priority": {
                            "type": "string",
                            "enum": ["critical", "high", "medium", "low"],
                            "description": "Filter by priority",
                        },
                        "kind": {
                            "type": "string",
                            "enum": ["feature", "bug", "tech_debt", "improvement", "spike", "epic"],
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
            tools["sw_claim"] = {
                "description": "Claim a backlog item: transition to in_progress and set assignee (atomic CAS)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "item_id": {"type": "string", "description": "Backlog item ID"},
                        "kb_name": {"type": "string", "description": "KB name"},
                        "assignee": {"type": "string", "description": "Who is claiming the item"},
                    },
                    "required": ["item_id", "kb_name", "assignee"],
                },
                "handler": self._mcp_claim,
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
                            "enum": ["feature", "bug", "tech_debt", "improvement", "spike", "epic"],
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
            "blocks": {
                "inverse": "blocked_by",
                "description": "Backlog item must complete before another can start",
            },
            "blocked_by": {
                "inverse": "blocks",
                "description": "Backlog item cannot start until blocker completes",
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

        db, should_close = self._get_db()
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
            if should_close:
                db.close()

    def _mcp_component(self, args: dict[str, Any]) -> dict[str, Any]:
        """Find component docs."""
        import json

        db, should_close = self._get_db()
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
            if should_close:
                db.close()

    def _mcp_standards(self, args: dict[str, Any]) -> dict[str, Any]:
        """List all standards (standard + programmatic_validation + development_convention)."""
        import json

        db, should_close = self._get_db()
        kb_name = args.get("kb_name")
        category_filter = args.get("category")

        try:
            query = "SELECT * FROM entry WHERE entry_type IN ('standard', 'programmatic_validation', 'development_convention')"
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
                        "type": row["entry_type"],
                        "category": category,
                        "enforced": meta.get("enforced", False),
                        "kb_name": row["kb_name"],
                    }
                )

            return {"count": len(standards), "standards": standards}
        finally:
            if should_close:
                db.close()

    def _mcp_validations(self, args: dict[str, Any]) -> dict[str, Any]:
        """List programmatic validations."""
        import json

        db, should_close = self._get_db()
        kb_name = args.get("kb_name")
        category_filter = args.get("category")

        try:
            query = "SELECT * FROM entry WHERE entry_type = 'programmatic_validation'"
            params: list = []
            if kb_name:
                query += " AND kb_name = ?"
                params.append(kb_name)

            rows = db._raw_conn.execute(query, params).fetchall()
            items = []
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
                items.append(
                    {
                        "id": row["id"],
                        "title": row["title"],
                        "category": category,
                        "check_command": meta.get("check_command", ""),
                        "pass_criteria": meta.get("pass_criteria", ""),
                        "kb_name": row["kb_name"],
                    }
                )

            return {"count": len(items), "validations": items}
        finally:
            if should_close:
                db.close()

    def _mcp_conventions(self, args: dict[str, Any]) -> dict[str, Any]:
        """List development conventions."""
        import json

        db, should_close = self._get_db()
        kb_name = args.get("kb_name")
        category_filter = args.get("category")

        try:
            query = "SELECT * FROM entry WHERE entry_type = 'development_convention'"
            params: list = []
            if kb_name:
                query += " AND kb_name = ?"
                params.append(kb_name)

            rows = db._raw_conn.execute(query, params).fetchall()
            items = []
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
                items.append(
                    {
                        "id": row["id"],
                        "title": row["title"],
                        "category": category,
                        "kb_name": row["kb_name"],
                    }
                )

            return {"count": len(items), "conventions": items}
        finally:
            if should_close:
                db.close()

    def _mcp_backlog(self, args: dict[str, Any]) -> dict[str, Any]:
        """List backlog items."""
        import json

        db, should_close = self._get_db()
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
            if should_close:
                db.close()

    def _mcp_milestones(self, args: dict[str, Any]) -> dict[str, Any]:
        """List milestones with completion stats."""
        import json

        db, should_close = self._get_db()
        kb_name = args.get("kb_name")
        status_filter = args.get("status")

        try:
            query = "SELECT * FROM entry WHERE entry_type = 'milestone'"
            params: list = []
            if kb_name:
                query += " AND kb_name = ?"
                params.append(kb_name)
            query += " ORDER BY created_at DESC"

            rows = db._raw_conn.execute(query, params).fetchall()
            milestones = []
            for row in rows:
                meta = {}
                if row["metadata"]:
                    try:
                        meta = json.loads(row["metadata"])
                    except (json.JSONDecodeError, TypeError):
                        pass
                status = meta.get("status", "open")
                if status_filter and status != status_filter:
                    continue

                # Get linked backlog items via outlinks
                linked = db.get_outlinks(row["id"], row["kb_name"])
                total = 0
                completed = 0
                for link in linked:
                    if link.get("entry_type") == "backlog_item":
                        total += 1
                        link_meta = {}
                        if link.get("metadata"):
                            try:
                                link_meta = json.loads(link["metadata"]) if isinstance(link["metadata"], str) else link.get("metadata", {})
                            except (json.JSONDecodeError, TypeError):
                                pass
                        if link_meta.get("status") in ("done", "completed"):
                            completed += 1

                pct = round(completed / total * 100) if total > 0 else 0
                milestones.append(
                    {
                        "id": row["id"],
                        "title": row["title"],
                        "status": status,
                        "total_items": total,
                        "completed_items": completed,
                        "completion_pct": pct,
                        "kb_name": row["kb_name"],
                    }
                )

            return {"count": len(milestones), "milestones": milestones}
        finally:
            if should_close:
                db.close()

    def _mcp_board(self, args: dict[str, Any]) -> dict[str, Any]:
        """View kanban board."""
        import json

        from .board import load_board_config

        db, should_close = self._get_db()
        kb_name = args.get("kb_name")

        try:
            # Load board config
            if self.ctx is not None and kb_name:
                from pyrite.config import load_config

                config = load_config()
                kb_conf = config.get_kb(kb_name)
                board_config = load_board_config(kb_conf.path) if kb_conf else load_board_config(Path("."))
            else:
                from pathlib import Path

                board_config = load_board_config(Path("."))

            # Query all backlog items
            query = "SELECT * FROM entry WHERE entry_type = 'backlog_item'"
            params: list = []
            if kb_name:
                query += " AND kb_name = ?"
                params.append(kb_name)

            rows = db._raw_conn.execute(query, params).fetchall()

            # Build status→lane mapping
            status_to_lane: dict[str, int] = {}
            for i, lane in enumerate(board_config["lanes"]):
                for s in lane["statuses"]:
                    status_to_lane[s] = i

            # Group items into lanes
            lane_items: dict[int, list] = {i: [] for i in range(len(board_config["lanes"]))}
            for row in rows:
                meta = {}
                if row["metadata"]:
                    try:
                        meta = json.loads(row["metadata"])
                    except (json.JSONDecodeError, TypeError):
                        pass
                status = meta.get("status", "proposed")
                lane_idx = status_to_lane.get(status)
                if lane_idx is not None:
                    lane_items[lane_idx].append(
                        {
                            "id": row["id"],
                            "title": row["title"],
                            "status": status,
                            "priority": meta.get("priority", "medium"),
                            "kind": meta.get("kind", ""),
                        }
                    )

            lanes = []
            for i, lane_def in enumerate(board_config["lanes"]):
                items = lane_items.get(i, [])
                wip_limit = lane_def.get("wip_limit")
                lane = {
                    "name": lane_def["name"],
                    "count": len(items),
                    "items": items,
                }
                if wip_limit is not None:
                    lane["wip_limit"] = wip_limit
                    lane["over_limit"] = len(items) > wip_limit
                lanes.append(lane)

            return {
                "lanes": lanes,
                "wip_policy": board_config.get("wip_policy", "warn"),
            }
        finally:
            if should_close:
                db.close()

    def _mcp_create_adr(self, args: dict[str, Any]) -> dict[str, Any]:
        """Create a new ADR with auto-numbering."""
        import json

        db, should_close = self._get_db()
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
            if should_close:
                db.close()

    def _mcp_review_queue(self, args: dict[str, Any]) -> dict[str, Any]:
        """View items in review status, sorted by wait time."""
        import json
        from pathlib import Path

        from .board import load_board_config

        db, should_close = self._get_db()
        kb_name = args.get("kb_name")

        try:
            query = "SELECT * FROM entry WHERE entry_type = 'backlog_item'"
            params: list = []
            if kb_name:
                query += " AND kb_name = ?"
                params.append(kb_name)
            query += " ORDER BY updated_at ASC"

            rows = db._raw_conn.execute(query, params).fetchall()
            items = []
            for row in rows:
                meta = {}
                if row["metadata"]:
                    try:
                        meta = json.loads(row["metadata"])
                    except (json.JSONDecodeError, TypeError):
                        pass
                status = row["status"] or meta.get("status", "proposed")
                if status != "review":
                    continue
                items.append(
                    {
                        "id": row["id"],
                        "title": row["title"],
                        "kind": meta.get("kind", ""),
                        "priority": row["priority"] or meta.get("priority", "medium"),
                        "assignee": row["assignee"] or meta.get("assignee", ""),
                        "updated_at": row["updated_at"] or "",
                    }
                )

            # Load board config for review lane WIP limit
            wip_limit = None
            try:
                if self.ctx is not None and kb_name:
                    from pyrite.config import load_config

                    config = load_config()
                    kb_conf = config.get_kb(kb_name)
                    board_config = load_board_config(kb_conf.path) if kb_conf else load_board_config(Path("."))
                else:
                    board_config = load_board_config(Path("."))

                for lane in board_config["lanes"]:
                    if "review" in lane.get("statuses", []):
                        wip_limit = lane.get("wip_limit")
                        break
            except Exception:
                pass

            result: dict[str, Any] = {
                "items": items,
                "count": len(items),
            }
            if wip_limit is not None:
                result["wip_limit"] = wip_limit
                result["over_limit"] = len(items) > wip_limit

            return result
        finally:
            if should_close:
                db.close()

    _RESOLVED_STATUSES = frozenset({"done", "completed", "retired", "wont_do"})

    def _get_dependency_status(self, db, item_id: str, kb_name: str) -> dict[str, Any]:
        """Return dependency info for a backlog item.

        Returns dict with blocked_by, blocks, and is_blocked.
        """
        import json

        blocked_by: list[dict[str, Any]] = []
        blocks: list[dict[str, Any]] = []

        # Outlinks with relation "blocked_by" → this item is blocked by those targets
        for link in db.get_outlinks(item_id, kb_name):
            if link.get("relation") != "blocked_by":
                continue
            dep_entry = db.get_entry(link["id"], link.get("kb_name", kb_name))
            if dep_entry:
                meta = {}
                if dep_entry.get("metadata"):
                    try:
                        meta = json.loads(dep_entry["metadata"]) if isinstance(dep_entry["metadata"], str) else dep_entry["metadata"]
                    except (json.JSONDecodeError, TypeError):
                        pass
                dep_status = dep_entry.get("status") or meta.get("status", "proposed")
            else:
                dep_status = "unknown"
            blocked_by.append({
                "id": link["id"],
                "title": link.get("title", ""),
                "status": dep_status,
                "resolved": dep_status in self._RESOLVED_STATUSES,
            })

        # Backlinks with relation "blocked_by" → the source item is blocked by *this* item,
        # meaning this item blocks that source.
        for link in db.get_backlinks(item_id, kb_name):
            if link.get("relation") != "blocked_by":
                continue
            dep_entry = db.get_entry(link["id"], link.get("kb_name", kb_name))
            if dep_entry:
                meta = {}
                if dep_entry.get("metadata"):
                    try:
                        meta = json.loads(dep_entry["metadata"]) if isinstance(dep_entry["metadata"], str) else dep_entry["metadata"]
                    except (json.JSONDecodeError, TypeError):
                        pass
                dep_status = dep_entry.get("status") or meta.get("status", "proposed")
            else:
                dep_status = "unknown"
            blocks.append({
                "id": link["id"],
                "title": link.get("title", ""),
                "status": dep_status,
            })

        return {
            "blocked_by": blocked_by,
            "blocks": blocks,
            "is_blocked": any(not dep["resolved"] for dep in blocked_by),
        }

    def _mcp_context_for_item(self, args: dict[str, Any]) -> dict[str, Any]:
        """Assemble full context bundle for a backlog item."""
        import json

        db, should_close = self._get_db()
        item_id = args["item_id"]
        kb_name = args["kb_name"]

        try:
            # Get the item itself
            entry = db.get_entry(item_id, kb_name)
            if not entry:
                return {"error": f"Entry '{item_id}' not found in KB '{kb_name}'"}

            meta = {}
            if entry.get("metadata"):
                try:
                    meta = json.loads(entry["metadata"]) if isinstance(entry["metadata"], str) else entry.get("metadata", {})
                except (json.JSONDecodeError, TypeError):
                    pass

            item_info = {
                "id": entry["id"],
                "title": entry["title"],
                "status": entry.get("status") or meta.get("status", "proposed"),
                "kind": meta.get("kind", ""),
                "priority": entry.get("priority") or meta.get("priority", "medium"),
                "body": entry.get("body", ""),
            }

            # Get linked entries (both directions)
            outlinks = db.get_outlinks(item_id, kb_name)
            backlinks = db.get_backlinks(item_id, kb_name)

            # Build dependency info from blocks/blocked_by links
            dep_status = self._get_dependency_status(db, item_id, kb_name)
            dep_link_ids = {d["id"] for d in dep_status["blocked_by"]} | {d["id"] for d in dep_status["blocks"]}

            # Categorize by entry_type
            buckets: dict[str, list] = {
                "adrs": [],
                "components": [],
                "validations": [],
                "conventions": [],
                "milestones": [],
                "related": [],
            }
            type_to_bucket = {
                "adr": "adrs",
                "component": "components",
                "programmatic_validation": "validations",
                "development_convention": "conventions",
                "milestone": "milestones",
            }

            for link in outlinks + backlinks:
                # Skip dependency links — they go in the dependencies bucket
                if link.get("id", "") in dep_link_ids:
                    continue
                entry_type = link.get("entry_type", "")
                bucket = type_to_bucket.get(entry_type, "related")
                body = link.get("body", "") or ""
                buckets[bucket].append(
                    {
                        "id": link.get("id", ""),
                        "title": link.get("title", ""),
                        "entry_type": entry_type,
                        "relation": link.get("relation", ""),
                        "body_preview": body[:200] if body else "",
                    }
                )

            dependencies = {
                "blocked_by": dep_status["blocked_by"],
                "blocks": dep_status["blocks"],
                "is_blocked": dep_status["is_blocked"],
            }

            return {"item": item_info, "dependencies": dependencies, **buckets}
        finally:
            if should_close:
                db.close()

    def _mcp_pull_next(self, args: dict[str, Any]) -> dict[str, Any]:
        """Recommend next work item based on priority and WIP limits."""
        import json
        from pathlib import Path

        from .board import load_board_config

        db, should_close = self._get_db()
        kb_name = args.get("kb_name")

        try:
            # Load board config for WIP limits
            try:
                if self.ctx is not None and kb_name:
                    from pyrite.config import load_config

                    config = load_config()
                    kb_conf = config.get_kb(kb_name)
                    board_config = load_board_config(kb_conf.path) if kb_conf else load_board_config(Path("."))
                else:
                    board_config = load_board_config(Path("."))
            except Exception:
                board_config = {"lanes": [], "wip_policy": "warn"}

            # Count in_progress items and find WIP limit
            ip_query = "SELECT COUNT(*) as cnt FROM entry WHERE entry_type = 'backlog_item'"
            ip_params: list = []
            if kb_name:
                ip_query += " AND kb_name = ?"
                ip_params.append(kb_name)
            ip_query += " AND status = 'in_progress'"
            ip_count = db._raw_conn.execute(ip_query, ip_params).fetchone()["cnt"]

            wip_limit = None
            wip_policy = board_config.get("wip_policy", "warn")
            for lane in board_config["lanes"]:
                if "in_progress" in lane.get("statuses", []):
                    wip_limit = lane.get("wip_limit")
                    break

            wip_status = {
                "current": ip_count,
                "limit": wip_limit,
                "policy": wip_policy,
            }

            # Check if over WIP limit with enforce policy
            if wip_limit is not None and ip_count >= wip_limit and wip_policy == "enforce":
                return {
                    "recommendation": None,
                    "reason": "WIP limit reached",
                    "wip_status": wip_status,
                }

            # Query accepted items, rank by priority then created_at
            query = "SELECT * FROM entry WHERE entry_type = 'backlog_item'"
            params: list = []
            if kb_name:
                query += " AND kb_name = ?"
                params.append(kb_name)
            query += " ORDER BY created_at ASC"

            rows = db._raw_conn.execute(query, params).fetchall()

            priority_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            candidates = []
            for row in rows:
                meta = {}
                if row["metadata"]:
                    try:
                        meta = json.loads(row["metadata"])
                    except (json.JSONDecodeError, TypeError):
                        pass
                status = row["status"] or meta.get("status", "proposed")
                if status != "accepted":
                    continue
                priority = row["priority"] or meta.get("priority", "medium")
                candidates.append(
                    {
                        "id": row["id"],
                        "title": row["title"],
                        "kind": meta.get("kind", ""),
                        "priority": priority,
                        "effort": meta.get("effort", ""),
                        "_rank": priority_rank.get(priority, 2),
                        "_created": row["created_at"] or "",
                    }
                )

            # Sort by priority rank (ascending), then created_at (ascending)
            candidates.sort(key=lambda c: (c["_rank"], c["_created"]))

            if not candidates:
                return {
                    "recommendation": None,
                    "reason": "No accepted items available",
                    "wip_status": wip_status,
                }

            # Filter out blocked candidates
            blocked_items = []
            top = None
            for candidate in candidates:
                dep = self._get_dependency_status(db, candidate["id"], kb_name or "")
                if dep["is_blocked"]:
                    blocked_items.append({
                        "id": candidate["id"],
                        "title": candidate["title"],
                        "blocked_by": [d["id"] for d in dep["blocked_by"] if not d["resolved"]],
                    })
                elif top is None:
                    top = candidate

            if top is None:
                return {
                    "recommendation": None,
                    "reason": "All accepted items are blocked by dependencies",
                    "blocked_items": blocked_items,
                    "wip_status": wip_status,
                }

            # Get context preview counts
            outlinks = db.get_outlinks(top["id"], kb_name or "")
            adr_count = sum(1 for l in outlinks if l.get("entry_type") == "adr")
            component_count = sum(1 for l in outlinks if l.get("entry_type") == "component")
            validation_count = sum(1 for l in outlinks if l.get("entry_type") == "programmatic_validation")

            result = {
                "recommendation": {
                    "id": top["id"],
                    "title": top["title"],
                    "kind": top["kind"],
                    "priority": top["priority"],
                    "effort": top["effort"],
                },
                "context_preview": {
                    "adr_count": adr_count,
                    "component_count": component_count,
                    "validation_count": validation_count,
                },
                "wip_status": wip_status,
            }
            if blocked_items:
                result["blocked_items"] = blocked_items
            return result
        finally:
            if should_close:
                db.close()

    def _mcp_claim(self, args: dict[str, Any]) -> dict[str, Any]:
        """Claim a backlog item: transition to in_progress and set assignee."""
        import json

        from .workflows import BACKLOG_WORKFLOW, can_transition, get_allowed_transitions

        db, should_close = self._get_db()
        item_id = args["item_id"]
        kb_name = args["kb_name"]
        assignee = args["assignee"]

        try:
            # Get current entry
            query = "SELECT * FROM entry WHERE id = ? AND kb_name = ? AND entry_type = 'backlog_item'"
            row = db._raw_conn.execute(query, (item_id, kb_name)).fetchone()
            if not row:
                return {"claimed": False, "error": f"Backlog item '{item_id}' not found in KB '{kb_name}'"}

            meta = {}
            if row["metadata"]:
                try:
                    meta = json.loads(row["metadata"])
                except (json.JSONDecodeError, TypeError):
                    pass

            current_status = row["status"] or meta.get("status", "proposed")

            # Check dependencies before allowing claim
            dep_status = self._get_dependency_status(db, item_id, kb_name)
            if dep_status["is_blocked"]:
                unresolved = [d for d in dep_status["blocked_by"] if not d["resolved"]]
                return {
                    "claimed": False,
                    "error": "Item has unresolved dependencies",
                    "unresolved_dependencies": [
                        {"id": d["id"], "title": d["title"], "status": d["status"]}
                        for d in unresolved
                    ],
                }

            # Validate transition
            if not can_transition(BACKLOG_WORKFLOW, current_status, "in_progress", "write"):
                allowed = get_allowed_transitions(BACKLOG_WORKFLOW, current_status, "write")
                return {
                    "claimed": False,
                    "error": f"Cannot transition from '{current_status}' to 'in_progress'",
                    "current_status": current_status,
                    "allowed_transitions": [t["to"] for t in allowed],
                }

            # Use KBService CAS pattern
            from pyrite.config import load_config
            from pyrite.services.kb_service import KBService

            config = load_config()
            svc = KBService(config, db)
            result = svc.claim_entry(
                item_id, kb_name, assignee,
                from_status=current_status, to_status="in_progress",
            )
            return result
        finally:
            if should_close:
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
