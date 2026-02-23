"""Encyclopedia workflow definitions.

The article review workflow controls the review_status field on ArticleEntry.
State machine: draft -> under_review -> published, with ability to send back.
"""

ARTICLE_REVIEW_WORKFLOW = {
    "states": ["draft", "under_review", "published"],
    "initial": "draft",
    "field": "review_status",  # entry field this workflow controls
    "transitions": [
        {
            "from": "draft",
            "to": "under_review",
            "requires": "write",
            "description": "Submit article for review",
        },
        {
            "from": "under_review",
            "to": "published",
            "requires": "reviewer",
            "description": "Approve and publish article",
        },
        {
            "from": "under_review",
            "to": "draft",
            "requires": "reviewer",
            "description": "Send article back for revisions",
        },
        {
            "from": "published",
            "to": "under_review",
            "requires": "write",
            "requires_reason": True,
            "description": "Dispute published article, send back for review",
        },
    ],
}


def get_allowed_transitions(current_state: str, user_role: str = "") -> list[dict]:
    """Get allowed transitions from the current state for the given role."""
    allowed = []
    for t in ARTICLE_REVIEW_WORKFLOW["transitions"]:
        if t["from"] != current_state:
            continue
        required = t.get("requires", "")
        # Role hierarchy: reviewer > write > read
        if not required:
            allowed.append(t)
        elif required == "write" and user_role in ("write", "reviewer", "admin"):
            allowed.append(t)
        elif required == "reviewer" and user_role in ("reviewer", "admin"):
            allowed.append(t)
        elif required == "admin" and user_role == "admin":
            allowed.append(t)
    return allowed


def can_transition(current_state: str, target_state: str, user_role: str = "") -> bool:
    """Check if a specific transition is allowed."""
    for t in get_allowed_transitions(current_state, user_role):
        if t["to"] == target_state:
            return True
    return False


def requires_reason(current_state: str, target_state: str) -> bool:
    """Check if a transition requires a reason."""
    for t in ARTICLE_REVIEW_WORKFLOW["transitions"]:
        if t["from"] == current_state and t["to"] == target_state:
            return t.get("requires_reason", False)
    return False
