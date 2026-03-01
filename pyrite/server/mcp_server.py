"""
MCP (Model Context Protocol) Server for pyrite

Three-tier MCP server supporting read, write, and admin access levels.
Each tier is a separate server instance with appropriate tools.

Tiers:
- read:  Search, browse, retrieve entries. Safe for any agent.
- write: Read + create/update/delete entries. For trusted agents/users.
- admin: Write + KB management, index rebuild, repo sync, config.
"""

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

from pydantic import AnyUrl

from ..config import PyriteConfig, load_config
from ..exceptions import ConfigError, PyriteError
from ..schema import generate_entry_id
from ..services.kb_service import KBService
from ..storage.database import PyriteDB
from ..storage.index import IndexManager


class PyriteMCPServer:
    """
    Three-tier MCP Server for pyrite.

    Provides tool-based access to knowledge bases for AI agents.
    Tier controls which tools are available.
    """

    VALID_TIERS = ("read", "write", "admin")

    def __init__(self, config: PyriteConfig | None = None, tier: str = "read"):
        if tier not in self.VALID_TIERS:
            raise ConfigError(f"Invalid tier '{tier}'. Must be one of {self.VALID_TIERS}")

        self.config = config or load_config()
        self.tier = tier
        self.db = PyriteDB(self.config.settings.index_path)
        self.index_mgr = IndexManager(self.db, self.config)
        self.svc = KBService(self.config, self.db)

        # Build tool registry based on tier
        self.tools = {}
        self._build_read_tools()
        if tier in ("write", "admin"):
            self._build_write_tools()
        if tier == "admin":
            self._build_admin_tools()

        # Register plugin tools for this tier
        self._register_plugin_tools()

        # Build prompt and resource registries (available at all tiers)
        self.prompts = self._build_prompts()
        self.resources = self._build_resources()
        self.resource_templates = self._build_resource_templates()

    # =========================================================================
    # Tool registration by tier
    # =========================================================================

    def _build_read_tools(self):
        """Register read-only tools (available in all tiers)."""
        from .tool_schemas import READ_TOOLS

        for name, schema in READ_TOOLS.items():
            self.tools[name] = {**schema, "handler": getattr(self, f"_{name}")}

    def _build_write_tools(self):
        """Register write tools (available in write and admin tiers)."""
        from .tool_schemas import WRITE_TOOLS

        for name, schema in WRITE_TOOLS.items():
            self.tools[name] = {**schema, "handler": getattr(self, f"_{name}")}

    def _build_admin_tools(self):
        """Register admin tools (available only in admin tier)."""
        from .tool_schemas import ADMIN_TOOLS

        for name, schema in ADMIN_TOOLS.items():
            self.tools[name] = {**schema, "handler": getattr(self, f"_{name}")}

    def _register_plugin_tools(self):
        """Register MCP tools from plugins for the current tier."""
        try:
            from ..plugins import PluginContext, get_registry

            registry = get_registry()

            # Inject shared context so plugin handlers don't need to self-bootstrap
            ctx = PluginContext(config=self.config, db=self.db)
            registry.set_context(ctx)

            plugin_tools = registry.get_all_mcp_tools(self.tier)
            self.tools.update(plugin_tools)
        except Exception:
            logger.warning("Plugin MCP tool loading failed", exc_info=True)

    # =========================================================================
    # Lazy service properties
    # =========================================================================

    @property
    def qa_svc(self):
        if not hasattr(self, "_qa_svc_cache"):
            from ..services.qa_service import QAService

            self._qa_svc_cache = QAService(self.config, self.db)
        return self._qa_svc_cache

    @property
    def search_svc(self):
        if not hasattr(self, "_search_svc_cache"):
            from ..services.search_service import SearchService

            self._search_svc_cache = SearchService(self.db, settings=self.config.settings)
        return self._search_svc_cache

    # =========================================================================
    # Read handlers
    # =========================================================================

    def _kb_list(self, args: dict[str, Any]) -> dict[str, Any]:
        """List all knowledge bases."""
        kbs_data = self.svc.list_kbs()
        kbs = [
            {
                "name": kb["name"],
                "type": kb["type"],
                "path": kb["path"],
                "description": kb.get("description", ""),
                "entry_count": kb["entries"],
                "read_only": kb.get("read_only", False),
            }
            for kb in kbs_data
        ]
        return {"knowledge_bases": kbs}

    def _kb_search(self, args: dict[str, Any]) -> dict[str, Any]:
        """Full-text search with optional semantic/hybrid mode."""
        query = args.get("query", "")
        limit = args.get("limit", 20)
        results = self.search_svc.search(
            query=query,
            kb_name=args.get("kb_name"),
            entry_type=args.get("entry_type"),
            tags=args.get("tags"),
            date_from=args.get("date_from"),
            date_to=args.get("date_to"),
            limit=limit,
            offset=args.get("offset", 0),
            mode=args.get("mode", "keyword"),
            expand=args.get("expand", False),
        )

        return {
            "query": query,
            "count": len(results),
            "has_more": len(results) == limit,
            "results": results,
        }

    def _kb_get(self, args: dict[str, Any]) -> dict[str, Any]:
        """Get entry by ID."""
        entry_id = args.get("entry_id")
        kb_name = args.get("kb_name")

        result = self.svc.get_entry(entry_id, kb_name=kb_name)

        if not result:
            return {"error": f"Entry '{entry_id}' not found"}

        return {"entry": result}

    def _kb_timeline(self, args: dict[str, Any]) -> dict[str, Any]:
        """Get timeline events."""
        limit = args.get("limit", 50)
        results = self.svc.get_timeline(
            date_from=args.get("date_from"),
            date_to=args.get("date_to"),
            min_importance=args.get("min_importance", 1),
            limit=limit,
            offset=args.get("offset", 0),
        )
        return {
            "count": len(results),
            "has_more": len(results) == limit,
            "events": results,
        }

    def _kb_backlinks(self, args: dict[str, Any]) -> dict[str, Any]:
        """Get backlinks to an entry."""
        entry_id = args.get("entry_id")
        kb_name = args.get("kb_name")
        limit = args.get("limit", 100)
        backlinks = self.svc.get_backlinks(
            entry_id, kb_name, limit=limit, offset=args.get("offset", 0)
        )
        return {
            "entry_id": entry_id,
            "backlink_count": len(backlinks),
            "has_more": len(backlinks) == limit,
            "backlinks": backlinks,
        }

    def _kb_tags(self, args: dict[str, Any]) -> dict[str, Any]:
        """Get all tags with counts."""
        kb_name = args.get("kb_name")
        prefix = args.get("prefix") or None

        if args.get("tree"):
            tree = self.svc.get_tag_tree(kb_name=kb_name)
            return {"tree": tree}

        limit = args.get("limit", 100)
        tag_dicts = self.svc.get_tags(
            kb_name=kb_name,
            limit=limit,
            offset=args.get("offset", 0),
            prefix=prefix,
        )
        tags = [{"tag": t["name"], "count": t["count"]} for t in tag_dicts]
        return {
            "tag_count": len(tags),
            "has_more": len(tags) == limit,
            "tags": tags,
        }

    def _kb_stats(self, args: dict[str, Any]) -> dict[str, Any]:
        """Get index statistics."""
        stats = self.index_mgr.get_index_stats()
        return stats

    def _kb_schema(self, args: dict[str, Any]) -> dict[str, Any]:
        """Get KB schema for agent discoverability."""
        kb_name = args.get("kb_name")
        kb_config = self.config.get_kb(kb_name)
        if not kb_config:
            return {"error": f"KB '{kb_name}' not found"}

        schema = kb_config.kb_schema
        return schema.to_agent_schema()

    def _kb_qa_validate(self, args: dict[str, Any]) -> dict[str, Any]:
        """Validate KB structural integrity."""
        qa = self.qa_svc

        entry_id = args.get("entry_id")
        kb_name = args.get("kb_name")
        severity_filter = args.get("severity", "warning")
        limit = args.get("limit", 50)

        if entry_id and kb_name:
            result = qa.validate_entry(entry_id, kb_name)
            issues = result["issues"]
        elif kb_name:
            result = qa.validate_kb(kb_name)
            issues = result["issues"]
        else:
            result = qa.validate_all()
            issues = []
            for kb in result["kbs"]:
                issues.extend(kb["issues"])

        # Filter by severity
        severity_order = {"error": 0, "warning": 1, "info": 2}
        min_level = severity_order.get(severity_filter, 1)
        issues = [
            i for i in issues if severity_order.get(i.get("severity", "info"), 2) <= min_level
        ]

        # Apply limit
        truncated = len(issues) > limit
        issues = issues[:limit]

        return {
            "issues": issues,
            "count": len(issues),
            "truncated": truncated,
        }

    def _kb_qa_status(self, args: dict[str, Any]) -> dict[str, Any]:
        """Get QA status dashboard with coverage stats."""
        qa = self.qa_svc
        status = qa.get_status(kb_name=args.get("kb_name"))

        # Add coverage stats if a specific KB is requested
        kb_name = args.get("kb_name")
        if kb_name:
            status["coverage"] = qa.get_coverage(kb_name)

        return status

    def _kb_qa_assess(self, args: dict[str, Any]) -> dict[str, Any]:
        """Assess entry or KB quality."""
        qa = self.qa_svc
        kb_name = args["kb_name"]
        entry_id = args.get("entry_id")
        tier = args.get("tier", 1)
        create_tasks = args.get("create_tasks", False)

        if entry_id:
            return qa.assess_entry(entry_id, kb_name, tier=tier, create_task_on_fail=create_tasks)
        else:
            max_age = args.get("max_age_hours", 24)
            return qa.assess_kb(kb_name, tier=tier, max_age_hours=max_age, create_task_on_fail=create_tasks)

    # =========================================================================
    # Post-save QA validation
    # =========================================================================

    def _maybe_validate(self, entry_id: str, kb_name: str, args: dict) -> list[dict] | None:
        """Run post-save QA validation if requested or KB has qa_on_write."""
        should_validate = args.get("validate", False)
        if not should_validate:
            kb_config = self.config.get_kb(kb_name)
            if kb_config:
                schema = kb_config.kb_schema
                should_validate = schema.validation.get("qa_on_write", False)
        if should_validate:
            result = self.qa_svc.validate_entry(entry_id, kb_name)
            if result["issues"]:
                return result["issues"]
        return None

    # =========================================================================
    # Write handlers
    # =========================================================================

    def _kb_create(self, args: dict[str, Any]) -> dict[str, Any]:
        """Create a new entry."""
        kb_name = args.get("kb_name")
        entry_type = args.get("entry_type", "note")
        title = args.get("title")
        body = args.get("body", "")

        kb_config = self.config.get_kb(kb_name)
        if not kb_config:
            return {"error": f"KB '{kb_name}' not found"}
        if kb_config.read_only:
            return {"error": f"KB '{kb_name}' is read-only"}

        # Validate against schema
        schema = kb_config.kb_schema
        validation = schema.validate_entry(
            entry_type, args, context={"kb_type": kb_config.kb_type}
        )
        warnings = validation.get("warnings", [])

        if entry_type == "event" and not args.get("date"):
            return {"error": "Date is required for events"}

        entry_id = generate_entry_id(title)

        # Filter out keys already passed as explicit arguments
        extra = {
            k: v
            for k, v in args.items()
            if k not in ("kb_name", "entry_type", "title", "body", "validate")
        }

        try:
            entry = self.svc.create_entry(kb_name, entry_id, title, entry_type, body, **extra)
        except PyriteError as e:
            return {"error": str(e)}

        result = {"created": True, "entry_id": entry.id, "file_path": ""}
        if warnings:
            result["warnings"] = warnings
        qa_issues = self._maybe_validate(entry.id, kb_name, args)
        if qa_issues:
            result["qa_issues"] = qa_issues
        return result

    def _kb_bulk_create(self, args: dict[str, Any]) -> dict[str, Any]:
        """Batch-create multiple entries."""
        kb_name = args.get("kb_name")
        entries = args.get("entries", [])

        if not entries:
            return {"error": "entries array is required and must not be empty"}
        if len(entries) > 50:
            return {"error": "Maximum 50 entries per call"}

        # Pre-validate each entry against schema
        kb_config = self.config.get_kb(kb_name)
        schema = None
        if kb_config:
            schema = kb_config.kb_schema

        try:
            results = self.svc.bulk_create_entries(kb_name, entries)
        except PyriteError as e:
            return {"error": str(e)}

        # Attach per-entry validation warnings
        if schema:
            for i, spec in enumerate(entries):
                if i < len(results) and results[i].get("created"):
                    entry_type = spec.get("entry_type", "note")
                    validation = schema.validate_entry(
                        entry_type, spec, context={"kb_type": kb_config.kb_type}
                    )
                    entry_warnings = validation.get("warnings", [])
                    if entry_warnings:
                        results[i]["warnings"] = entry_warnings

        created = sum(1 for r in results if r.get("created"))
        failed = len(results) - created
        return {
            "total": len(results),
            "created": created,
            "failed": failed,
            "results": results,
        }

    def _kb_update(self, args: dict[str, Any]) -> dict[str, Any]:
        """Update an existing entry."""
        entry_id = args.get("entry_id")
        kb_name = args.get("kb_name")

        updates = {}
        for key in ("title", "body", "importance", "tags", "participants", "metadata"):
            if key in args:
                updates[key] = args[key]

        # Schema validation on the updated fields
        warnings: list[dict[str, Any]] = []
        kb_config = self.config.get_kb(kb_name)
        if kb_config:
            schema = kb_config.kb_schema
            # Get the current entry to determine its type
            existing = self.svc.get_entry(entry_id, kb_name)
            if existing:
                entry_type = existing.get("entry_type", "note")
                # Merge existing fields with updates for validation
                validation = schema.validate_entry(
                    entry_type, {**existing, **updates},
                    context={"kb_type": kb_config.kb_type},
                )
                warnings = validation.get("warnings", [])

        try:
            entry = self.svc.update_entry(entry_id, kb_name, **updates)
        except PyriteError as e:
            return {"error": str(e)}

        result: dict[str, Any] = {"updated": True, "entry_id": entry.id, "file_path": ""}
        if warnings:
            result["warnings"] = warnings
        qa_issues = self._maybe_validate(entry.id, kb_name, args)
        if qa_issues:
            result["qa_issues"] = qa_issues
        return result

    def _kb_delete(self, args: dict[str, Any]) -> dict[str, Any]:
        """Delete an entry."""
        entry_id = args.get("entry_id")
        kb_name = args.get("kb_name")

        try:
            deleted = self.svc.delete_entry(entry_id, kb_name)
        except PyriteError as e:
            return {"error": str(e)}

        if not deleted:
            return {"error": f"Entry '{entry_id}' not found in {kb_name}"}

        return {"deleted": True, "entry_id": entry_id}

    def _kb_link(self, args: dict[str, Any]) -> dict[str, Any]:
        """Create a link between two entries."""
        source_id = args.get("source_id")
        source_kb = args.get("source_kb")
        target_id = args.get("target_id")
        relation = args.get("relation", "related_to")
        target_kb = args.get("target_kb")
        note = args.get("note", "")

        try:
            self.svc.add_link(
                source_id=source_id,
                source_kb=source_kb,
                target_id=target_id,
                relation=relation,
                target_kb=target_kb,
                note=note,
            )
        except PyriteError as e:
            return {"error": str(e)}

        return {
            "linked": True,
            "source_id": source_id,
            "target_id": target_id,
            "relation": relation,
        }

    # =========================================================================
    # Admin handlers
    # =========================================================================

    def _kb_index_sync(self, args: dict[str, Any]) -> dict[str, Any]:
        """Sync index with file changes."""
        kb_name = args.get("kb_name")
        results = self.index_mgr.sync_incremental(kb_name)
        return {
            "synced": True,
            "added": results["added"],
            "updated": results["updated"],
            "removed": results["removed"],
        }

    def _kb_manage(self, args: dict[str, Any]) -> dict[str, Any]:
        """Manage knowledge bases."""
        action = args.get("action")

        if action == "discover":
            discovered = self.config.auto_discover_kbs()
            return {"discovered": len(discovered), "kbs": [str(p) for p in discovered]}
        elif action == "validate":
            kb_name = args.get("kb_name")
            if not kb_name:
                return {"error": "kb_name required for validate"}
            kb_config = self.config.get_kb(kb_name)
            if not kb_config:
                return {"error": f"KB '{kb_name}' not found"}
            schema = kb_config.kb_schema
            return {"valid": True, "types": list(schema.types.keys())}

        elif action in ("show_schema", "add_type", "remove_type", "set_schema"):
            return self._kb_manage_schema(action, args)

        return {"error": f"Unknown action: {action}"}

    def _kb_manage_schema(self, action: str, args: dict[str, Any]) -> dict[str, Any]:
        """Handle schema management actions for _kb_manage."""
        from pyrite.services.schema_service import SchemaService

        kb_name = args.get("kb_name")
        svc = SchemaService(self.config)

        try:
            if action == "show_schema":
                if not kb_name:
                    return {"error": "kb_name required for show_schema"}
                return svc.show_schema(kb_name)

            elif action == "add_type":
                type_name = args.get("type_name")
                type_def = args.get("type_def", {})
                if not kb_name or not type_name:
                    return {"error": "kb_name and type_name required for add_type"}
                return svc.add_type(kb_name, type_name, type_def)

            elif action == "remove_type":
                type_name = args.get("type_name")
                if not kb_name or not type_name:
                    return {"error": "kb_name and type_name required for remove_type"}
                return svc.remove_type(kb_name, type_name)

            elif action == "set_schema":
                schema = args.get("schema", {})
                if not kb_name:
                    return {"error": "kb_name required for set_schema"}
                return svc.set_schema(kb_name, schema)

        except ValueError as e:
            return {"error": str(e)}

        return {"error": f"Unknown schema action: {action}"}

    def _kb_commit(self, args: dict[str, Any]) -> dict[str, Any]:
        """Commit changes in a KB's git repository."""
        kb_name = args.get("kb")
        message = args.get("message")
        paths = args.get("paths")
        sign_off = args.get("sign_off", False)

        if not kb_name or not message:
            return {"error": "Both 'kb' and 'message' are required"}

        try:
            return self.svc.commit_kb(
                kb_name, message=message, paths=paths, sign_off=sign_off
            )
        except PyriteError as e:
            return {"error": str(e)}

    def _kb_push(self, args: dict[str, Any]) -> dict[str, Any]:
        """Push KB commits to a remote repository."""
        kb_name = args.get("kb")
        remote = args.get("remote", "origin")
        branch = args.get("branch")

        if not kb_name:
            return {"error": "'kb' is required"}

        try:
            return self.svc.push_kb(kb_name, remote=remote, branch=branch)
        except PyriteError as e:
            return {"error": str(e)}

    # =========================================================================
    # Prompts
    # =========================================================================

    def _build_prompts(self) -> dict[str, dict[str, Any]]:
        """Build prompt definitions available to MCP clients."""
        return {
            "research_topic": {
                "name": "research_topic",
                "description": "Research a topic across all knowledge bases, summarize findings, and identify gaps",
                "arguments": [
                    {"name": "topic", "description": "Topic to research", "required": True}
                ],
            },
            "summarize_entry": {
                "name": "summarize_entry",
                "description": "Get an entry and generate a concise summary",
                "arguments": [
                    {
                        "name": "entry_id",
                        "description": "Entry ID to summarize",
                        "required": True,
                    },
                    {
                        "name": "kb_name",
                        "description": "KB name (optional)",
                        "required": False,
                    },
                ],
            },
            "find_connections": {
                "name": "find_connections",
                "description": "Analyze connections between two entries",
                "arguments": [
                    {"name": "entry_a", "description": "First entry ID", "required": True},
                    {"name": "entry_b", "description": "Second entry ID", "required": True},
                ],
            },
            "daily_briefing": {
                "name": "daily_briefing",
                "description": "Generate a briefing from recent entries and timeline events",
                "arguments": [
                    {
                        "name": "days",
                        "description": "Number of days to look back (default 7)",
                        "required": False,
                    }
                ],
            },
        }

    def _get_prompt(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Dispatch to the appropriate prompt handler."""
        handlers = {
            "research_topic": self._prompt_research_topic,
            "summarize_entry": self._prompt_summarize_entry,
            "find_connections": self._prompt_find_connections,
            "daily_briefing": self._prompt_daily_briefing,
        }
        handler = handlers.get(name)
        if not handler:
            return {"error": f"Unknown prompt: {name}"}
        return handler(arguments)

    def _prompt_research_topic(self, args: dict[str, Any]) -> dict[str, Any]:
        """Generate research prompt for a topic."""
        topic = args.get("topic", "")
        return {
            "messages": [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": (
                            f"You are a research assistant with access to Pyrite knowledge bases. "
                            f"Research the topic: {topic}. Search across all KBs, summarize key "
                            f"findings, identify related entries, and note any gaps in coverage."
                        ),
                    },
                }
            ]
        }

    def _prompt_summarize_entry(self, args: dict[str, Any]) -> dict[str, Any]:
        """Fetch an entry and generate a summary prompt."""
        entry_id = args.get("entry_id", "")
        kb_name = args.get("kb_name")

        entry = self.svc.get_entry(entry_id, kb_name=kb_name)
        if not entry:
            return {
                "messages": [
                    {
                        "role": "user",
                        "content": {
                            "type": "text",
                            "text": f"Entry '{entry_id}' was not found. Please check the ID and try again.",
                        },
                    }
                ]
            }

        entry_text = json.dumps(entry, separators=(",", ":"), default=str)
        return {
            "messages": [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": (
                            f"Summarize the following entry concisely. Highlight the key facts, "
                            f"connections to other entries, and significance.\n\n{entry_text}"
                        ),
                    },
                }
            ]
        }

    def _prompt_find_connections(self, args: dict[str, Any]) -> dict[str, Any]:
        """Fetch two entries and generate a connections analysis prompt."""
        entry_a_id = args.get("entry_a", "")
        entry_b_id = args.get("entry_b", "")

        entry_a = self.svc.get_entry(entry_a_id)
        entry_b = self.svc.get_entry(entry_b_id)

        entry_a_text = (
            json.dumps(entry_a, separators=(",", ":"), default=str)
            if entry_a
            else f"Entry '{entry_a_id}' not found"
        )
        entry_b_text = (
            json.dumps(entry_b, separators=(",", ":"), default=str)
            if entry_b
            else f"Entry '{entry_b_id}' not found"
        )

        return {
            "messages": [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": (
                            f"Analyze the connections between these two entries. Identify shared "
                            f"themes, people, organizations, events, or other relationships.\n\n"
                            f"## Entry A\n{entry_a_text}\n\n## Entry B\n{entry_b_text}"
                        ),
                    },
                }
            ]
        }

    def _prompt_daily_briefing(self, args: dict[str, Any]) -> dict[str, Any]:
        """Generate a briefing prompt from recent timeline events."""
        from datetime import datetime, timedelta

        days = int(args.get("days", 7))
        date_to = datetime.now().strftime("%Y-%m-%d")
        date_from = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        events = self.svc.get_timeline(date_from=date_from, date_to=date_to)
        events = events[:50]  # Cap at 50 events

        if events:
            events_text = json.dumps(events, separators=(",", ":"), default=str)
        else:
            events_text = "No timeline events found in this period."

        return {
            "messages": [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": (
                            f"Generate a briefing based on the following timeline events from "
                            f"the last {days} days ({date_from} to {date_to}). Summarize key "
                            f"developments, highlight the most important items, and note any "
                            f"emerging patterns.\n\n{events_text}"
                        ),
                    },
                }
            ]
        }

    # =========================================================================
    # Resources
    # =========================================================================

    def _build_resources(self) -> list[dict[str, Any]]:
        """Build static resource list."""
        return [
            {
                "uri": "pyrite://kbs",
                "name": "Knowledge Bases",
                "description": "List all knowledge bases",
                "mimeType": "application/json",
            },
        ]

    def _build_resource_templates(self) -> list[dict[str, Any]]:
        """Build resource URI templates."""
        return [
            {
                "uriTemplate": "pyrite://kbs/{name}/entries",
                "name": "KB Entries",
                "description": "List entries in a knowledge base",
                "mimeType": "application/json",
            },
            {
                "uriTemplate": "pyrite://entries/{id}",
                "name": "Entry",
                "description": "Get a specific entry",
                "mimeType": "application/json",
            },
        ]

    def _read_resource(self, uri: str) -> dict[str, Any]:
        """Read a resource by URI and return contents."""
        if uri == "pyrite://kbs":
            kbs_data = self.svc.list_kbs()
            return {
                "contents": [
                    {
                        "uri": uri,
                        "mimeType": "application/json",
                        "text": json.dumps(kbs_data, separators=(",", ":"), default=str),
                    }
                ]
            }

        # pyrite://kbs/{name}/entries
        if uri.startswith("pyrite://kbs/") and uri.endswith("/entries"):
            kb_name = uri[len("pyrite://kbs/") : -len("/entries")]
            entries = self.db.list_entries(kb_name=kb_name, limit=200)
            return {
                "contents": [
                    {
                        "uri": uri,
                        "mimeType": "application/json",
                        "text": json.dumps(entries, separators=(",", ":"), default=str),
                    }
                ]
            }

        # pyrite://entries/{id}
        if uri.startswith("pyrite://entries/"):
            entry_id = uri[len("pyrite://entries/") :]
            entry = self.svc.get_entry(entry_id)
            if not entry:
                return {"error": f"Entry '{entry_id}' not found"}
            return {
                "contents": [
                    {
                        "uri": uri,
                        "mimeType": "application/json",
                        "text": json.dumps(entry, separators=(",", ":"), default=str),
                    }
                ]
            }

        return {"error": f"Unknown resource URI: {uri}"}

    # =========================================================================
    # MCP Protocol
    # =========================================================================

    def get_tools_list(self) -> list[dict[str, Any]]:
        """Return list of available tools in MCP format."""
        return [
            {"name": name, "description": meta["description"], "inputSchema": meta["inputSchema"]}
            for name, meta in self.tools.items()
        ]

    def _dispatch_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute a tool and return result."""
        if name not in self.tools:
            return {"error": f"Unknown tool: {name}"}

        try:
            handler = self.tools[name]["handler"]
            return handler(arguments)
        except Exception as e:
            return {"error": str(e)}

    def build_sdk_server(self):
        """Build an mcp.server.Server wired to this instance's business logic."""
        from mcp.server import Server
        from mcp.types import (
            GetPromptResult,
            Prompt,
            PromptArgument,
            PromptMessage,
            ReadResourceResult,
            Resource,
            ResourceTemplate,
            TextContent,
            TextResourceContents,
            Tool,
        )

        sdk = Server(f"pyrite-{self.tier}")

        mcp_server = self  # capture for closures

        @sdk.list_tools()
        async def _list_tools():
            return [
                Tool(
                    name=name,
                    description=meta["description"],
                    inputSchema=meta["inputSchema"],
                )
                for name, meta in mcp_server.tools.items()
            ]

        @sdk.call_tool()
        async def _call_tool(name: str, arguments: dict):
            result = mcp_server._dispatch_tool(name, arguments or {})
            return [TextContent(type="text", text=json.dumps(result, separators=(",", ":"), default=str))]

        @sdk.list_prompts()
        async def _list_prompts():
            return [
                Prompt(
                    name=p["name"],
                    description=p.get("description"),
                    arguments=[
                        PromptArgument(
                            name=a["name"],
                            description=a.get("description"),
                            required=a.get("required", False),
                        )
                        for a in p.get("arguments", [])
                    ],
                )
                for p in mcp_server.prompts.values()
            ]

        @sdk.get_prompt()
        async def _get_prompt(name: str, arguments: dict[str, str] | None):
            if name not in mcp_server.prompts:
                raise ValueError(f"Unknown prompt: {name}")
            result = mcp_server._get_prompt(name, arguments or {})
            if "error" in result:
                raise ValueError(result["error"])
            return GetPromptResult(
                messages=[
                    PromptMessage(
                        role=m["role"],
                        content=TextContent(type="text", text=m["content"]["text"]),
                    )
                    for m in result["messages"]
                ]
            )

        @sdk.list_resources()
        async def _list_resources():
            return [
                Resource(
                    uri=AnyUrl(r["uri"]),
                    name=r["name"],
                    description=r.get("description"),
                    mimeType=r.get("mimeType"),
                )
                for r in mcp_server.resources
            ]

        @sdk.list_resource_templates()
        async def _list_resource_templates():
            return [
                ResourceTemplate(
                    uriTemplate=t["uriTemplate"],
                    name=t["name"],
                    description=t.get("description"),
                    mimeType=t.get("mimeType"),
                )
                for t in mcp_server.resource_templates
            ]

        @sdk.read_resource()
        async def _read_resource(uri: AnyUrl):
            result = mcp_server._read_resource(str(uri))
            if "error" in result:
                raise ValueError(result["error"])
            return ReadResourceResult(
                contents=[
                    TextResourceContents(
                        uri=AnyUrl(c["uri"]),
                        mimeType=c.get("mimeType"),
                        text=c["text"],
                    )
                    for c in result["contents"]
                ]
            )

        return sdk

    def run_stdio(self):
        """Run the MCP server over stdio using the official MCP SDK."""
        import anyio
        from mcp.server.stdio import stdio_server

        sdk = self.build_sdk_server()

        async def _run():
            async with stdio_server() as (read_stream, write_stream):
                await sdk.run(read_stream, write_stream, sdk.create_initialization_options())

        anyio.run(_run)

    def close(self):
        """Clean up resources."""
        self.db.close()


def main():
    """Entry point for MCP server. Supports --tier flag."""
    import argparse

    parser = argparse.ArgumentParser(prog="pyrite-server", description="Pyrite MCP Server")
    parser.add_argument(
        "--tier",
        choices=["read", "write", "admin"],
        default="read",
        help="Access tier (default: read)",
    )
    args = parser.parse_args()

    server = PyriteMCPServer(tier=args.tier)
    try:
        server.run_stdio()
    finally:
        server.close()


if __name__ == "__main__":
    main()
