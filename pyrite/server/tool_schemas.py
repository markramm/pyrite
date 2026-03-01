"""
MCP tool schema definitions for Pyrite.

Static description and inputSchema data for all MCP tools, separated from
handler logic in mcp_server.py. Each dict maps tool_name -> {description, inputSchema}.
"""

READ_TOOLS = {
    "kb_list": {
        "description": "List all mounted knowledge bases with their types and entry counts",
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
    "kb_search": {
        "description": "Full-text search across knowledge bases. Supports FTS5 query syntax (AND, OR, NOT, phrases in quotes). Returns entries with snippets ranked by relevance.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (FTS5 syntax supported)",
                },
                "kb_name": {
                    "type": "string",
                    "description": "Limit search to specific KB (optional)",
                },
                "entry_type": {
                    "type": "string",
                    "description": "Filter by entry type: note, person, organization, event, document, topic, etc.",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Filter by tags (entries must have ALL specified tags)",
                },
                "date_from": {
                    "type": "string",
                    "description": "Start date (YYYY-MM-DD)",
                },
                "date_to": {
                    "type": "string",
                    "description": "End date (YYYY-MM-DD)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum results to return (default 20)",
                },
                "offset": {
                    "type": "integer",
                    "description": "Pagination offset (default 0)",
                },
                "mode": {
                    "type": "string",
                    "enum": ["keyword", "semantic", "hybrid"],
                    "description": "Search mode: keyword (FTS5), semantic (vector), or hybrid. Default: keyword",
                },
                "expand": {
                    "type": "boolean",
                    "description": "Use AI query expansion for additional search terms. Default: false",
                },
            },
            "required": ["query"],
        },
    },
    "kb_get": {
        "description": "Get a specific entry by its ID. Returns full content including body, metadata, sources, and links.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "entry_id": {
                    "type": "string",
                    "description": "The entry ID (e.g., '2025-01-20--event-slug' or 'alice-smith')",
                },
                "kb_name": {
                    "type": "string",
                    "description": "KB name (optional - searches all KBs if not provided)",
                },
            },
            "required": ["entry_id"],
        },
    },
    "kb_timeline": {
        "description": "Get timeline events within a date range, optionally filtered by importance.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "date_from": {
                    "type": "string",
                    "description": "Start date (YYYY-MM-DD)",
                },
                "date_to": {"type": "string", "description": "End date (YYYY-MM-DD)"},
                "min_importance": {
                    "type": "integer",
                    "description": "Minimum importance score (1-10)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum results (default 50)",
                },
                "offset": {
                    "type": "integer",
                    "description": "Pagination offset (default 0)",
                },
            },
            "required": [],
        },
    },
    "kb_backlinks": {
        "description": "Get all entries that link TO a given entry (reverse link lookup).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "entry_id": {
                    "type": "string",
                    "description": "Entry ID to find backlinks for",
                },
                "kb_name": {"type": "string", "description": "KB name"},
                "limit": {
                    "type": "integer",
                    "description": "Maximum results (default 100)",
                },
                "offset": {
                    "type": "integer",
                    "description": "Pagination offset (default 0)",
                },
            },
            "required": ["entry_id", "kb_name"],
        },
    },
    "kb_tags": {
        "description": "Get all tags with their usage counts, optionally filtered by KB. Supports hierarchical /-separated tags.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "kb_name": {
                    "type": "string",
                    "description": "Filter to specific KB (optional)",
                },
                "prefix": {
                    "type": "string",
                    "description": "Filter tags starting with prefix",
                },
                "tree": {
                    "type": "boolean",
                    "description": "Return hierarchical tree instead of flat list",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum tags to return (default 100)",
                },
                "offset": {
                    "type": "integer",
                    "description": "Pagination offset (default 0)",
                },
            },
            "required": [],
        },
    },
    "kb_stats": {
        "description": "Get index statistics: entry counts, tag counts, link counts per KB.",
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
    "kb_schema": {
        "description": "Get the schema for a knowledge base. Returns available entry types, required/optional fields, validation rules, and relationship types. Essential for agents creating entries.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "kb_name": {
                    "type": "string",
                    "description": "KB name to get schema for",
                },
            },
            "required": ["kb_name"],
        },
    },
    "kb_qa_validate": {
        "description": "Validate KB structural integrity. Checks missing titles, empty bodies, broken links, orphans, invalid dates, importance range, and schema violations.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "kb_name": {
                    "type": "string",
                    "description": "KB to validate (validates all if not provided)",
                },
                "entry_id": {
                    "type": "string",
                    "description": "Validate a single entry (requires kb_name)",
                },
                "severity": {
                    "type": "string",
                    "enum": ["error", "warning", "info"],
                    "description": "Minimum severity to include (default: warning)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum issues to return (default 50)",
                },
            },
            "required": [],
        },
    },
    "kb_qa_status": {
        "description": "Get QA status dashboard with issue counts by severity and rule.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "kb_name": {
                    "type": "string",
                    "description": "KB to check (checks all if not provided)",
                },
            },
            "required": [],
        },
    },
}

