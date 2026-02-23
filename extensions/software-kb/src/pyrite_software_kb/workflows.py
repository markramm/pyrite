"""Software KB workflow definitions."""

ADR_LIFECYCLE = {
    "states": ["proposed", "accepted", "deprecated", "superseded"],
    "initial": "proposed",
    "field": "status",
    "transitions": [
        {
            "from": "proposed",
            "to": "accepted",
            "requires": "write",
            "description": "Accept the ADR",
        },
        {
            "from": "accepted",
            "to": "deprecated",
            "requires": "write",
            "description": "Deprecate the ADR",
        },
        {
            "from": "accepted",
            "to": "superseded",
            "requires": "write",
            "description": "Supersede the ADR (requires superseded_by link)",
        },
    ],
}

BACKLOG_WORKFLOW = {
    "states": ["proposed", "accepted", "in_progress", "done", "wont_do"],
    "initial": "proposed",
    "field": "status",
    "transitions": [
        {
            "from": "proposed",
            "to": "accepted",
            "requires": "write",
            "description": "Accept the backlog item",
        },
        {
            "from": "accepted",
            "to": "in_progress",
            "requires": "write",
            "description": "Start work on the item",
        },
        {
            "from": "in_progress",
            "to": "done",
            "requires": "write",
            "description": "Mark item as done",
        },
        {
            "from": "proposed",
            "to": "wont_do",
            "requires": "write",
            "requires_reason": True,
            "description": "Reject the proposed item",
        },
        {
            "from": "accepted",
            "to": "wont_do",
            "requires": "write",
            "requires_reason": True,
            "description": "Cancel the accepted item",
        },
        {
            "from": "done",
            "to": "accepted",
            "requires": "write",
            "requires_reason": True,
            "description": "Reopen a completed item",
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
