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

from pydantic import AnyUrl

from ..config import PyriteConfig, load_config
from ..exceptions import ConfigError, KBNotFoundError, KBProtectedError, PyriteError
from ..schema import generate_entry_id
from ..services.export_service import ExportService
from ..services.graph_service import GraphService
from ..services.kb_service import KBService
from ..storage.database import PyriteDB
from ..storage.index import IndexManager
from .mcp_rate_limiter import MCPRateLimiter

logger = logging.getLogger(__name__)

URI_SCHEME = "pyrite://"
MAX_BATCH_READ_ENTRIES = 50
DEFAULT_BODY_CHUNK = 8000
MAX_BODY_CHUNK = 50_000
_UPDATE_FIELDS = frozenset(
    {
        "title",
        "body",
        "importance",
        "tags",
        "participants",
        "metadata",
        "status",
        "date",
        "location",
        "summary",
        "role",
        "assignee",
        "priority",
        "due_date",
        "lifecycle",
        "affiliations",
        "org_type",
        "jurisdiction",
        "notes",
        "research_status",
        "verification_status",
        "claim_status",
        "confidence",
        "reliability",
        "evidence_refs",
        "actors",
        "source_refs",
        "sender",
        "receiver",
        "owner",
        "asset",
        "person",
        "organization",
        "funder",
        "recipient",
        "amount",
        "currency",
        "beneficial",
        "aliases",
    }
)


def _project_fields(entry: dict, fields: list[str] | None) -> dict:
    """Project only requested fields from an entry dict."""
    if not fields:
        return entry
    return {k: entry[k] for k in fields if k in entry}


def _chunk_body(entry: dict, offset: int = 0, limit: int = DEFAULT_BODY_CHUNK) -> dict:
    """Apply body chunking to an entry dict.

    If the body fits within the offset+limit window, return unchanged.
    Otherwise return a shallow copy with the body sliced and truncation metadata.
    """
    body = entry.get("body")
    if body is None:
        return entry
    body_len = len(body)
    limit = min(limit, MAX_BODY_CHUNK)
    chunk = body[offset : offset + limit]
    if offset == 0 and len(chunk) == body_len:
        # No truncation needed
        return entry
    out = {**entry, "body": chunk}
    out["body_truncated"] = True
    out["body_length"] = body_len
    out["body_offset"] = offset
    out["body_chunk_size"] = len(chunk)
    return out


def _error(
    code: str,
    message: str,
    *,
    suggestion: str | None = None,
    retryable: bool = False,
) -> dict:
    """Build a structured error response for MCP tools."""
    r: dict = {"error": message, "error_code": code, "retryable": retryable}
    if suggestion:
        r["suggestion"] = suggestion
    return r


