"""Task plugin — agent-oriented task management for pyrite."""

import logging
from collections.abc import Callable
from typing import Any

from .entry_types import TaskEntry
from .preset import TASK_KB_PRESET
from .validators import validate_task
from .workflows import TASK_WORKFLOW, can_transition

logger = logging.getLogger(__name__)


class TaskPlugin:
    """Task management plugin for pyrite.

    Provides agent-oriented task tracking with workflow state machine,
    parent-child relationships, dependency tracking, and evidence linking.
    """

    name = "task"

    def __init__(self):
        self.ctx = None

    def set_context(self, ctx) -> None:
        """Receive shared dependencies from the plugin infrastructure."""
        self.ctx = ctx

    def _get_db(self):
        """Get DB from injected context, fallen back to self-bootstrap."""
        if self.ctx is not None:
            return self.ctx.db, False
        from pyrite.config import load_config
        from pyrite.storage.database import PyriteDB

        config = load_config()
        return PyriteDB(config.settings.index_path), True

    def get_entry_types(self) -> dict[str, type]:
        return {"task": TaskEntry}

    def get_kb_types(self) -> list[str]:
        return ["task"]

    def get_cli_commands(self) -> list[tuple[str, Any]]:
        from .cli import task_app

        return [("task", task_app)]

    def get_mcp_tools(self, tier: str) -> dict[str, dict]:
        tools = {}

        if tier in ("read", "write", "admin"):
            tools["task_list"] = {
                "description": "List tasks, filter by status/assignee/parent. Use to find available work or check progress.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "kb_name": {"type": "string", "description": "KB name (optional)"},
                        "status": {
                            "type": "string",
                            "enum": [
                                "open",
                                "claimed",
                                "in_progress",
                                "blocked",
                                "review",
                                "done",
                                "failed",
                            ],
                            "description": "Filter by task status",
                        },
                        "assignee": {
                            "type": "string",
                            "description": "Filter by assignee (e.g. agent:claude-code-7a3f)",
                        },
                        "parent": {
                            "type": "string",
                            "description": "Filter by parent task ID",
                        },
                    },
                    "required": [],
                },
                "handler": self._mcp_task_list,
            }
            tools["task_status"] = {
                "description": "Get task details including children, dependencies, and evidence links.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string", "description": "Task entry ID"},
                        "kb_name": {"type": "string", "description": "KB name (optional)"},
                    },
                    "required": ["task_id"],
                },
                "handler": self._mcp_task_status,
            }

        if tier in ("write", "admin"):
            tools["task_create"] = {
                "description": "Create a new task with optional parent, priority, and assignee.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "kb_name": {"type": "string", "description": "KB name"},
                        "title": {"type": "string", "description": "Task title"},
                        "parent_task": {
                            "type": "string",
                            "description": "Parent task entry ID",
                        },
                        "priority": {
                            "type": "integer",
                            "description": "Priority 1-10 (default 5)",
                            "minimum": 1,
                            "maximum": 10,
                        },
                        "assignee": {
                            "type": "string",
                            "description": "Assignee (e.g. agent:claude-code-7a3f)",
                        },
                        "body": {"type": "string", "description": "Task description"},
                    },
                    "required": ["title"],
                },
                "handler": self._mcp_task_create,
            }
            tools["task_update"] = {
                "description": "Update task fields (status, assignee, priority).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string", "description": "Task entry ID"},
                        "kb_name": {"type": "string", "description": "KB name"},
                        "status": {
                            "type": "string",
                            "enum": [
                                "open",
                                "claimed",
                                "in_progress",
                                "blocked",
                                "review",
                                "done",
                                "failed",
                            ],
                            "description": "New status",
                        },
                        "assignee": {
                            "type": "string",
                            "description": "New assignee",
                        },
                        "priority": {
                            "type": "integer",
                            "description": "New priority 1-10",
                            "minimum": 1,
                            "maximum": 10,
                        },
                    },
                    "required": ["task_id"],
                },
                "handler": self._mcp_task_update,
            }

        return tools

    def get_relationship_types(self) -> dict[str, dict]:
        return {
            "subtask_of": {
                "inverse": "has_subtask",
                "description": "Task is a subtask of another task",
            },
            "has_subtask": {
                "inverse": "subtask_of",
                "description": "Task has a subtask",
            },
            "produces": {
                "inverse": "produced_by",
                "description": "Task produces an entry as evidence",
            },
            "produced_by": {
                "inverse": "produces",
                "description": "Entry was produced by a task",
            },
        }

    def get_db_tables(self) -> list[dict]:
        return []

    def get_workflows(self) -> dict[str, dict]:
        return {"task_workflow": TASK_WORKFLOW}

    def get_validators(self) -> list[Callable]:
        return [validate_task]

    def get_kb_presets(self) -> dict[str, dict]:
        return {"task": TASK_KB_PRESET}

    def get_hooks(self) -> dict[str, list[Callable]]:
        return {
            "before_save": [self._hook_validate_transition],
            "after_save": [self._hook_parent_rollup],
        }

    # =========================================================================
    # Hooks
    # =========================================================================

    def _hook_validate_transition(self, entry: Any, context: dict) -> Any:
        """Validate status transitions against workflow on update."""
        if context.get("operation") != "update":
            return entry
        if not hasattr(entry, "entry_type") or entry.entry_type != "task":
            return entry

        old_status = context.get("old_status")
        new_status = getattr(entry, "status", None)
        if not old_status or not new_status or old_status == new_status:
            return entry

        if not can_transition(TASK_WORKFLOW, old_status, new_status, "write"):
            raise ValueError(
                f"Invalid task transition: {old_status} → {new_status}"
            )

        return entry

    def _hook_parent_rollup(self, entry: Any, context: dict) -> Any:
        """Log when all children of a parent task are done."""
        if not hasattr(entry, "entry_type") or entry.entry_type != "task":
            return entry

        parent_id = getattr(entry, "parent_task", "")
        if not parent_id:
            return entry

        new_status = getattr(entry, "status", "")
        if new_status == "done":
            logger.info(
                "Task %s (child of %s) marked done — check if all siblings complete",
                getattr(entry, "id", "?"),
                parent_id,
            )

        return entry

    # =========================================================================
    # MCP tool handlers
    # =========================================================================

    def _mcp_task_list(self, args: dict[str, Any]) -> dict[str, Any]:
        """List tasks with filters."""
        import json as json_mod

        db, should_close = self._get_db()
        kb_name = args.get("kb_name")
        status_filter = args.get("status")
        assignee_filter = args.get("assignee")
        parent_filter = args.get("parent")

        try:
            query = "SELECT * FROM entry WHERE entry_type = 'task'"
            params: list = []
            if kb_name:
                query += " AND kb_name = ?"
                params.append(kb_name)
            query += " ORDER BY created_at DESC"

            rows = db._raw_conn.execute(query, params).fetchall()
            tasks = []
            for row in rows:
                meta = {}
                if row["metadata"]:
                    try:
                        meta = json_mod.loads(row["metadata"])
                    except (json_mod.JSONDecodeError, TypeError):
                        pass
                status = meta.get("status", "open")
                assignee = meta.get("assignee", "")
                parent_task = meta.get("parent_task", "")
                if status_filter and status != status_filter:
                    continue
                if assignee_filter and assignee != assignee_filter:
                    continue
                if parent_filter and parent_task != parent_filter:
                    continue
                tasks.append(
                    {
                        "id": row["id"],
                        "title": row["title"],
                        "status": status,
                        "assignee": assignee,
                        "priority": meta.get("priority", 5),
                        "parent_task": parent_task,
                        "kb_name": row["kb_name"],
                    }
                )

            return {"count": len(tasks), "tasks": tasks}
        finally:
            if should_close:
                db.close()

    def _mcp_task_status(self, args: dict[str, Any]) -> dict[str, Any]:
        """Get task details with children, deps, evidence."""
        import json as json_mod

        db, should_close = self._get_db()
        task_id = args.get("task_id")
        kb_name = args.get("kb_name")

        try:
            query = "SELECT * FROM entry WHERE entry_type = 'task'"
            params: list = []
            if kb_name:
                query += " AND kb_name = ?"
                params.append(kb_name)

            rows = db._raw_conn.execute(query, params).fetchall()
            task = None
            all_tasks = []
            for row in rows:
                meta = {}
                if row["metadata"]:
                    try:
                        meta = json_mod.loads(row["metadata"])
                    except (json_mod.JSONDecodeError, TypeError):
                        pass
                entry = {
                    "id": row["id"],
                    "title": row["title"],
                    "meta": meta,
                    "kb_name": row["kb_name"],
                }
                all_tasks.append(entry)
                if row["id"] == task_id:
                    task = entry

            if not task:
                return {"error": f"Task '{task_id}' not found"}

            meta = task["meta"]
            children = [
                {"id": t["id"], "title": t["title"], "status": t["meta"].get("status", "open")}
                for t in all_tasks
                if t["meta"].get("parent_task", "") == task_id
            ]

            return {
                "id": task["id"],
                "title": task["title"],
                "status": meta.get("status", "open"),
                "assignee": meta.get("assignee", ""),
                "priority": meta.get("priority", 5),
                "parent_task": meta.get("parent_task", ""),
                "dependencies": meta.get("dependencies", []),
                "evidence": meta.get("evidence", []),
                "due_date": meta.get("due_date", ""),
                "agent_context": meta.get("agent_context", {}),
                "children": children,
                "kb_name": task["kb_name"],
            }
        finally:
            if should_close:
                db.close()

    def _mcp_task_create(self, args: dict[str, Any]) -> dict[str, Any]:
        """Create a new task."""
        title = args["title"]
        slug = title.lower().replace(" ", "-")
        priority = args.get("priority", 5)

        result = {
            "created": True,
            "title": title,
            "status": "open",
            "priority": priority,
            "filename": f"tasks/{slug}.md",
        }
        if args.get("parent_task"):
            result["parent_task"] = args["parent_task"]
        if args.get("assignee"):
            result["assignee"] = args["assignee"]
        if args.get("body"):
            result["body"] = args["body"]

        result["note"] = "Create the markdown file with this frontmatter and body to complete."
        return result

    def _mcp_task_update(self, args: dict[str, Any]) -> dict[str, Any]:
        """Update task fields."""
        task_id = args.get("task_id")
        if not task_id:
            return {"error": "task_id is required"}

        updates = {}
        if "status" in args:
            updates["status"] = args["status"]
        if "assignee" in args:
            updates["assignee"] = args["assignee"]
        if "priority" in args:
            updates["priority"] = args["priority"]

        if not updates:
            return {"error": "No updates specified"}

        return {"updated": True, "task_id": task_id, "updates": updates}
