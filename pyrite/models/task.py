"""Task entry type and workflow definitions."""

from dataclasses import dataclass, field
from typing import Any

from ..schema import Provenance, generate_entry_id
from ..utils.parse import safe_int
from .base import parse_datetime, parse_links, parse_sources
from .core_types import NoteEntry
from .protocols import Assignable, Parentable, Prioritizable, Statusable, Temporal

TASK_STATUSES = (
    "open",
    "claimed",
    "in_progress",
    "blocked",
    "review",
    "done",
    "failed",
    "cancelled",
)
TASK_PRIORITIES = tuple(range(1, 11))  # 1-10

# Terminal states that mean "resolved, no further work expected" — both for
# parent rollup and dependency unblocking. `failed` is intentionally excluded:
# a failed task is not resolved (it can be reopened), so it should not roll up a
# parent or unblock dependents.
TASK_RESOLVED_STATUSES = ("done", "cancelled")

# =========================================================================
# Workflow
# =========================================================================

TASK_WORKFLOW = {
    "states": [
        "open",
        "claimed",
        "in_progress",
        "blocked",
        "review",
        "done",
        "failed",
        "cancelled",
    ],
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
        # Cancel an obsolete task from any non-terminal state. Closes in one
        # call and reads honestly: no work was claimed or performed.
        {
            "from": "open",
            "to": "cancelled",
            "requires": "write",
            "description": "Cancel an obsolete, never-worked task",
        },
        {
            "from": "claimed",
            "to": "cancelled",
            "requires": "write",
            "description": "Cancel a claimed but obsolete task",
        },
        {
            "from": "in_progress",
            "to": "cancelled",
            "requires": "write",
            "description": "Cancel a task recognized as obsolete mid-work",
        },
        {
            "from": "blocked",
            "to": "cancelled",
            "requires": "write",
            "description": "Cancel a blocked, no-longer-needed task",
        },
        {
            "from": "review",
            "to": "cancelled",
            "requires": "write",
            "description": "Cancel a task in review that's no longer needed",
        },
        # Privileged stale-claim recovery: release a claim back to open when a
        # worker crashed/aged out. Requires a reason for the audit trail. This
        # is the conductor/operator path (see TaskService.reset_task), not a
        # normal worker transition.
        {
            "from": "in_progress",
            "to": "open",
            "requires": "write",
            "requires_reason": True,
            "description": "Reset a stale in_progress claim back to open",
        },
        {
            "from": "blocked",
            "to": "open",
            "requires": "write",
            "requires_reason": True,
            "description": "Reset a stale blocked claim back to open",
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


def resolve_workflow_for_type(entry_type: str, kb_schema: Any) -> dict:
    """Return the workflow dict that should govern transitions for entries
    of ``entry_type``.

    The locked design (Tier A r1175, Reading C):

      - For the core ``task`` type or any type whose TypeSchema does not
        carry a ``state_machine`` block: return ``TASK_WORKFLOW``
        (preserves all existing behavior).
      - For a type whose TypeSchema carries a ``state_machine`` dict
        (e.g. a plugin's ``sw_ticket`` that opts into relaxed mode):
        return that dict. Plugin can override ``enforce_transitions``,
        ``require_reason_on_transition``, ``states``, ``transitions``
        independently.

    Args:
        entry_type: The entry's type name (e.g. ``"task"``, ``"sw_ticket"``).
        kb_schema: The KB's ``KBSchema`` instance, or None if unavailable.

    Returns:
        A workflow dict in the same shape as ``TASK_WORKFLOW``.
    """
    if kb_schema is None:
        return TASK_WORKFLOW
    get_type_schema = getattr(kb_schema, "get_type_schema", None)
    if get_type_schema is None:
        return TASK_WORKFLOW
    type_schema = get_type_schema(entry_type)
    if type_schema is None:
        return TASK_WORKFLOW
    state_machine = getattr(type_schema, "state_machine", None)
    if state_machine:
        return state_machine
    return TASK_WORKFLOW


def validate_status_change(
    workflow: dict,
    old_status: str,
    new_status: str,
    status_reason: str = "",
    user_role: str = "write",
) -> tuple[bool, str]:
    """Validate a status transition under either the strict or relaxed regime.

    Dispatches based on the workflow's ``enforce_transitions`` flag (Tier A
    r1175 per-entity-type relaxed-mode design):

      - **strict** (``enforce_transitions=True``, default): the transition
        must appear in the workflow's ``transitions`` table. Reason is
        only required when the matching transition declares
        ``requires_reason: True`` (matches pre-existing behavior).
      - **relaxed** (``enforce_transitions=False``): any ``new_status``
        that's a member of ``workflow["states"]`` is accepted, IFF
        ``status_reason`` is non-empty (when
        ``require_reason_on_transition=True``, the default for relaxed
        mode). Loosens transitions but NOT state membership — typos in
        status still fail, which keeps the index queryable.

    The atomic ``open→claimed`` invariant lives at the repo/db
    compare-and-swap layer, not here. This function never blocks
    ``open→claimed`` under either mode (strict has it declared; relaxed
    accepts it as a member of ``states`` with reason).

    Args:
        workflow: Workflow dict (see ``TASK_WORKFLOW`` for shape). May
            carry ``enforce_transitions`` and
            ``require_reason_on_transition`` keys; defaults preserve
            back-compat (strict, reason optional).
        old_status: Current task status.
        new_status: Target status.
        status_reason: Free-string reason for the transition (v1; entry-ref
            shape is a future enrichment per ticket design).
        user_role: Role of the caller; only consulted in strict mode.

    Returns:
        ``(ok, error_message)``. ``ok=True`` with empty message on
        success; ``ok=False`` with a one-line human-readable message
        otherwise.
    """
    enforce = workflow.get("enforce_transitions", True)
    require_reason = workflow.get("require_reason_on_transition", False)

    if enforce:
        # Strict path: existing behavior. Transition must be in the
        # declared table; reason is required only for transitions that
        # opt in via `requires_reason: True`.
        if not can_transition(workflow, old_status, new_status, user_role):
            allowed = [
                t["to"]
                for t in get_allowed_transitions(workflow, old_status, user_role)
            ]
            allowed_msg = ", ".join(allowed) if allowed else "(none — terminal state)"
            return (
                False,
                f"Cannot move from '{old_status}' to '{new_status}'. "
                f"Allowed next: {allowed_msg}.",
            )
        if requires_reason(workflow, old_status, new_status) and not status_reason.strip():
            return (
                False,
                f"Transition '{old_status}' → '{new_status}' requires a reason "
                f"(set --reason / status_reason).",
            )
        return True, ""

    # Relaxed path: any member of `states` accepted, with reason gating.
    states = workflow.get("states", [])
    if new_status not in states:
        return (
            False,
            f"Status '{new_status}' is not in the declared state set "
            f"({', '.join(states) or '(empty)'}). Relaxed mode loosens "
            f"transitions, not state membership — check for typos.",
        )
    if require_reason and not status_reason.strip():
        return (
            False,
            f"Relaxed-mode transition '{old_status}' → '{new_status}' "
            f"requires a non-empty status_reason (set --reason).",
        )
    return True, ""


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
        "aliases": meta.get("aliases", []) or [],
        "sources": parse_sources(meta.get("sources")),
        "links": parse_links(meta.get("links")),
        "provenance": provenance,
        "importance": safe_int(meta.get("importance"), 5),
        "metadata": meta.get("metadata", {}),
        "created_at": parse_datetime(meta.get("created_at")),
        "updated_at": parse_datetime(meta.get("updated_at")),
        "_schema_version": safe_int(meta.get("_schema_version"), 0),
    }


@dataclass
class TaskEntry(Assignable, Temporal, Statusable, Prioritizable, Parentable, NoteEntry):
    """Agent-oriented task with workflow state machine."""

    status: str = "open"  # overrides Statusable default
    status_reason: str = ""  # Free-string reason for the current status (Tier A r1175)
    parent: str = ""  # overrides Parentable default
    dependencies: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    priority: int = 5  # overrides Prioritizable default
    agent_context: dict[str, Any] = field(default_factory=dict)
    # Structured audit trail of status transitions: each entry is
    # {date, from, to, by, comment}. Appended on status change when a comment
    # is supplied, so the *why* of a transition lives with the task rather than
    # only in git history.
    status_change_log: list[dict[str, Any]] = field(default_factory=list)

    @property
    def entry_type(self) -> str:
        return "task"

    def to_frontmatter(self) -> dict[str, Any]:
        meta = super().to_frontmatter()
        meta["type"] = "task"
        meta["status"] = self.status
        if self.status_reason:
            meta["status_reason"] = self.status_reason
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
        if self.status_change_log:
            meta["status_change_log"] = self.status_change_log
        return meta

    @classmethod
    def from_frontmatter(cls, meta: dict[str, Any], body: str) -> "TaskEntry":
        kwargs = _note_base_kwargs(meta, body)
        # Accept both "parent" and legacy "parent_task"
        parent = meta.get("parent", "") or meta.get("parent_task", "")
        return cls(
            **kwargs,
            status=meta.get("status", "open"),
            status_reason=meta.get("status_reason", "") or "",
            assignee=meta.get("assignee", ""),
            parent=parent,
            dependencies=meta.get("dependencies", []) or [],
            evidence=meta.get("evidence", []) or [],
            priority=meta.get("priority", 5),
            due_date=meta.get("due_date", ""),
            agent_context=meta.get("agent_context", {}) or {},
            status_change_log=meta.get("status_change_log", []) or [],
        )