WRITE_TOOLS = {
    "kb_create": {
        "description": "Create a new entry in a knowledge base. Validates against kb.yaml schema and returns warnings for unknown vocabulary values. Use kb_schema first to discover valid types and fields.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "kb_name": {"type": "string", "description": "Target KB name"},
                "entry_type": {
                    "type": "string",
                    "description": "Entry type: note, person, organization, event, document, topic, relationship, timeline, or custom type from kb.yaml",
                },
                "title": {"type": "string", "description": "Entry title"},
                "body": {
                    "type": "string",
                    "description": "Entry body content (markdown)",
                },
                "date": {
                    "type": "string",
                    "description": "Date (YYYY-MM-DD) - required for events",
                },
                "importance": {
                    "type": "integer",
                    "description": "Importance score 1-10 (default 5)",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tags for categorization",
                },
                "participants": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Participants involved (for events)",
                },
                "role": {
                    "type": "string",
                    "description": "Role description (for person entries)",
                },
                "metadata": {
                    "type": "object",
                    "description": "Additional fields for custom types or extension fields",
                },
                "validate": {
                    "type": "boolean",
                    "description": "Run QA validation after save and return issues. Also runs automatically if KB has qa_on_write: true in kb.yaml.",
                },
            },
            "required": ["kb_name", "entry_type", "title"],
        },
    },
    "kb_bulk_create": {
        "description": "Create multiple entries in one batch. More efficient than sequential kb_create calls \u2014 single index sync and batched embedding. Validates each entry against kb.yaml schema. Best-effort: each entry succeeds or fails independently. Max 50 entries per call.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "kb_name": {"type": "string", "description": "Target KB name"},
                "entries": {
                    "type": "array",
                    "description": "Array of entry specs (max 50)",
                    "maxItems": 50,
                    "items": {
                        "type": "object",
                        "properties": {
                            "entry_type": {
                                "type": "string",
                                "description": "Entry type: note, person, organization, event, etc.",
                            },
                            "title": {
                                "type": "string",
                                "description": "Entry title",
                            },
                            "body": {
                                "type": "string",
                                "description": "Entry body content (markdown)",
                            },
                            "date": {"type": "string", "description": "Date (YYYY-MM-DD)"},
                            "importance": {"type": "integer", "description": "Importance 1-10"},
                            "tags": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Tags for categorization",
                            },
                            "metadata": {
                                "type": "object",
                                "description": "Additional fields",
                            },
                        },
                        "required": ["title"],
                    },
                },
            },
            "required": ["kb_name", "entries"],
        },
    },
    "kb_update": {
        "description": "Update an existing entry. Only provided fields are updated. Runs schema validation and returns warnings for unknown select/multi-select values.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "entry_id": {"type": "string", "description": "Entry ID to update"},
                "kb_name": {"type": "string", "description": "KB containing the entry"},
                "title": {"type": "string", "description": "New title"},
                "body": {"type": "string", "description": "New body content (markdown)"},
                "importance": {"type": "integer", "description": "Importance score 1-10"},
                "tags": {"type": "array", "items": {"type": "string"}, "description": "Replacement tags (overwrites existing)"},
                "participants": {"type": "array", "items": {"type": "string"}, "description": "Participants involved (for events)"},
                "metadata": {
                    "type": "object",
                    "description": "Additional/extension fields to update",
                },
                "validate": {
                    "type": "boolean",
                    "description": "Run QA validation after save and return issues. Also runs automatically if KB has qa_on_write: true in kb.yaml.",
                },
            },
            "required": ["entry_id", "kb_name"],
        },
    },
    "kb_delete": {
        "description": "Delete an entry from a knowledge base.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "entry_id": {"type": "string", "description": "Entry ID to delete"},
                "kb_name": {"type": "string", "description": "KB name"},
            },
            "required": ["entry_id", "kb_name"],
        },
    },
    "kb_link": {
        "description": "Create a link between two entries. Adds a typed relationship from source to target. Idempotent \u2014 linking the same pair twice has no effect.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "source_id": {
                    "type": "string",
                    "description": "Source entry ID",
                },
                "source_kb": {
                    "type": "string",
                    "description": "KB containing the source entry",
                },
                "target_id": {
                    "type": "string",
                    "description": "Target entry ID",
                },
                "relation": {
                    "type": "string",
                    "description": "Relationship type (default: related_to)",
                },
                "target_kb": {
                    "type": "string",
                    "description": "KB containing the target entry (defaults to source_kb)",
                },
                "note": {
                    "type": "string",
                    "description": "Optional note about the link",
                },
            },
            "required": ["source_id", "source_kb", "target_id"],
        },
    },
    "kb_qa_assess": {
        "description": "Run QA assessment on an entry or entire KB. Creates qa_assessment entries recording results. Optionally creates tasks for failures.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "kb_name": {
                    "type": "string",
                    "description": "KB to assess",
                },
                "entry_id": {
                    "type": "string",
                    "description": "Specific entry to assess (assesses entire KB if omitted)",
                },
                "tier": {
                    "type": "integer",
                    "description": "Assessment tier: 1=structural (default)",
                },
                "max_age_hours": {
                    "type": "integer",
                    "description": "Skip entries assessed within this many hours (default 24, 0 to reassess all)",
                },
                "create_tasks": {
                    "type": "boolean",
                    "description": "Create tasks for failed assessments (default false)",
                },
            },
            "required": ["kb_name"],
        },
    },
}

