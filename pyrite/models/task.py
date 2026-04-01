"""Task entry type and workflow definitions."""

from dataclasses import dataclass, field
from typing import Any

from ..schema import Provenance, generate_entry_id
from .base import parse_datetime, parse_links, parse_sources
from .core_types import NoteEntry
from .protocols import Assignable, Parentable, Prioritizable, Statusable, Temporal

TASK_STATUSES = ("open", "claimed", "in_progress", "blocked", "review", "done", "failed")
TASK_PRIORITIES = tuple(range(1, 11))  # 1-10

# =========================================================================
# Workflow
# =========================================================================

TASK_WORKFLOW = {
    "states": ["open", "claimed", "in_progress", "blocked", "review", "done", "failed"],
    "initial": "open",
    "field": "status",
    "transitions": [
        {
            "from": "open",
            "to": "claimed",
            "requires": "write",
            "description": "Claim a task for work",
        },
        {
            "from": "claimed",
            "to": "in_progress",
            "requires": "write",
            "description": "Start working on the task",
        },
        {
            "from": "in_progress",
            "to": "blocked",
            "requires": "write",
            "description": "Mark task as blocked",
        },
        {
            "from": "in_progress",
            "to": "review",
            "requires": "write",
            "description": "Submit task for review",
        },
        {
            "from": "in_progress",
            "to": "done",
            "requires": "write",
            "description": "Mark task as done",
        },
        {
            "from": "in_progress",
            "to": "failed",
            "requires": "write",
            "description": "Mark task as failed",
        },
        {
            "from": "blocked",
            "to": "in_progress",
            "requires": "write",
            "description": "Resume blocked task",
        },
        {
            "from": "review",
            "to": "done",
            "requires": "write",
            "description": "Approve and complete task",
        },
        {
            "from": "review",
            "to": "in_progress",
            "requires": "write",
            "description": "Send task back for more work",
        },
        {
            "from": "failed",
            "to": "open",
            "requires": "write",
            "requires_reason": True,
            "description": "Reopen a failed task",
        },
    ],
}


def get_allowed_transitions(workflow: dict, current_state: str, user_role: str = "") -> list[dict]:
    """Get allowed transitions from the current state for the given role."""
    allowed = []
    for t in workflow["transitions"]:
        if t["from"] != current_state:
            continue
        required = t.get("requires", "")
        if not required:
            allowed.append(t)
        elif required == "write" and user_role in ("write", "reviewer", "admin"):
            allowed.append(t)
        elif required == "reviewer" and user_role in ("reviewer", "admin"):
            allowed.append(t)
        elif required == "admin" and user_role == "admin":
            allowed.append(t)
    return allowed


def can_transition(
    workflow: dict, current_state: str, target_state: str, user_role: str = ""
) -> bool:
    """Check if a specific transition is allowed."""
    for t in get_allowed_transitions(workflow, current_state, user_role):
        if t["to"] == target_state:
            return True
    return False


def requires_reason(workflow: dict, current_state: str, target_state: str) -> bool:
    """Check if a transition requires a reason."""
    for t in workflow["transitions"]:
        if t["from"] == current_state and t["to"] == target_state:
            return t.get("requires_reason", False)
    return False


# =========================================================================
# KB Preset
# =========================================================================

TASK_KB_PRESET = {
    "name": "task-board",
    "description": "Agent-oriented task tracking with workflow state machine",
    "types": {
        "task": {
            "description": "Agent-oriented task with workflow state machine",
            "required": ["title"],
            "optional": [
                "status",
                "assignee",
                "parent",
                "dependencies",
                "evidence",
                "priority",
                "due_date",
                "agent_context",
            ],
            "subdirectory": "tasks/",
        },
    },
    "policies": {
        "enforce_workflow": True,
    },
    "validation": {
        "enforce": True,
        "rules": [
            {
                "field": "status",
                "enum": list(TASK_STATUSES),
            },
            {"field": "priority", "range": [1, 10]},
        ],
    },
    "directories": ["tasks"],
}


# =========================================================================
# Entry type
# =========================================================================


def _note_base_kwargs(meta: dict[str, Any], body: str) -> dict[str, Any]:
    prov_data = meta.get("provenance")
    provenance = Provenance.from_dict(prov_data) if prov_data else None
    entry_id = meta.get("id", "")
    if not entry_id:
        entry_id = generate_entry_id(meta.get("title", ""))
    return {
        "id": entry_id,
        "title": meta.get("title", ""),
        "body": body,
        "summary": meta.get("summary", ""),
        "tags": meta.get("tags", []) or [],
        "sources": parse_sources(meta.get("sources")),
        "links": parse_links(meta.get("links")),
        "provenance": provenance,
        "metadata": meta.get("metadata", {}),
        "created_at": parse_datetime(meta.get("created_at")),
        "updated_at": parse_datetime(meta.get("updated_at")),
    }


@dataclass
class TaskEntry(Assignable, Temporal, Statusable, Prioritizable, Parentable, NoteEntry):
    """Agent-oriented task with workflow state machine."""

    status: str = "open"  # overrides Statusable default
    parent: str = ""  # overrides Parentable default
    dependencies: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    priority: int = 5  # overrides Prioritizable default
    agent_context: dict[str, Any] = field(default_factory=dict)

    @property
    def entry_type(self) -> str:
        return "task"

    def to_frontmatter(self) -> dict[str, Any]:
        meta = super().to_frontmatter()
        meta["type"] = "task"
        meta["status"] = self.status
        if self.assignee:
            meta["assignee"] = self.assignee
        if self.parent:
            meta["parent"] = self.parent
        if self.dependencies:
            meta["dependencies"] = self.dependencies
        if self.evidence:
            meta["evidence"] = self.evidence
        meta["priority"] = self.priority
        if self.due_date:
            meta["due_date"] = self.due_date
        if self.agent_context:
            meta["agent_context"] = self.agent_context
        return meta

    @classmethod
    def from_frontmatter(cls, meta: dict[str, Any], body: str) -> "TaskEntry":
        kwargs = _note_base_kwargs(meta, body)
        # Accept both "parent" and legacy "parent_task"
        parent = meta.get("parent", "") or meta.get("parent_task", "")
        return cls(
            **kwargs,
            status=meta.get("status", "open"),
            assignee=meta.get("assignee", ""),
            parent=parent,
            dependencies=meta.get("dependencies", []) or [],
            evidence=meta.get("evidence", []) or [],
            priority=meta.get("priority", 5),
            due_date=meta.get("due_date", ""),
            agent_context=meta.get("agent_context", {}) or {},
        )
