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

    def _get_task_service(self):
        """Get a TaskService instance."""
        from .service import TaskService

        if self.ctx:
            return TaskService(self.ctx.config, self.ctx.db)
        from pyrite.config import load_config
        from pyrite.storage.database import PyriteDB

        config = load_config()
        db = PyriteDB(config.settings.index_path)
        return TaskService(config, db)

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
                        "dependencies": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Dependency entry IDs",
                        },
                    },
                    "required": ["kb_name", "title"],
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
                    "required": ["task_id", "kb_name"],
                },
                "handler": self._mcp_task_update,
            }
            tools["task_claim"] = {
                "description": "Atomically claim an open task. Fails if task is not open.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string", "description": "Task entry ID"},
                        "kb_name": {"type": "string", "description": "KB name"},
                        "assignee": {
                            "type": "string",
                            "description": "Assignee (e.g. agent:claude-code-7a3f)",
                        },
                    },
                    "required": ["task_id", "kb_name", "assignee"],
                },
                "handler": self._mcp_task_claim,
            }
            tools["task_decompose"] = {
                "description": "Decompose a parent task into child tasks.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "parent_id": {"type": "string", "description": "Parent task entry ID"},
                        "kb_name": {"type": "string", "description": "KB name"},
                        "children": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "title": {"type": "string"},
                                    "body": {"type": "string"},
                                    "priority": {"type": "integer", "minimum": 1, "maximum": 10},
                                    "assignee": {"type": "string"},
                                },
                                "required": ["title"],
                            },
                            "description": "Child task specs",
                        },
                    },
                    "required": ["parent_id", "kb_name", "children"],
                },
                "handler": self._mcp_task_decompose,
            }
            tools["task_checkpoint"] = {
                "description": "Log a checkpoint on a task with optional confidence and evidence.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string", "description": "Task entry ID"},
                        "kb_name": {"type": "string", "description": "KB name"},
                        "message": {"type": "string", "description": "Checkpoint message"},
                        "confidence": {
                            "type": "number",
                            "description": "Confidence 0.0-1.0",
                            "minimum": 0,
                            "maximum": 1,
                        },
                        "partial_evidence": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Evidence entry IDs",
                        },
                    },
                    "required": ["task_id", "kb_name", "message"],
                },
                "handler": self._mcp_task_checkpoint,
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
        """Auto-complete parent when all children are done."""
        if not hasattr(entry, "entry_type") or entry.entry_type != "task":
            return entry
        if getattr(entry, "status", "") != "done":
            return entry

        parent_id = getattr(entry, "parent_task", "")
        if not parent_id:
            return entry

        kb_name = context.get("kb_name", "")
        if not kb_name:
            return entry

        try:
            svc = self._get_task_service()
            svc.rollup_parent(parent_id, kb_name)
        except Exception as e:
            logger.warning("Parent rollup failed for %s: %s", parent_id, e)

        return entry

    # =========================================================================
    # MCP tool handlers
    # =========================================================================

    def _mcp_task_list(self, args: dict[str, Any]) -> dict[str, Any]:
        """List tasks with filters."""
        svc = self._get_task_service()
        tasks = svc.list_tasks(
            kb_name=args.get("kb_name"),
            status=args.get("status"),
            assignee=args.get("assignee"),
            parent=args.get("parent"),
        )
        return {"count": len(tasks), "tasks": tasks}

    def _mcp_task_status(self, args: dict[str, Any]) -> dict[str, Any]:
        """Get task details with children, deps, evidence."""
        svc = self._get_task_service()
        task_id = args.get("task_id")
        kb_name = args.get("kb_name")

        task = svc.get_task(task_id, kb_name)
        if not task:
            return {"error": f"Task '{task_id}' not found"}

        meta = task.get("metadata", {})
        if isinstance(meta, str):
            import json

            try:
                meta = json.loads(meta)
            except (json.JSONDecodeError, TypeError):
                meta = {}

        # Find children
        children_list = svc.list_tasks(kb_name=kb_name, parent=task_id)
        children = [
            {"id": c["id"], "title": c["title"], "status": c["status"]}
            for c in children_list
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
            "kb_name": task.get("kb_name", kb_name or ""),
        }

    def _mcp_task_create(self, args: dict[str, Any]) -> dict[str, Any]:
        """Create a new task."""
        svc = self._get_task_service()
        kb_name = args["kb_name"]
        title = args["title"]

        return svc.create_task(
            kb_name=kb_name,
            title=title,
            body=args.get("body", ""),
            parent_task=args.get("parent_task", ""),
            priority=args.get("priority", 5),
            assignee=args.get("assignee", ""),
            dependencies=args.get("dependencies"),
        )

    def _mcp_task_update(self, args: dict[str, Any]) -> dict[str, Any]:
        """Update task fields."""
        svc = self._get_task_service()
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

        return svc.update_task(task_id, kb_name, **updates)

    def _mcp_task_claim(self, args: dict[str, Any]) -> dict[str, Any]:
        """Atomically claim an open task."""
        svc = self._get_task_service()
        return svc.claim_task(
            task_id=args["task_id"],
            kb_name=args["kb_name"],
            assignee=args["assignee"],
        )

    def _mcp_task_decompose(self, args: dict[str, Any]) -> dict[str, Any]:
        """Decompose a parent task into children."""
        svc = self._get_task_service()
        try:
            results = svc.decompose_task(
                parent_id=args["parent_id"],
                kb_name=args["kb_name"],
                children=args["children"],
            )
            return {"decomposed": True, "parent_id": args["parent_id"], "children": results}
        except ValueError as e:
            return {"error": str(e)}

    def _mcp_task_checkpoint(self, args: dict[str, Any]) -> dict[str, Any]:
        """Log a checkpoint on a task."""
        svc = self._get_task_service()
        try:
            return svc.checkpoint_task(
                task_id=args["task_id"],
                kb_name=args["kb_name"],
                message=args["message"],
                confidence=args.get("confidence", 0.0),
                partial_evidence=args.get("partial_evidence"),
            )
        except ValueError as e:
            return {"error": str(e)}
