"""Task workflow definitions."""

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
