"""Task KB preset definition."""

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
                "parent_task",
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
                "enum": [
                    "open",
                    "claimed",
                    "in_progress",
                    "blocked",
                    "review",
                    "done",
                    "failed",
                ],
            },
            {"field": "priority", "range": [1, 10]},
        ],
    },
    "directories": ["tasks"],
}
