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
    """Raised when entry data fails validation.

    Every write refusal is a ValidationError, and carries a stable
    ``error_code`` that REST, MCP and the CLI all report unchanged (#378).
    Subclasses below narrow the code; the base code is ``VALIDATION_FAILED``.
    ``suggestion`` is an optional surface-neutral fix hint.
    """

    error_code = "VALIDATION_FAILED"
    suggestion: str | None = None


class UndeclaredTypeError(ValidationError):
    """A create named a type the KB's kb.yaml does not declare (#197).

    Raised only when the KB declares types at all. Core types are not
    exempt: a KB that declares a schema declares its vocabulary.
    """

    error_code = "UNDECLARED_TYPE"

    def __init__(self, message: str, declared_types: list[str]):
        super().__init__(message)
        self.declared_types = declared_types


class EntryExistsError(ValidationError):
    """A create resolved to an id that already exists. Create never replaces."""

    error_code = "ENTRY_EXISTS"


class SchemaViolationError(ValidationError):
    """The KB schema or a plugin validator rejected the entry (enum, required, range...)."""

    error_code = "SCHEMA_VIOLATION"

    def __init__(self, message: str, errors: list[dict] | None = None):
        super().__init__(message)
        self.errors = errors or []


class TruncatedBodyError(ValidationError):
    """ADR-0034 rule 2: a write carried a body marked ``body_truncated``.

    Keeps the base ``VALIDATION_FAILED`` code, which docs/json-contracts.md
    documents for this refusal.
    """

    def __init__(self, message: str, suggestion: str | None = None):
        super().__init__(message)
        self.suggestion = suggestion


class InvalidGitRefError(ValidationError):
    """A caller-supplied git remote or branch is not an acceptable name.

    A remote must be one of the repository's configured remotes (never a URL
    or a path); a branch must be a valid branch name that does not begin
    with "-". Raised before git runs. Carries ``error_code`` ``INVALID_REF``.
    """

    error_code = "INVALID_REF"


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


class QueryTooLongError(ValidationError):
    """A search query is longer than the fixed maximum length.

    Raised before any sanitizing or searching runs, on every surface, so the
    cost of preparing a query is bounded by the cap. A query is never silently
    truncated. Carries ``error_code`` ``QUERY_TOO_LONG``; REST maps it to 422.
    """

    error_code = "QUERY_TOO_LONG"


class ClipperBlockedHostError(PyriteError):
    """Raised when the web clipper refuses to fetch a URL because the
    resolved host is on the SSRF blocklist (loopback, link-local,
    RFC1918 private, reserved IPv4/IPv6 ranges) or because the URL uses
    a non-http(s) scheme.

    Carries an ``error_code`` attribute (``CLIPPER_BLOCKED_HOST``) so
    REST/MCP handlers can surface a stable identifier.
    """

    error_code = "CLIPPER_BLOCKED_HOST"
