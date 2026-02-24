---
type: component
title: "Exception Hierarchy"
kind: module
path: "pyrite/exceptions.py"
owner: "markr"
dependencies: []
tags: [core, errors]
---

# Exception Hierarchy

The exception hierarchy provides typed, domain-specific exceptions for all Pyrite error conditions. All exceptions inherit from `PyriteError`, which itself extends Python's built-in `Exception`. This replaces generic `ValueError` / `PermissionError` usage with structured errors that can be caught precisely and mapped to appropriate HTTP status codes at the API boundary.

## Key Files

| File | Purpose |
|------|---------|
| `pyrite/exceptions.py` | Defines `PyriteError` base and all specific exception classes |
| `pyrite/server/endpoints/entries.py` | Maps exceptions to HTTP status codes in API handlers |
| `pyrite/server/mcp_server.py` | Catches `PyriteError` and `ConfigError` in MCP tool handlers |

## API / Key Classes

### Exception Classes

| Exception | Description |
|-----------|-------------|
| `PyriteError` | Base exception for all Pyrite errors |
| `EntryNotFoundError` | Raised when an entry cannot be found by ID |
| `KBNotFoundError` | Raised when a knowledge base cannot be found by name |
| `KBReadOnlyError` | Raised when attempting to write to a read-only (subscribed) KB |
| `ValidationError` | Raised when entry data fails validation (bad frontmatter, missing fields, etc.) |
| `PluginError` | Raised when a plugin operation fails |
| `StorageError` | Raised when a storage/database operation fails |
| `ConfigError` | Raised when configuration is invalid |

### HTTP Status Code Mapping

The REST API endpoints in `pyrite/server/endpoints/entries.py` use a consistent pattern to translate exceptions into HTTP responses:

| Exception(s) | HTTP Status | Error Code |
|--------------|-------------|------------|
| `KBNotFoundError`, `EntryNotFoundError` | 404 Not Found | `NOT_FOUND` |
| `KBReadOnlyError` | 403 Forbidden | `READ_ONLY` |
| `ValidationError`, `PyriteError`, `ValueError` | 400 Bad Request | `CREATE_FAILED` / `UPDATE_FAILED` / `DELETE_FAILED` |

This pattern is applied uniformly in the create, update, and delete entry handlers. Each handler wraps its service call in a try/except block that catches the three exception groups in order of specificity.

In the MCP server, `PyriteError` is caught generically and returned as tool error text, since MCP does not use HTTP status codes.

## Design Notes

- **Flat hierarchy.** All exceptions are direct subclasses of `PyriteError` with no deeper nesting. This keeps the hierarchy simple and easy to catch at any granularity.
- **No custom attributes.** Exceptions carry only a message string (via the standard `Exception` constructor). Context like entry IDs or KB names is included in the message text.
- **Catch ordering matters.** Because `ValidationError` is a subclass of `PyriteError`, endpoint handlers catch it before the generic `PyriteError` fallback to assign the correct HTTP status code.
- **Gradual adoption.** The `ValueError` fallback in endpoint handlers ensures backward compatibility during the migration from generic exceptions to typed ones.

## Consumers

- **KBService** — raises `EntryNotFoundError`, `KBNotFoundError`, `KBReadOnlyError`, `ValidationError`
- **Storage layer** — raises `StorageError` for database failures
- **Plugin system** — raises `PluginError` for extension failures
- **Config loader** — raises `ConfigError` for invalid configuration
- **REST API endpoints** — catches and maps to HTTP responses
- **MCP server** — catches `PyriteError` / `ConfigError` for tool error responses

## Related

- [[rest-api]] — HTTP endpoints that map exceptions to status codes
- [[mcp-server]] — MCP tool handlers that catch PyriteError
- [[storage-layer]] — raises StorageError
- [[plugin-system]] — raises PluginError
- [[schema-validation]] — validation logic that raises ValidationError
