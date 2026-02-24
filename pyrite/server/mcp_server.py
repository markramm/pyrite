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
from typing import Any

from pydantic import AnyUrl

from ..config import PyriteConfig, load_config
from ..exceptions import ConfigError, PyriteError
from ..schema import KBSchema, generate_entry_id
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
        self.tools.update(
            {
                "kb_list": {
                    "description": "List all mounted knowledge bases with their types and entry counts",
                    "inputSchema": {"type": "object", "properties": {}, "required": []},
                    "handler": self._kb_list,
                },
                "kb_search": {
                    "description": "Full-text search across knowledge bases. Supports FTS5 query syntax (AND, OR, NOT, phrases in quotes). Returns entries with snippets ranked by relevance.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query (FTS5 syntax supported)",
                            },
                            "kb_name": {
                                "type": "string",
                                "description": "Limit search to specific KB (optional)",
                            },
                            "entry_type": {
                                "type": "string",
                                "description": "Filter by entry type: note, person, organization, event, document, topic, etc.",
                            },
                            "tags": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Filter by tags (entries must have ALL specified tags)",
                            },
                            "date_from": {
                                "type": "string",
                                "description": "Start date (YYYY-MM-DD)",
                            },
                            "date_to": {
                                "type": "string",
                                "description": "End date (YYYY-MM-DD)",
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum results to return (default 20)",
                            },
                            "mode": {
                                "type": "string",
                                "enum": ["keyword", "semantic", "hybrid"],
                                "description": "Search mode: keyword (FTS5), semantic (vector), or hybrid. Default: keyword",
                            },
                            "expand": {
                                "type": "boolean",
                                "description": "Use AI query expansion for additional search terms. Default: false",
                            },
                        },
                        "required": ["query"],
                    },
                    "handler": self._kb_search,
                },
                "kb_get": {
                    "description": "Get a specific entry by its ID. Returns full content including body, metadata, sources, and links.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "entry_id": {
                                "type": "string",
                                "description": "The entry ID (e.g., '2025-01-20--event-slug' or 'alice-smith')",
                            },
                            "kb_name": {
                                "type": "string",
                                "description": "KB name (optional - searches all KBs if not provided)",
                            },
                        },
                        "required": ["entry_id"],
                    },
                    "handler": self._kb_get,
                },
                "kb_timeline": {
                    "description": "Get timeline events within a date range, optionally filtered by importance.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "date_from": {
                                "type": "string",
                                "description": "Start date (YYYY-MM-DD)",
                            },
                            "date_to": {"type": "string", "description": "End date (YYYY-MM-DD)"},
                            "min_importance": {
                                "type": "integer",
                                "description": "Minimum importance score (1-10)",
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum results (default 50)",
                            },
                        },
                        "required": [],
                    },
                    "handler": self._kb_timeline,
                },
                "kb_backlinks": {
                    "description": "Get all entries that link TO a given entry (reverse link lookup).",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "entry_id": {
                                "type": "string",
                                "description": "Entry ID to find backlinks for",
                            },
                            "kb_name": {"type": "string", "description": "KB name"},
                        },
                        "required": ["entry_id", "kb_name"],
                    },
                    "handler": self._kb_backlinks,
                },
                "kb_tags": {
                    "description": "Get all tags with their usage counts, optionally filtered by KB. Supports hierarchical /-separated tags.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "kb_name": {
                                "type": "string",
                                "description": "Filter to specific KB (optional)",
                            },
                            "prefix": {
                                "type": "string",
                                "description": "Filter tags starting with prefix",
                            },
                            "tree": {
                                "type": "boolean",
                                "description": "Return hierarchical tree instead of flat list",
                            },
                        },
                        "required": [],
                    },
                    "handler": self._kb_tags,
                },
                "kb_stats": {
                    "description": "Get index statistics: entry counts, tag counts, link counts per KB.",
                    "inputSchema": {"type": "object", "properties": {}, "required": []},
                    "handler": self._kb_stats,
                },
                "kb_schema": {
                    "description": "Get the schema for a knowledge base. Returns available entry types, required/optional fields, validation rules, and relationship types. Essential for agents creating entries.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "kb_name": {
                                "type": "string",
                                "description": "KB name to get schema for",
                            },
                        },
                        "required": ["kb_name"],
                    },
                    "handler": self._kb_schema,
                },
            }
        )

    def _build_write_tools(self):
        """Register write tools (available in write and admin tiers)."""
        self.tools.update(
            {
                "kb_create": {
                    "description": "Create a new entry in a knowledge base. Use kb_schema first to discover valid types and fields.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "kb_name": {"type": "string", "description": "Target KB name"},
                            "entry_type": {
                                "type": "string",
                                "description": "Entry type: note, person, organization, event, document, topic, relationship, timeline, or custom type from kb.yaml",
                            },
                            "title": {"type": "string", "description": "Entry title"},
                            "body": {
                                "type": "string",
                                "description": "Entry body content (markdown)",
                            },
                            "date": {
                                "type": "string",
                                "description": "Date (YYYY-MM-DD) - required for events",
                            },
                            "importance": {
                                "type": "integer",
                                "description": "Importance score 1-10 (default 5)",
                            },
                            "tags": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Tags for categorization",
                            },
                            "participants": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Participants involved (for events)",
                            },
                            "role": {
                                "type": "string",
                                "description": "Role description (for person entries)",
                            },
                            "metadata": {
                                "type": "object",
                                "description": "Additional fields for custom types or extension fields",
                            },
                        },
                        "required": ["kb_name", "entry_type", "title"],
                    },
                    "handler": self._kb_create,
                },
                "kb_update": {
                    "description": "Update an existing entry. Only provided fields are updated.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "entry_id": {"type": "string", "description": "Entry ID to update"},
                            "kb_name": {"type": "string", "description": "KB name"},
                            "title": {"type": "string"},
                            "body": {"type": "string"},
                            "importance": {"type": "integer"},
                            "tags": {"type": "array", "items": {"type": "string"}},
                            "metadata": {
                                "type": "object",
                                "description": "Extension fields to update",
                            },
                        },
                        "required": ["entry_id", "kb_name"],
                    },
                    "handler": self._kb_update,
                },
                "kb_delete": {
                    "description": "Delete an entry from a knowledge base.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "entry_id": {"type": "string", "description": "Entry ID to delete"},
                            "kb_name": {"type": "string", "description": "KB name"},
                        },
                        "required": ["entry_id", "kb_name"],
                    },
                    "handler": self._kb_delete,
                },
            }
        )

    def _build_admin_tools(self):
        """Register admin tools (available only in admin tier)."""
        self.tools.update(
            {
                "kb_index_sync": {
                    "description": "Sync the search index with file changes. Use after editing files directly.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "kb_name": {
                                "type": "string",
                                "description": "Sync specific KB (optional - syncs all if not provided)",
                            }
                        },
                        "required": [],
                    },
                    "handler": self._kb_index_sync,
                },
                "kb_manage": {
                    "description": "Manage knowledge bases: add, remove, discover, validate.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "action": {
                                "type": "string",
                                "enum": ["discover", "validate"],
                                "description": "Management action",
                            },
                            "kb_name": {"type": "string", "description": "KB name (for validate)"},
                        },
                        "required": ["action"],
                    },
                    "handler": self._kb_manage,
                },
            }
        )

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
            pass  # Plugin loading shouldn't break the MCP server

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
        from ..services.search_service import SearchService

        query = args.get("query", "")
        search_svc = SearchService(self.db, settings=self.config.settings)
        results = search_svc.search(
            query=query,
            kb_name=args.get("kb_name"),
            entry_type=args.get("entry_type"),
            tags=args.get("tags"),
            date_from=args.get("date_from"),
            date_to=args.get("date_to"),
            limit=args.get("limit", 20),
            mode=args.get("mode", "keyword"),
            expand=args.get("expand", False),
        )

        return {"query": query, "count": len(results), "results": results}

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
        results = self.svc.get_timeline(
            date_from=args.get("date_from"),
            date_to=args.get("date_to"),
            min_importance=args.get("min_importance", 1),
        )
        results = results[: args.get("limit", 50)]
        return {"count": len(results), "events": results}

    def _kb_backlinks(self, args: dict[str, Any]) -> dict[str, Any]:
        """Get backlinks to an entry."""
        entry_id = args.get("entry_id")
        kb_name = args.get("kb_name")
        backlinks = self.svc.get_backlinks(entry_id, kb_name)
        return {"entry_id": entry_id, "backlink_count": len(backlinks), "backlinks": backlinks}

    def _kb_tags(self, args: dict[str, Any]) -> dict[str, Any]:
        """Get all tags with counts."""
        kb_name = args.get("kb_name")
        prefix = args.get("prefix", "")

        if args.get("tree"):
            tree = self.svc.get_tag_tree(kb_name=kb_name)
            return {"tree": tree}

        tag_dicts = self.svc.get_tags(kb_name=kb_name)
        tags = [
            {"tag": t["name"], "count": t["count"]}
            for t in tag_dicts
            if t["name"].startswith(prefix)
        ]
        return {"tag_count": len(tags), "tags": tags}

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

        schema = KBSchema.from_yaml(kb_config.path / "kb.yaml")
        return schema.to_agent_schema()

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
        schema = KBSchema.from_yaml(kb_config.path / "kb.yaml")
        validation = schema.validate_entry(entry_type, args)
        warnings = [e for e in validation.get("errors", []) if e.get("severity") == "warning"]

        if entry_type == "event" and not args.get("date"):
            return {"error": "Date is required for events"}

        entry_id = generate_entry_id(title)

        # Filter out keys already passed as explicit arguments
        extra = {
            k: v for k, v in args.items() if k not in ("kb_name", "entry_type", "title", "body")
        }

        try:
            entry = self.svc.create_entry(kb_name, entry_id, title, entry_type, body, **extra)
        except PyriteError as e:
            return {"error": str(e)}

        result = {"created": True, "entry_id": entry.id, "file_path": ""}
        if warnings:
            result["warnings"] = warnings
        return result

    def _kb_update(self, args: dict[str, Any]) -> dict[str, Any]:
        """Update an existing entry."""
        entry_id = args.get("entry_id")
        kb_name = args.get("kb_name")

        updates = {}
        for key in ("title", "body", "importance", "tags", "participants", "metadata"):
            if key in args:
                updates[key] = args[key]

        try:
            entry = self.svc.update_entry(entry_id, kb_name, **updates)
        except PyriteError as e:
            return {"error": str(e)}

        return {"updated": True, "entry_id": entry.id, "file_path": ""}

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
            schema = KBSchema.from_yaml(kb_config.path / "kb.yaml")
            return {"valid": True, "types": list(schema.types.keys())}

        return {"error": f"Unknown action: {action}"}

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

        entry_text = json.dumps(entry, indent=2, default=str)
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
            json.dumps(entry_a, indent=2, default=str)
            if entry_a
            else f"Entry '{entry_a_id}' not found"
        )
        entry_b_text = (
            json.dumps(entry_b, indent=2, default=str)
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
            events_text = json.dumps(events, indent=2, default=str)
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
                        "text": json.dumps(kbs_data, indent=2, default=str),
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
                        "text": json.dumps(entries, indent=2, default=str),
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
                        "text": json.dumps(entry, indent=2, default=str),
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
            return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]

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
