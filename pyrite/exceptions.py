"""
Pyrite Exception Hierarchy

Typed exceptions for distinct error conditions, replacing generic ValueError/PermissionError.
"""


class PyriteError(Exception):
    """Base exception for all Pyrite errors."""


class EntryNotFoundError(PyriteError):
    """Raised when an entry cannot be found."""


class KBNotFoundError(PyriteError):
    """Raised when a knowledge base cannot be found."""


class KBReadOnlyError(PyriteError):
    """Raised when attempting to write to a read-only KB."""


class ValidationError(PyriteError):
    """Raised when entry data fails validation."""


class FrontmatterError(ValidationError):
    """Raised when YAML frontmatter is malformed or not a mapping.

    A ValidationError subclass so existing ``except ValidationError`` handlers
    continue to catch it, while callers that care specifically about parse
    failures can catch this narrower type.
    """


class PluginError(PyriteError):
    """Raised when a plugin operation fails."""


class StorageError(PyriteError):
    """Raised when a storage operation fails."""


class KBProtectedError(PyriteError):
    """Raised when attempting to modify/remove a config-protected KB."""


class ConfigError(PyriteError):
    """Raised when configuration is invalid."""


class QuerySyntaxError(PyriteError):
    """Raised when a search query cannot be parsed by the backend's query
    engine (e.g. SQLite FTS5's ``no such column: ...`` when a bare
    special-char token reaches MATCH unquoted).

    Deterministic and not retryable — the query needs to change, retrying
    unchanged will fail identically. Carries an ``error_code`` attribute
    (``QUERY_SYNTAX``) so REST/MCP/CLI handlers can surface a stable
    identifier instead of falling through to a generic internal error.
    """

    error_code = "QUERY_SYNTAX"


class ClipperBlockedHostError(PyriteError):
    """Raised when the web clipper refuses to fetch a URL because the
    resolved host is on the SSRF blocklist (loopback, link-local,
    RFC1918 private, reserved IPv4/IPv6 ranges) or because the URL uses
    a non-http(s) scheme.

    Carries an ``error_code`` attribute (``CLIPPER_BLOCKED_HOST``) so
    REST/MCP handlers can surface a stable identifier.
    """

    error_code = "CLIPPER_BLOCKED_HOST"
