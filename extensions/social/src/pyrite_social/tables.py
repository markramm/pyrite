"""Social KB custom database tables."""

SOCIAL_TABLES = [
    {
        "name": "social_vote",
        "columns": [
            {"name": "id", "type": "INTEGER", "primary_key": True},
            {"name": "entry_id", "type": "TEXT", "nullable": False},
            {"name": "kb_name", "type": "TEXT", "nullable": False},
            {"name": "user_id", "type": "TEXT", "nullable": False},
            {"name": "value", "type": "INTEGER", "nullable": False},  # +1 or -1
            {"name": "created_at", "type": "TEXT", "nullable": False},
        ],
        "indexes": [
            {"columns": ["entry_id", "kb_name", "user_id"], "unique": True},
            {"columns": ["entry_id", "kb_name"]},
            {"columns": ["user_id"]},
        ],
    },
    {
        "name": "social_reputation_log",
        "columns": [
            {"name": "id", "type": "INTEGER", "primary_key": True},
            {"name": "user_id", "type": "TEXT", "nullable": False},
            {"name": "delta", "type": "INTEGER", "nullable": False},
            {"name": "reason", "type": "TEXT", "nullable": False},
            {"name": "entry_id", "type": "TEXT"},
            {"name": "kb_name", "type": "TEXT"},
            {"name": "created_at", "type": "TEXT", "nullable": False},
        ],
        "indexes": [
            {"columns": ["user_id"]},
            {"columns": ["entry_id", "kb_name"]},
        ],
    },
]