ADMIN_TOOLS = {
    "kb_index_sync": {
        "description": "Sync the search index with file changes. Use after editing files directly.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "kb_name": {
                    "type": "string",
                    "description": "Sync specific KB (optional - syncs all if not provided)",
                }
            },
            "required": [],
        },
    },
    "kb_manage": {
        "description": "Manage knowledge bases: add, remove, discover, validate.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["discover", "validate", "show_schema", "add_type", "remove_type", "set_schema"],
                    "description": "Management action",
                },
                "kb_name": {"type": "string", "description": "KB name (for validate)"},
                "type_name": {"type": "string", "description": "Type name (for add_type, remove_type)"},
                "type_def": {
                    "type": "object",
                    "description": "Type definition with description, required, optional, subdirectory (for add_type)",
                },
                "schema": {
                    "type": "object",
                    "description": "Schema object with types, policies, validation keys (for set_schema)",
                },
            },
            "required": ["action"],
        },
    },
    "kb_commit": {
        "description": "Commit changes in a KB's git repository. Stages and commits files with a message. Admin tier only \u2014 prevents write-tier agents from self-approving changes.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "kb": {
                    "type": "string",
                    "description": "Knowledge base name",
                },
                "message": {
                    "type": "string",
                    "description": "Commit message describing the changes",
                },
                "paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific file paths to commit (commits all changes if omitted)",
                },
                "sign_off": {
                    "type": "boolean",
                    "description": "Add Signed-off-by line to commit",
                },
            },
            "required": ["kb", "message"],
        },
    },
    "kb_push": {
        "description": "Push KB commits to a remote repository. Requires a configured remote. Admin tier only.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "kb": {
                    "type": "string",
                    "description": "Knowledge base name",
                },
                "remote": {
                    "type": "string",
                    "description": "Remote name (default: origin)",
                },
                "branch": {
                    "type": "string",
                    "description": "Branch to push (default: current branch)",
                },
            },
            "required": ["kb"],
        },
    },
}