MAX_TIMELINE_EVENTS = 50
MAX_BULK_CREATE_ENTRIES = 50
MAX_RESOURCE_LIST_ENTRIES = 200


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
        # Merge DB-registered KBs into config
        try:
            from sqlalchemy import text
            rows = self.db.session.execute(
                text("SELECT name, path, kb_type, description FROM kb WHERE source = 'user'")
            ).fetchall()
            if rows:
                db_kbs = [{"name": r[0], "path": r[1], "kb_type": r[2], "description": r[3] or ""} for r in rows]
                self.config.merge_db_kbs(db_kbs)
        except Exception:
            pass
        self.index_mgr = IndexManager(self.db, self.config)
        self.svc = KBService(self.config, self.db)
        self.graph_svc = GraphService(self.db)
        self.export_svc = ExportService(self.config, self.db)
        self._index_worker = None  # Lazy-init

        # KB registry (seeded from config on init)
        from ..services.kb_registry_service import KBRegistryService

        self.registry = KBRegistryService(self.config, self.db, self.index_mgr)
        self.registry.seed_from_config()

        # Rate limiter and tool→tier map
        self.rate_limiter = MCPRateLimiter(self.config.settings)
        self._tool_tiers: dict[str, str] = {}

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
            self._tool_tiers[name] = "read"

    def _build_write_tools(self):
        """Register write tools (available in write and admin tiers)."""
        from .tool_schemas import WRITE_TOOLS

        for name, schema in WRITE_TOOLS.items():
            self.tools[name] = {**schema, "handler": getattr(self, f"_{name}")}
            self._tool_tiers[name] = "write"

    def _build_admin_tools(self):
        """Register admin tools (available only in admin tier)."""
        from .tool_schemas import ADMIN_TOOLS

        for name, schema in ADMIN_TOOLS.items():
            self.tools[name] = {**schema, "handler": getattr(self, f"_{name}")}
            self._tool_tiers[name] = "admin"

    def _register_plugin_tools(self):
        """Register MCP tools from plugins for the current tier."""
        try:
            from ..plugins import PluginContext, get_registry

            registry = get_registry()

            # Inject shared context so plugin handlers don't need to self-bootstrap
            ctx = PluginContext(config=self.config, db=self.db)
            registry.set_context(ctx)

            plugin_tools = registry.get_all_mcp_tools(self.tier)
            for name in plugin_tools:
                self._tool_tiers[name] = self.tier
            self.tools.update(plugin_tools)
        except Exception:
            logger.warning("Plugin MCP tool loading failed", exc_info=True)

    # =========================================================================
    # Lazy service properties
    # =========================================================================

    @property
    def qa_svc(self):
        if not hasattr(self, "_qa_svc_cache"):
            from ..services.llm_service import LLMService
            from ..services.qa_service import QAService

            llm_service = LLMService(self.config.settings)
            self._qa_svc_cache = QAService(self.config, self.db, llm_service=llm_service)
        return self._qa_svc_cache

    @property
    def task_svc(self):
        if not hasattr(self, "_task_svc_cache"):
            from ..services.task_service import TaskService

            self._task_svc_cache = TaskService(self.config, self.db)
        return self._task_svc_cache

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
        kbs_data = self.registry.list_kbs()
        kbs = [
            {
                "name": kb["name"],
                "type": kb["type"],
                "path": kb["path"],
                "description": kb.get("description", ""),
                "entry_count": kb["entries"],
                "read_only": kb.get("read_only", False),
                "source": kb.get("source", "user"),
            }
            for kb in kbs_data
        ]
        return {"knowledge_bases": kbs}

    def _kb_search(self, args: dict[str, Any]) -> dict[str, Any]:
        """Full-text search with optional semantic/hybrid mode."""
        query = args.get("query", "")
        limit = args.get("limit", 20)
        fields = args.get("fields")
        include_body = args.get("include_body", False)
        results = self.search_svc.search(
            query=query,
            kb_name=args.get("kb_name"),
            entry_type=args.get("entry_type"),
            tags=args.get("tags"),
            date_from=args.get("date_from"),
            date_to=args.get("date_to"),
            limit=limit,
            offset=args.get("offset", 0),
            mode=args.get("mode", "hybrid"),
            expand=args.get("expand", False),
        )

        if fields:
            results = [_project_fields(r, fields) for r in results]
        elif not include_body:
            # Strip body by default to save tokens — snippet is included instead
            for r in results:
                r.pop("body", None)

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
        fields = args.get("fields")
        body_offset = args.get("body_offset", 0)
        body_limit = args.get("body_limit", DEFAULT_BODY_CHUNK)

        result = self.svc.get_entry(entry_id, kb_name=kb_name)

        if not result:
            return _error(
                "NOT_FOUND",
                f"Entry '{entry_id}' not found",
                suggestion="Use kb_list_entries or kb_search to find entries",
            )

        if fields:
            result = _project_fields(result, fields)
        else:
            result = _chunk_body(result, offset=body_offset, limit=body_limit)

        return {"entry": result}

    def _kb_read_body(self, args: dict[str, Any]) -> dict[str, Any]:
        """Read a chunk of an entry's body text. Lightweight continuation tool."""
        entry_id = args.get("entry_id")
        kb_name = args.get("kb_name")
        offset = args.get("body_offset", 0)
        limit = min(args.get("body_limit", DEFAULT_BODY_CHUNK), MAX_BODY_CHUNK)

        result = self.svc.get_entry(entry_id, kb_name=kb_name)
        if not result:
            return _error(
                "NOT_FOUND",
                f"Entry '{entry_id}' not found",
                suggestion="Use kb_list_entries or kb_search to find entries",
            )

        body = result.get("body") or ""
        body_len = len(body)
        chunk = body[offset : offset + limit]
        return {
            "body": chunk,
            "body_length": body_len,
            "body_offset": offset,
            "body_chunk_size": len(chunk),
            "has_more": offset + len(chunk) < body_len,
        }

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
        backlinks = self.graph_svc.get_backlinks(
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

    def _kb_batch_read(self, args: dict[str, Any]) -> dict[str, Any]:
        """Fetch multiple entries in one call."""
        entries_spec = args.get("entries", [])
        fields = args.get("fields")
        body_offset = args.get("body_offset", 0)
        body_limit = args.get("body_limit", DEFAULT_BODY_CHUNK)

        if not entries_spec:
            return _error("VALIDATION_FAILED", "entries array is required and must not be empty")
        if len(entries_spec) > MAX_BATCH_READ_ENTRIES:
            return _error("VALIDATION_FAILED", f"Maximum {MAX_BATCH_READ_ENTRIES} entries per call")

        ids = [(e["entry_id"], e["kb_name"]) for e in entries_spec]
        results = self.svc.get_entries(ids)

        if fields:
            results = [_project_fields(r, fields) for r in results]
        else:
            results = [_chunk_body(r, offset=body_offset, limit=body_limit) for r in results]

        found_ids = {(r["id"], r["kb_name"]) for r in results}
        not_found = [
            {"entry_id": eid, "kb_name": kb} for eid, kb in ids if (eid, kb) not in found_ids
        ]

        return {
            "entries": results,
            "found": len(results),
            "not_found": not_found,
        }

    def _kb_list_entries(self, args: dict[str, Any]) -> dict[str, Any]:
        """Browse entries with optional filters and pagination."""
        kb_name = args.get("kb_name")
        entry_type = args.get("entry_type")
        tag = args.get("tag")
        sort_by = args.get("sort_by", "updated_at")
        sort_order = args.get("sort_order", "desc")
        limit = min(args.get("limit", 50), 200)
        offset = args.get("offset", 0)
        fields = args.get("fields")

        entries = self.svc.list_entries(
            kb_name=kb_name,
            entry_type=entry_type,
            tag=tag,
            sort_by=sort_by,
            sort_order=sort_order,
            limit=limit,
            offset=offset,
        )
        total = self.svc.count_entries(kb_name=kb_name, entry_type=entry_type, tag=tag)

        if fields:
            entries = [_project_fields(e, fields) for e in entries]

        return {
            "entries": entries,
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total,
        }

    def _kb_orient(self, args: dict[str, Any]) -> dict[str, Any]:
        """One-shot KB orientation summary."""
        kb_name = args.get("kb_name")
        recent_limit = args.get("recent_limit", 5)
        try:
            return self.svc.orient(kb_name, recent_limit=recent_limit)
        except PyriteError as e:
            return {"error": str(e)}

    def _kb_recent(self, args: dict[str, Any]) -> dict[str, Any]:
        """Get recently changed entries."""
        kb_name = args.get("kb_name")
        entry_type = args.get("entry_type")
        limit = min(args.get("limit", 20), 200)
        since = args.get("since")
        fields = args.get("fields")

        entries = self.svc.list_entries(
            kb_name=kb_name,
            entry_type=entry_type,
            sort_by="updated_at",
            sort_order="desc",
            limit=limit,
        )

        # Post-filter by `since` if provided
        if since:
            entries = [e for e in entries if (e.get("updated_at") or "") >= since]

        if fields:
            entries = [_project_fields(e, fields) for e in entries]

        return {
            "entries": entries,
            "count": len(entries),
        }

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
            return qa.assess_kb(
                kb_name, tier=tier, max_age_hours=max_age, create_task_on_fail=create_tasks
            )

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
    # Protocol query handlers (ADR-0017)
    # =========================================================================

    def _kb_find_by_assignee(self, args: dict[str, Any]) -> dict[str, Any]:
        """Find entries assigned to a specific agent/user."""
        assignee = args.get("assignee", "")
        if not assignee:
            return _error("VALIDATION_FAILED", "assignee is required")
        rows = self.db.find_by_assignee(
            assignee=assignee,
            kb_name=args.get("kb_name"),
            status=args.get("status"),
            limit=min(args.get("limit", 50), 200),
            offset=args.get("offset", 0),
        )
        return {"entries": rows, "count": len(rows), "assignee": assignee}

    def _kb_find_overdue(self, args: dict[str, Any]) -> dict[str, Any]:
        """Find entries with overdue due_date."""
        rows = self.db.find_overdue(
            as_of=args.get("as_of"),
            kb_name=args.get("kb_name"),
            limit=min(args.get("limit", 50), 200),
            offset=args.get("offset", 0),
        )
        return {"entries": rows, "count": len(rows)}

    def _kb_find_by_status(self, args: dict[str, Any]) -> dict[str, Any]:
        """Find entries by status across all types."""
        status = args.get("status", "")
        if not status:
            return _error("VALIDATION_FAILED", "status is required")
        rows = self.db.find_by_status(
            status=status,
            kb_name=args.get("kb_name"),
            entry_type=args.get("entry_type"),
            limit=min(args.get("limit", 50), 200),
            offset=args.get("offset", 0),
        )
        return {"entries": rows, "count": len(rows), "status": status}

    def _kb_find_by_location(self, args: dict[str, Any]) -> dict[str, Any]:
        """Find entries by location (substring match)."""
        location = args.get("location", "")
        if not location:
            return _error("VALIDATION_FAILED", "location is required")
        rows = self.db.find_by_location(
            location=location,
            kb_name=args.get("kb_name"),
            limit=min(args.get("limit", 50), 200),
            offset=args.get("offset", 0),
        )
        return {"entries": rows, "count": len(rows), "location": location}

    def _list_edge_types(self, args: dict[str, Any]) -> dict[str, Any]:
        """List available edge types with their endpoint schemas."""
        kb_name = args.get("kb_name")

        edge_types = []

        for kb_config in self.config.knowledge_bases:
            if kb_name and kb_config.name != kb_name:
                continue

            schema = kb_config.kb_schema
            for type_name, type_schema in schema.types.items():
                if not getattr(type_schema, "edge_type", False):
                    continue

                endpoints = {}
                for role, ep in type_schema.endpoints.items():
                    endpoints[role] = {
                        "field": ep.field,
                        "accepts": ep.accepts,
                    }

                # Count existing edges of this type
                count = self.db.count_entries(
                    kb_name=kb_config.name,
                    entry_type=type_name,
                )

                edge_types.append(
                    {
                        "type": type_name,
                        "kb_name": kb_config.name,
                        "description": type_schema.description,
                        "endpoints": endpoints,
                        "count": count,
                    }
                )

        return {
            "edge_types": edge_types,
            "total": len(edge_types),
        }

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
            return _error(
                "KB_NOT_FOUND",
                f"KB '{kb_name}' not found",
                suggestion="Use kb_list to see available KBs",
            )
        if kb_config.read_only:
            return _error("READ_ONLY", f"KB '{kb_name}' is read-only")

        # Validate against schema
        schema = kb_config.kb_schema
        validation = schema.validate_entry(entry_type, args, context={"kb_type": kb_config.kb_type})
        warnings = validation.get("warnings", [])

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
            return _error("CREATE_FAILED", str(e), retryable=True)

        result = {
            "created": True,
            "entry_id": entry.id,
            "file_path": str(entry.file_path) if entry.file_path else "",
        }
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
            return _error("VALIDATION_FAILED", "entries array is required and must not be empty")
        if len(entries) > MAX_BULK_CREATE_ENTRIES:
            return _error(
                "VALIDATION_FAILED", f"Maximum {MAX_BULK_CREATE_ENTRIES} entries per call"
            )

        # Pre-validate each entry against schema
        kb_config = self.config.get_kb(kb_name)
        schema = None
        if kb_config:
            schema = kb_config.kb_schema

        try:
            results = self.svc.bulk_create_entries(kb_name, entries)
        except PyriteError as e:
            return _error("BULK_CREATE_FAILED", str(e), retryable=True)

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
        for key in _UPDATE_FIELDS:
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
                    entry_type,
                    {**existing, **updates},
                    context={"kb_type": kb_config.kb_type},
                )
                warnings = validation.get("warnings", [])

        try:
            entry = self.svc.update_entry(entry_id, kb_name, **updates)
        except PyriteError as e:
            return _error("UPDATE_FAILED", str(e), retryable=True)

        result: dict[str, Any] = {
            "updated": True,
            "entry_id": entry.id,
            "file_path": str(entry.file_path) if entry.file_path else "",
        }
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
            return _error("DELETE_FAILED", str(e), retryable=True)

        if not deleted:
            return _error(
                "NOT_FOUND",
                f"Entry '{entry_id}' not found in {kb_name}",
                suggestion="Use kb_list_entries or kb_search to find entries",
            )

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
            return _error("LINK_FAILED", str(e), retryable=True)

        return {
            "linked": True,
            "source_id": source_id,
            "target_id": target_id,
            "relation": relation,
        }

    # =========================================================================
    # Task handlers
    # =========================================================================

    def _task_list(self, args: dict[str, Any]) -> dict[str, Any]:
        """List tasks with filters."""
        tasks = self.task_svc.list_tasks(
            kb_name=args.get("kb_name"),
            status=args.get("status"),
            assignee=args.get("assignee"),
            parent=args.get("parent"),
        )
        return {"count": len(tasks), "tasks": tasks}

    def _task_subtree(self, args: dict[str, Any]) -> dict[str, Any]:
        """Get all descendants of a task."""
        task_id = args.get("task_id")
        if not task_id:
            return {"error": "task_id is required"}
        kb_name = args.get("kb_name") or self._find_task_kb(task_id)
        result = self._task_svc.get_subtree(task_id, kb_name)
        return {"task_id": task_id, "count": len(result), "subtree": result}

    def _task_ancestors(self, args: dict[str, Any]) -> dict[str, Any]:
        """Get parent chain from task to root."""
        task_id = args.get("task_id")
        if not task_id:
            return {"error": "task_id is required"}
        kb_name = args.get("kb_name") or self._find_task_kb(task_id)
        result = self._task_svc.get_ancestors(task_id, kb_name)
        return {"task_id": task_id, "count": len(result), "ancestors": result}

    def _task_blocked_by(self, args: dict[str, Any]) -> dict[str, Any]:
        """Get transitive dependency chain."""
        task_id = args.get("task_id")
        if not task_id:
            return {"error": "task_id is required"}
        kb_name = args.get("kb_name") or self._find_task_kb(task_id)
        result = self._task_svc.get_blocked_by(task_id, kb_name)
        return {"task_id": task_id, "count": len(result), "blocked_by": result}

    def _task_critical_path(self, args: dict[str, Any]) -> dict[str, Any]:
        """Find the longest blocking dependency chain."""
        task_id = args.get("task_id")
        if not task_id:
            return {"error": "task_id is required"}
        kb_name = args.get("kb_name") or self._find_task_kb(task_id)
        result = self._task_svc.critical_path(task_id, kb_name)
        return {"task_id": task_id, "chain_length": len(result), "critical_path": result}

    def _task_status(self, args: dict[str, Any]) -> dict[str, Any]:
        """Get task details with children, deps, evidence."""
        import json as _json

        task_id = args.get("task_id")
        kb_name = args.get("kb_name")

        task = self.task_svc.get_task(task_id, kb_name)
        if not task:
            return {"error": f"Task '{task_id}' not found"}

        meta = task.get("metadata", {})
        if isinstance(meta, str):
            try:
                meta = _json.loads(meta)
            except (ValueError, TypeError):
                meta = {}

        children_list = self.task_svc.list_tasks(kb_name=kb_name, parent=task_id)
        children = [
            {"id": c["id"], "title": c["title"], "status": c["status"]} for c in children_list
        ]

        return {
            "id": task["id"],
            "title": task["title"],
            "status": meta.get("status", "open"),
            "assignee": meta.get("assignee", ""),
            "priority": meta.get("priority", 5),
            "parent": meta.get("parent", ""),
            "dependencies": meta.get("dependencies", []),
            "evidence": meta.get("evidence", []),
            "due_date": meta.get("due_date", ""),
            "agent_context": meta.get("agent_context", {}),
            "children": children,
            "kb_name": task.get("kb_name", kb_name or ""),
        }

    def _kb_batch_suggest(self, args: dict[str, Any]) -> dict[str, Any]:
        """Batch-compare two KBs to find potential cross-KB links."""
        source_kb = args.get("source_kb")
        target_kb = args.get("target_kb")
        if not source_kb or not target_kb:
            return {"error": "source_kb and target_kb are required"}

        from ..services.link_discovery_service import LinkDiscoveryService

        svc = LinkDiscoveryService(self.config, self.db)
        pairs = svc.batch_suggest(
            source_kb=source_kb,
            target_kb=target_kb,
            limit_per_entry=args.get("limit_per_entry", 3),
            mode=args.get("mode", "keyword"),
            exclude_linked=args.get("exclude_linked", True),
        )

        return {
            "source_kb": source_kb,
            "target_kb": target_kb,
            "count": len(pairs),
            "pairs": pairs,
        }

    def _kb_discover_neighbors(self, args: dict[str, Any]) -> dict[str, Any]:
        """Find semantically similar but unlinked entries across KBs."""
        entry_id = args.get("entry_id")
        kb_name = args.get("kb_name")
        if not entry_id or not kb_name:
            return {"error": "entry_id and kb_name are required"}

        from ..services.link_discovery_service import LinkDiscoveryService

        svc = LinkDiscoveryService(self.config, self.db)
        candidates = svc.discover_neighbors(
            entry_id=entry_id,
            kb_name=kb_name,
            target_kb=args.get("target_kb"),
            limit=args.get("limit", 10),
            mode=args.get("mode", "hybrid"),
            exclude_linked=args.get("exclude_linked", True),
        )

        return {
            "entry_id": entry_id,
            "kb_name": kb_name,
            "count": len(candidates),
            "discoveries": candidates,
        }

    def _task_create(self, args: dict[str, Any]) -> dict[str, Any]:
        """Create a new task."""
        return self.task_svc.create_task(
            kb_name=args["kb_name"],
            title=args["title"],
            body=args.get("body", ""),
            parent=args.get("parent", ""),
            priority=args.get("priority", 5),
            assignee=args.get("assignee", ""),
            dependencies=args.get("dependencies"),
        )

    def _task_update(self, args: dict[str, Any]) -> dict[str, Any]:
        """Update task fields."""
        task_id = args.get("task_id")
        kb_name = args.get("kb_name")
        if not task_id:
            return {"error": "task_id is required"}
        if not kb_name:
            return {"error": "kb_name is required"}

        updates = {}
        if "status" in args:
            updates["status"] = args["status"]
        if "assignee" in args:
            updates["assignee"] = args["assignee"]
        if "priority" in args:
            updates["priority"] = args["priority"]

        if not updates:
            return {"error": "No updates specified"}

        return self.task_svc.update_task(task_id, kb_name, **updates)

    def _task_claim(self, args: dict[str, Any]) -> dict[str, Any]:
        """Atomically claim an open task."""
        return self.task_svc.claim_task(
            task_id=args["task_id"],
            kb_name=args["kb_name"],
            assignee=args["assignee"],
        )

    def _task_decompose(self, args: dict[str, Any]) -> dict[str, Any]:
        """Decompose a parent task into children."""
        try:
            results = self.task_svc.decompose_task(
                parent_id=args["parent_id"],
                kb_name=args["kb_name"],
                children=args["children"],
            )
            return {"decomposed": True, "parent_id": args["parent_id"], "children": results}
        except ValueError as e:
            return {"error": str(e)}

    def _task_checkpoint(self, args: dict[str, Any]) -> dict[str, Any]:
        """Log a checkpoint on a task."""
        try:
            return self.task_svc.checkpoint_task(
                task_id=args["task_id"],
                kb_name=args["kb_name"],
                message=args["message"],
                confidence=args.get("confidence", 0.0),
                partial_evidence=args.get("partial_evidence"),
            )
        except ValueError as e:
            return {"error": str(e)}

    # =========================================================================
    # Admin handlers
    # =========================================================================

    def _kb_index_sync(self, args: dict[str, Any]) -> dict[str, Any]:
        """Sync index with file changes. Set background=true for async execution."""
        kb_name = args.get("kb_name")
        background = args.get("background", False)

        if background:
            worker = self._get_index_worker()
            job_id = worker.submit_sync(kb_name)
            return {"submitted": True, "job_id": job_id}

        results = self.index_mgr.sync_incremental(kb_name)
        return {
            "synced": True,
            "added": results["added"],
            "updated": results["updated"],
            "removed": results["removed"],
        }

    def _kb_index_job_status(self, args: dict[str, Any]) -> dict[str, Any]:
        """Check status of a background index job."""
        job_id = args.get("job_id")
        if not job_id:
            # List active jobs
            worker = self._get_index_worker()
            return {"jobs": worker.get_active_jobs()}

        worker = self._get_index_worker()
        job = worker.get_job(job_id)
        if not job:
            return _error("NOT_FOUND", f"Job '{job_id}' not found")
        return job

    def _get_index_worker(self):
        """Lazy-init IndexWorker."""
        if self._index_worker is None:
            from ..services.index_worker import IndexWorker

            self._index_worker = IndexWorker(self.db, self.config)
        return self._index_worker

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
            return self.export_svc.commit_kb(kb_name, message=message, paths=paths, sign_off=sign_off)
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
            return self.export_svc.push_kb(kb_name, remote=remote, branch=branch)
        except PyriteError as e:
            return {"error": str(e)}

    def _kb_registry_add(self, args: dict[str, Any]) -> dict[str, Any]:
        """Register a new user KB by path."""
        name = args.get("name")
        path = args.get("path")
        if not name or not path:
            return _error("MISSING_PARAM", "'name' and 'path' are required")
        try:
            result = self.registry.add_kb(
                name=name,
                path=path,
                kb_type=args.get("kb_type", "generic"),
                description=args.get("description", ""),
            )
            return {"created": True, **result}
        except ValueError as e:
            return _error("CONFLICT", str(e))

    def _kb_registry_remove(self, args: dict[str, Any]) -> dict[str, Any]:
        """Remove a user-added KB."""
        name = args.get("name")
        if not name:
            return _error("MISSING_PARAM", "'name' is required")
        try:
            self.registry.remove_kb(name)
            return {"deleted": True, "name": name}
        except KBNotFoundError as e:
            return _error("NOT_FOUND", str(e))
        except KBProtectedError as e:
            return _error("PROTECTED", str(e))

    def _kb_registry_reindex(self, args: dict[str, Any]) -> dict[str, Any]:
        """Reindex a specific KB."""
        name = args.get("name")
        if not name:
            return _error("MISSING_PARAM", "'name' is required")
        try:
            result = self.registry.reindex_kb(name)
            return {"reindexed": True, "name": name, **result}
        except KBNotFoundError as e:
            return _error("NOT_FOUND", str(e))

    def _kb_registry_health(self, args: dict[str, Any]) -> dict[str, Any]:
        """Check KB health."""
        name = args.get("name")
        if not name:
            return _error("MISSING_PARAM", "'name' is required")
        try:
            return self.registry.health_kb(name)
        except KBNotFoundError as e:
            return _error("NOT_FOUND", str(e))

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
        events = events[:MAX_TIMELINE_EVENTS]

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
                "uri": f"{URI_SCHEME}kbs",
                "name": "Knowledge Bases",
                "description": "List all knowledge bases",
                "mimeType": "application/json",
            },
        ]

    def _build_resource_templates(self) -> list[dict[str, Any]]:
        """Build resource URI templates."""
        return [
            {
                "uriTemplate": f"{URI_SCHEME}kbs/{{name}}/entries",
                "name": "KB Entries",
                "description": "List entries in a knowledge base",
                "mimeType": "application/json",
            },
            {
                "uriTemplate": f"{URI_SCHEME}entries/{{id}}",
                "name": "Entry",
                "description": "Get a specific entry",
                "mimeType": "application/json",
            },
        ]

    def _read_resource(self, uri: str) -> dict[str, Any]:
        """Read a resource by URI and return contents."""
        if uri == f"{URI_SCHEME}kbs":
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
        if uri.startswith(f"{URI_SCHEME}kbs/") and uri.endswith("/entries"):
            kb_name = uri[len(f"{URI_SCHEME}kbs/") : -len("/entries")]
            entries = self.db.list_entries(kb_name=kb_name, limit=MAX_RESOURCE_LIST_ENTRIES)
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
        if uri.startswith(f"{URI_SCHEME}entries/"):
            entry_id = uri[len(f"{URI_SCHEME}entries/") :]
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

    def _dispatch_tool(
        self, name: str, arguments: dict[str, Any], *, client_id: str = "local"
    ) -> dict[str, Any]:
        """Execute a tool and return result."""
        if name not in self.tools:
            return _error(
                "UNKNOWN_TOOL",
                f"Unknown tool: {name}",
                suggestion="Use list_tools to see available tools",
            )

        # Rate limiting (skip for local stdio when configured)
        if not (client_id == "stdio" and self.config.settings.mcp_rate_limit_exempt_local):
            tool_tier = self._tool_tiers.get(name, "read")
            allowed, info = self.rate_limiter.check(client_id, tool_tier)
            if not allowed:
                return _error(
                    "RATE_LIMITED",
                    f"Rate limit exceeded for {tool_tier} tier. Retry after {info['retry_after']}s.",
                    suggestion=f"Wait {info['retry_after']} seconds",
                    retryable=True,
                )

        try:
            handler = self.tools[name]["handler"]
            return handler(arguments)
        except Exception as e:
            logger.exception("Tool %s failed with args %s", name, arguments)
            return _error("INTERNAL", str(e), retryable=True)

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
            result = mcp_server._dispatch_tool(name, arguments or {}, client_id="stdio")
            return [
                TextContent(
                    type="text", text=json.dumps(result, separators=(",", ":"), default=str)
                )
            ]

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
