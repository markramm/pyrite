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
            "description": "Coding standard or convention",
            "required": ["title"],
            "optional": ["category", "enforced"],
            "subdirectory": "standards/",
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
    "directories": ["adrs", "designs", "standards", "components", "backlog", "runbooks"],
}
