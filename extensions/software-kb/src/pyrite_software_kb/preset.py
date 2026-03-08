"""Software KB preset definition."""

SOFTWARE_KB_PRESET = {
    "name": "my-project",
    "description": "Software team knowledge base with ADRs, design docs, standards, components, backlog, and runbooks",
    "types": {
        "adr": {
            "description": "Architecture Decision Record",
            "required": ["title"],
            "optional": ["adr_number", "status", "deciders", "date", "superseded_by"],
            "subdirectory": "adrs/",
        },
        "design_doc": {
            "description": "Design document or specification",
            "required": ["title"],
            "optional": ["status", "reviewers", "date", "author", "url"],
            "subdirectory": "designs/",
        },
        "standard": {
            "description": "Coding standard or convention (legacy — use programmatic_validation or development_convention)",
            "required": ["title"],
            "optional": ["category", "enforced"],
            "subdirectory": "standards/",
        },
        "programmatic_validation": {
            "description": "Automated check with verifiable pass/fail criteria",
            "required": ["title"],
            "optional": ["category", "check_command", "pass_criteria"],
            "subdirectory": "validations/",
        },
        "development_convention": {
            "description": "Judgment-based guidance carried as context during work",
            "required": ["title"],
            "optional": ["category"],
            "subdirectory": "conventions/",
        },
        "component": {
            "description": "Module or service documentation",
            "required": ["title"],
            "optional": ["kind", "path", "owner", "dependencies"],
            "subdirectory": "components/",
        },
        "backlog_item": {
            "description": "Feature, bug, or tech debt item",
            "required": ["title"],
            "optional": ["kind", "status", "priority", "assignee", "effort"],
            "subdirectory": "backlog/",
        },
        "runbook": {
            "description": "How-to guide or operational procedure",
            "required": ["title"],
            "optional": ["runbook_kind", "audience"],
            "subdirectory": "runbooks/",
        },
        "milestone": {
            "description": "Project milestone for grouping backlog items",
            "required": ["title"],
            "optional": ["status"],
            "subdirectory": "milestones/",
        },
    },
    "policies": {
        "team_owned": True,
        "require_adr_number": True,
    },
    "validation": {
        "enforce": True,
        "rules": [
            {"field": "status", "enum": ["proposed", "accepted", "deprecated", "superseded"]},
        ],
    },
    "directories": ["adrs", "designs", "standards", "validations", "conventions", "components", "backlog", "runbooks", "milestones"],
    "default_board": {
        "lanes": [
            {"name": "Backlog", "statuses": ["proposed", "planned"]},
            {"name": "Ready", "statuses": ["accepted"]},
            {"name": "In Progress", "statuses": ["in_progress"], "wip_limit": 5},
            {"name": "Review", "statuses": ["review"], "wip_limit": 3},
            {"name": "Done", "statuses": ["done", "completed"]},
        ],
        "wip_policy": "warn",
    },
}
