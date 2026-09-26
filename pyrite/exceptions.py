"""
Pyrite Exception Hierarchy

Typed exceptions for distinct error conditions, replacing generic ValueError/PermissionError.

ADR-0037 theme 2: **codes live on exception classes.** Every ``PyriteError``
subclass carries a class-level ``error_code`` -- a plain string, inherited
from its parent unless it narrows the code itself -- so a transport maps a
code from the class alone, with no external table keyed by type to keep in
sync. Where REST and MCP used to disagree (``NOT_FOUND`` vs
``ENTRY_NOT_FOUND``/``KB_NOT_FOUND``, ``READ_ONLY`` vs ``KB_READ_ONLY``,
``VALIDATION_FAILED`` vs ``VALIDATION_ERROR``, ``CONFIG_ERROR`` vs
``CONFIG_CONFLICT``), the maintainer's decision (2026-09-25) is that REST's
more specific code is the one on the class; MCP keeps emitting its old code
for one release in a transitional ``legacy_error_code`` field it builds
itself (see ``server/mcp_server._refusal``), never on the class.

**Messages are public or private by construction.** ``public_message`` is
``None`` by default -- every transport's
``getattr(exc, "public_message", None) or str(exc)`` then falls back to
``str(exc)``, which every refusal family here (not-found, read-only,
validation, query errors) writes to be safe to show. A class that *can*
carry server-side detail in ``str(exc)`` (a real filesystem path, a plugin's
internals) sets a fixed, safe ``public_message`` instead, e.g.
``ConfigSaveRefusedError`` (#377) and ``BrandingInvalidError`` (#445, #408).
"""


class PyriteError(Exception):
    """Base exception for all Pyrite errors.

    ``error_code`` is the fallback for any domain error that reaches a
    transport without a more specific class -- REST's central handler and
    MCP's ``_refusal`` both map an unrecognised ``PyriteError`` to
    ``INTERNAL_ERROR`` today; this makes that the same string as a class
    attribute instead of a magic literal duplicated at each site.
    """

    error_code: str = "INTERNAL_ERROR"
    #: Safe to show over HTTP/MCP/CLI. ``None`` means "str(exc) is safe" --
    #: see the module docstring. A subclass whose own text can carry
    #: server-side detail (a path, a traceback fragment) sets a fixed string.
    public_message: str | None = None


class EntryNotFoundError(PyriteError):
    """Raised when an entry cannot be found."""

    error_code = "ENTRY_NOT_FOUND"


class KBNotFoundError(PyriteError):
    """Raised when a knowledge base cannot be found."""

    error_code = "KB_NOT_FOUND"


class KBReadOnlyError(PyriteError):
    """Raised when attempting to write to a read-only KB."""

    error_code = "KB_READ_ONLY"


class ValidationError(PyriteError):
    """Raised when entry data fails validation.

    Every write refusal is a ValidationError, and carries a stable
    ``error_code`` that REST, MCP and the CLI all report unchanged (#378).
    Subclasses below narrow the code; the base code is ``VALIDATION_ERROR``,
    REST's historical spelling (ADR-0037 theme 2: REST's code wins -- MCP
    used to say ``VALIDATION_FAILED`` for this base case, and now carries
    that old spelling in ``legacy_error_code`` for one release).
    ``suggestion`` is an optional surface-neutral fix hint.
    """

    error_code = "VALIDATION_ERROR"
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
    """A caller-supplied git remote, branch or commit id is not acceptable.

    A remote must be one of the repository's configured remotes (never a URL
    or a path); a branch must be a valid branch name that does not begin
    with "-"; a commit id must be 4-64 hex characters (checked before git
    runs) and must name a commit, not a tree or blob (an annotated tag peels
    to its commit). Carries ``error_code`` ``INVALID_REF``.
    """

    error_code = "INVALID_REF"


class FrontmatterError(ValidationError):
    """Raised when YAML frontmatter is malformed or not a mapping.

    A ValidationError subclass so existing ``except ValidationError`` handlers
    continue to catch it, while callers that care specifically about parse
    failures can catch this narrower type. Its own code, not the base
    ``VALIDATION_ERROR``: REST has always answered 422 ``INVALID_FRONTMATTER``
    for this specific case.
    """

    error_code = "INVALID_FRONTMATTER"


class PluginError(PyriteError):
    """Raised when a plugin operation fails."""

    error_code = "PLUGIN_ERROR"


