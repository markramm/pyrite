"""Encyclopedia custom database tables.

These are engagement-tier data: local to this install, not git-tracked.
Reviews and edit history are DB-only for performance and because they
represent workflow state rather than knowledge content.
"""

ENCYCLOPEDIA_TABLES = [
    {
        "name": "encyclopedia_review",
        "columns": [
            {"name": "id", "type": "INTEGER", "primary_key": True},
            {"name": "entry_id", "type": "TEXT", "nullable": False},
            {"name": "kb_name", "type": "TEXT", "nullable": False},
            {"name": "reviewer_id", "type": "TEXT", "nullable": False},
            {"name": "status", "type": "TEXT", "nullable": False},  # approve, reject, comment
            {"name": "comments", "type": "TEXT"},
            {"name": "created_at", "type": "TEXT", "nullable": False},
        ],
        "indexes": [
            {"columns": ["entry_id", "kb_name"]},
            {"columns": ["reviewer_id"]},
            {"columns": ["status"]},
        ],
    },
    {
        "name": "encyclopedia_article_history",
        "columns": [
            {"name": "id", "type": "INTEGER", "primary_key": True},
            {"name": "entry_id", "type": "TEXT", "nullable": False},
            {"name": "kb_name", "type": "TEXT", "nullable": False},
            {"name": "edit_summary", "type": "TEXT"},
            {"name": "editor_id", "type": "TEXT", "nullable": False},
            {"name": "created_at", "type": "TEXT", "nullable": False},
        ],
        "indexes": [
            {"columns": ["entry_id", "kb_name"]},
            {"columns": ["editor_id"]},
        ],
    },
]
