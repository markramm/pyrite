"""MCP's ``_refusal`` reads the exception class's own code, and carries its
old code for one release in ``legacy_error_code`` (ADR-0037 theme 2,
maintainer decision 2026-09-25: "one code per exception, and REST's code
wins. For one release, MCP keeps emitting its current code in a
legacy_error_code field, then switches.").

Unit-level: ``_refusal`` takes an exception instance and returns a dict; no
app or dispatch needed.
"""

from pyrite.exceptions import (
    BrandingInvalidError,
    ConfigError,
    ConfigSaveRefusedError,
    EntryNotFoundError,
    FrontmatterError,
    KBNotFoundError,
    KBProtectedError,
    KBReadOnlyError,
    PluginError,
    PyriteError,
    QuerySyntaxError,
    QueryTooLongError,
    StorageBusyError,
    StorageError,
    TruncatedBodyError,
    ValidationError,
)
from pyrite.server.mcp_server import _refusal


class TestCodesThatChanged:
    """These four disagreed between REST and MCP before this theme (ADR-0037:
    'REST says ENTRY_NOT_FOUND / KB_NOT_FOUND / KB_READ_ONLY / VALIDATION_ERROR
    where MCP says NOT_FOUND / NOT_FOUND / READ_ONLY / VALIDATION_FAILED'), plus
    ConfigError (REST CONFIG_CONFLICT vs MCP CONFIG_ERROR, same disagreement
    shape though not named in that exact sentence). REST's code wins; MCP's old
    code moves to legacy_error_code.
    """

    def test_entry_not_found(self):
        out = _refusal(EntryNotFoundError("no entry here"))
        assert out["error_code"] == "ENTRY_NOT_FOUND"
        assert out["legacy_error_code"] == "NOT_FOUND"

    def test_kb_not_found(self):
        out = _refusal(KBNotFoundError("no kb here"))
        assert out["error_code"] == "KB_NOT_FOUND"
        assert out["legacy_error_code"] == "NOT_FOUND"

    def test_kb_read_only(self):
        out = _refusal(KBReadOnlyError("read-only"))
        assert out["error_code"] == "KB_READ_ONLY"
        assert out["legacy_error_code"] == "READ_ONLY"

    def test_base_validation_error(self):
        out = _refusal(ValidationError("bad field"))
        assert out["error_code"] == "VALIDATION_ERROR"
        assert out["legacy_error_code"] == "VALIDATION_FAILED"

    def test_base_config_error(self):
        out = _refusal(ConfigError("dup kb"))
        assert out["error_code"] == "CONFIG_CONFLICT"
        assert out["legacy_error_code"] == "CONFIG_ERROR"

    def test_frontmatter_error(self):
        """Never had its own error_code before this theme, so it inherited
        ValidationError's old literal (VALIDATION_FAILED) via normal
        attribute lookup -- not the domain table's isinstance walk. Its new
        class code (INVALID_FRONTMATTER) is REST's long-standing status-table
        entry for this specific case."""
        out = _refusal(FrontmatterError("bad yaml"))
        assert out["error_code"] == "INVALID_FRONTMATTER"
        assert out["legacy_error_code"] == "VALIDATION_FAILED"

    def test_truncated_body_error(self):
        out = _refusal(TruncatedBodyError("body_truncated marker on write"))
        assert out["error_code"] == "VALIDATION_ERROR"
        assert out["legacy_error_code"] == "VALIDATION_FAILED"

    def test_plugin_error(self):
        """Fell all the way to the REQUEST_REFUSED fallback before this
        theme: not in the old domain table, no error_code of its own."""
        out = _refusal(PluginError("missing sdk"))
        assert out["error_code"] == "PLUGIN_ERROR"
        assert out["legacy_error_code"] == "REQUEST_REFUSED"

    def test_storage_error(self):
        out = _refusal(StorageError("disk gone"))
        assert out["error_code"] == "STORAGE_ERROR"
        assert out["legacy_error_code"] == "REQUEST_REFUSED"
        assert out["retryable"] is False

    def test_storage_busy_error(self):
        out = _refusal(StorageBusyError("database is locked"))
        assert out["error_code"] == "STORAGE_ERROR"
        assert out["legacy_error_code"] == "REQUEST_REFUSED"
        assert out["retryable"] is True

    def test_config_save_refused_error(self):
        """ConfigSaveRefusedError used to answer MCP's CONFIG_ERROR (via the
        old domain table's isinstance match on its ConfigError parent); its
        new class code (CONFIG_SAVE_REFUSED) is its own, distinct from the
        base ConfigError's CONFIG_CONFLICT."""
        exc = ConfigSaveRefusedError("real path leaked", dropped=[])
        out = _refusal(exc)
        assert out["error_code"] == "CONFIG_SAVE_REFUSED"
        assert out["legacy_error_code"] == "CONFIG_ERROR"

    def test_base_pyrite_error(self):
        out = _refusal(PyriteError("generic domain error"))
        assert out["error_code"] == "INTERNAL_ERROR"
        assert out["legacy_error_code"] == "REQUEST_REFUSED"


class TestAccessDeniedGetsNoLegacyCode:
    """AccessDenied and its subclasses are new (ADR-0037 §3) -- never raised
    by any surface before this theme, so there is no old MCP behaviour to
    disagree with. legacy_error_code must not appear."""

    def test_not_authenticated(self):
        from pyrite.exceptions import NotAuthenticated

        out = _refusal(NotAuthenticated("no credential"))
        assert out["error_code"] == "UNAUTHENTICATED"
        assert "legacy_error_code" not in out

    def test_forbidden(self):
        from pyrite.exceptions import Forbidden

        out = _refusal(Forbidden("lacks the action"))
        assert out["error_code"] == "FORBIDDEN"
        assert "legacy_error_code" not in out


class TestCodesThatAlreadyAgreed:
    """A class whose REST and MCP codes always matched gets no
    legacy_error_code at all -- there is nothing "legacy" to report, and
    adding the key unconditionally would be a new key on every response,
    not just the ones the maintainer's decision is about.
    """

    def test_kb_protected_no_legacy_code(self):
        out = _refusal(KBProtectedError("kb is protected"))
        assert out["error_code"] == "KB_PROTECTED"
        assert "legacy_error_code" not in out

    def test_query_syntax_no_legacy_code(self):
        out = _refusal(QuerySyntaxError("bad query"))
        assert out["error_code"] == "QUERY_SYNTAX"
        assert "legacy_error_code" not in out

    def test_query_too_long_no_legacy_code(self):
        out = _refusal(QueryTooLongError("too long"))
        assert out["error_code"] == "QUERY_TOO_LONG"
        assert "legacy_error_code" not in out

    def test_branding_invalid_no_legacy_code(self):
        out = _refusal(BrandingInvalidError("bad branding.yaml"))
        assert out["error_code"] == "BRANDING_INVALID"
        assert "legacy_error_code" not in out


class TestValidationSubclassesUnaffected:
    """Subclasses that already carried their own code before this theme
    (#378's family) are untouched -- same code, no legacy_error_code, since
    REST and MCP never disagreed about them."""

    def test_undeclared_type_error(self):
        from pyrite.exceptions import UndeclaredTypeError

        out = _refusal(UndeclaredTypeError("not declared", declared_types=["note"]))
        assert out["error_code"] == "UNDECLARED_TYPE"
        assert "legacy_error_code" not in out

    def test_entry_exists_error(self):
        from pyrite.exceptions import EntryExistsError

        out = _refusal(EntryExistsError("already exists"))
        assert out["error_code"] == "ENTRY_EXISTS"
        assert "legacy_error_code" not in out