class StorageError(PyriteError):
    """Raised when a storage operation fails.

    ``retryable`` says whether the same call could succeed if made again. It is
    False here: schema drift, a missing table and a corrupt file fail the same
    way every time. Only ``StorageBusyError`` sets it.
    """

    error_code = "STORAGE_ERROR"
    retryable: bool = False


class StorageBusyError(StorageError):
    """A transient storage fault: the database was locked or busy (#431).

    The one ``StorageError`` a caller may retry: another connection held a
    lock, and the same call can succeed once it is released. REST still maps
    it to ``STORAGE_ERROR`` 500; MCP reports it with ``retryable: true``.
    """

    retryable = True


class KBProtectedError(PyriteError):
    """Raised when attempting to modify/remove a config-protected KB."""

    error_code = "KB_PROTECTED"


class ConfigError(PyriteError):
    """Raised when configuration is invalid."""

    error_code = "CONFIG_CONFLICT"


class BrandingInvalidError(PyriteError):
    """Raised when ``branding.yaml`` exists but cannot be parsed, or it or
    one of its nested mappings (``meta``, ``mcp``) is not a mapping (#408).

    ``str()`` names the real branding.yaml path and the parser's own text --
    useful in the server log, not safe to return over HTTP or MCP: every
    caller of ``BrandingService`` runs on an anonymous, always-public path
    (``/config/branding``, ``/sitemap.xml``, ``/robots.txt``, the MCP
    ``research_topic`` prompt), not just the admin-only render endpoint
    (#445's cold read). ``public_message`` is safe to show; it names neither.
    """

    error_code = "BRANDING_INVALID"
    public_message = (
        "The server's branding configuration is invalid and could not be loaded. "
        "An administrator needs to fix branding.yaml; the server log names the "
        "file and the problem."
    )


class ConfigSaveRefusedError(ConfigError):
    """A config save was refused: it would drop KBs the caller did not name,
    or the file on disk could not be read to check (#377).

    ``str()`` is the operator's message: it names the real config file and the
    KBs. ``public_message`` is safe to return over HTTP.
    """

    error_code = "CONFIG_SAVE_REFUSED"
    public_message = (
        "The configuration was not saved: the config file changed since the server "
        "loaded it. Restart the server so it reads the current file, then re-run the "
        "request; the server log names the file and the knowledge bases."
    )

    def __init__(self, message: str, *, config_file=None, dropped: list[str] | None = None):
        super().__init__(message)
        self.config_file = config_file
        self.dropped = list(dropped or [])


class ConfigFileUnreadableError(ConfigSaveRefusedError):
    """The config file on disk could not be read as a registry (unparseable,
    not a mapping, an entry with no name), so a save cannot check what it
    would drop. Restarting does not help -- the server would fail to load the
    same file -- so the advice is to fix or move it.
    """

    public_message = (
        "The configuration was not saved: the config file on the server could not "
        "be read. An administrator needs to fix or move config.yaml; the server log "
        "names the file and the problem."
    )


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


class LastAdminError(ValidationError):
    """AuthService.set_role refused to demote the last global admin (#416).

    A ValidationError subclass so any generic ``except ValidationError``
    handler still catches it, but with its own ``error_code`` so a route
    that wants to label *this specific* refusal (409 LAST_ADMIN) does not
    also mislabel every other validation failure from the same call the
    same way.
    """

    error_code = "LAST_ADMIN"


class AccessDenied(PyriteError):  # noqa: N818 -- named "AccessDenied" verbatim by ADR-0037 §3
    """ADR-0037 §3: a denial is an exception in the same hierarchy, not a
    bespoke ``HTTPException`` or MCP refusal dict a surface builds by hand.

    Not raised by any surface yet -- theme 1 (the policy point, #383) and
    theme 3b/3c (REST's write and instance routes) are what raises these.
    This theme only needs the classes and their codes to exist, so those
    later themes, and this theme's transports, have something to map.

    A concealment denial is deliberately **not** a subclass here: an
    unreadable KB raises the not-found exception itself
    (``KBNotFoundError``/``EntryNotFoundError``), so no transport can tell a
    private KB apart from a missing one, even by accident (ADR-0037 §4).
    """


class NotAuthenticated(AccessDenied):
    """No principal at all -- the caller sent no credential, or an invalid
    one. REST's 401; MCP and the CLI report the same code.
    """

    error_code = "UNAUTHENTICATED"


class Forbidden(AccessDenied):
    """A principal exists but lacks the action on the resource. REST's 403;
    MCP and the CLI report the same code.
    """

    error_code = "FORBIDDEN"
