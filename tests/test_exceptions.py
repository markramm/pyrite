"""Tests for custom exception hierarchy and _run_hooks propagation."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pyrite.exceptions import (
    ConfigError,
    EntryNotFoundError,
    KBNotFoundError,
    KBReadOnlyError,
    PluginError,
    PyriteError,
    StorageError,
    ValidationError,
)


class TestExceptionHierarchy:
    """All custom exceptions inherit from PyriteError."""

    def test_pyrite_error_is_base(self):
        assert issubclass(PyriteError, Exception)

    @pytest.mark.parametrize(
        "exc_class",
        [
            EntryNotFoundError,
            KBNotFoundError,
            KBReadOnlyError,
            ValidationError,
            PluginError,
            StorageError,
            ConfigError,
        ],
    )
    def test_subclass_of_pyrite_error(self, exc_class):
        assert issubclass(exc_class, PyriteError)

    @pytest.mark.parametrize(
        "exc_class",
        [
            EntryNotFoundError,
            KBNotFoundError,
            KBReadOnlyError,
            ValidationError,
            PluginError,
            StorageError,
            ConfigError,
        ],
    )
    def test_catchable_as_pyrite_error(self, exc_class):
        with pytest.raises(PyriteError):
            raise exc_class("test message")

    def test_exception_message(self):
        err = EntryNotFoundError("Entry not found: foo")
        assert str(err) == "Entry not found: foo"


class TestRunHooksPropagation:
    """_run_hooks lets PyriteError propagate but catches other exceptions.

    #379: HookRunner owns both core- and plugin-hook dispatch, and it looks
    plugin hooks up via the registry's get_hooks_for_kb (a pure lookup, not
    a runner -- run_hooks_for_kb no longer exists). So these mock the hook
    *callable* the lookup returns, the way a real plugin hook would raise or
    return a value, rather than mocking a runner method directly on the
    registry.
    """

    def _svc_with_plugin_hook(self, hook_fn):
        """A KBService whose plugin registry has one before_save hook."""
        from pyrite.services.kb_service import KBService

        mock_registry = MagicMock()
        mock_registry.get_hooks_for_kb.return_value = {"before_save": [hook_fn]}
        # KBService.__init__ resolves get_registry() once at construction
        # time (#379), so the patch must be active for the constructor call.
        with patch("pyrite.plugins.get_registry", return_value=mock_registry):
            return KBService(config=MagicMock(), db=MagicMock())

    def test_pyrite_error_propagates(self):
        """PyriteError from hooks should propagate through _run_hooks."""
        from pyrite.models.core_types import NoteEntry

        def raising_hook(entry, ctx):
            raise KBReadOnlyError("read-only")

        svc = self._svc_with_plugin_hook(raising_hook)
        entry = NoteEntry(id="test", title="Test")
        with pytest.raises(KBReadOnlyError):
            svc._run_hooks("before_save", entry, {})

    def test_permission_error_propagated_in_before_hooks(self):
        """PermissionError in before_save hooks should propagate (hook atomicity)."""
        from pyrite.models.core_types import NoteEntry

        def raising_hook(entry, ctx):
            raise PermissionError("denied")

        svc = self._svc_with_plugin_hook(raising_hook)
        entry = NoteEntry(id="test", title="Test")
        with pytest.raises(PermissionError, match="denied"):
            svc._run_hooks("before_save", entry, {})

    def test_generic_exception_propagated_in_before_hooks(self):
        """Generic exceptions in before_save hooks should propagate (hook atomicity)."""
        from pyrite.models.core_types import NoteEntry

        def raising_hook(entry, ctx):
            raise RuntimeError("boom")

        svc = self._svc_with_plugin_hook(raising_hook)
        entry = NoteEntry(id="test", title="Test")
        with pytest.raises(RuntimeError, match="boom"):
            svc._run_hooks("before_save", entry, {})

    def test_successful_hook_returns_result(self):
        """Successful hooks return the modified entry."""
        from pyrite.models.core_types import NoteEntry

        modified = NoteEntry(id="modified", title="Modified")

        def replacing_hook(entry, ctx):
            return modified

        svc = self._svc_with_plugin_hook(replacing_hook)
        entry = NoteEntry(id="test", title="Test")
        result = svc._run_hooks("before_save", entry, {})
        assert result is modified


class TestServiceExceptionTypes:
    """KBService methods raise the correct exception types."""

    def test_create_entry_kb_not_found(self):
        from pyrite.config import PyriteConfig, Settings
        from pyrite.services.kb_service import KBService
        from pyrite.storage.database import PyriteDB

        with tempfile.TemporaryDirectory() as d:
            config = PyriteConfig(
                knowledge_bases=[],
                settings=Settings(index_path=Path(d) / "test.db"),
            )
            db = PyriteDB(config.settings.index_path)
            try:
                svc = KBService(config, db)
                with pytest.raises(KBNotFoundError):
                    svc.create_entry("nonexistent", "id", "title", "note")
            finally:
                db.close()

    def test_update_entry_kb_not_found(self):
        from pyrite.config import PyriteConfig, Settings
        from pyrite.services.kb_service import KBService
        from pyrite.storage.database import PyriteDB

        with tempfile.TemporaryDirectory() as d:
            config = PyriteConfig(
                knowledge_bases=[],
                settings=Settings(index_path=Path(d) / "test.db"),
            )
            db = PyriteDB(config.settings.index_path)
            try:
                svc = KBService(config, db)
                with pytest.raises(KBNotFoundError):
                    svc.update_entry("id", "nonexistent", title="new")
            finally:
                db.close()

    def test_delete_entry_kb_not_found(self):
        from pyrite.config import PyriteConfig, Settings
        from pyrite.services.kb_service import KBService
        from pyrite.storage.database import PyriteDB

        with tempfile.TemporaryDirectory() as d:
            config = PyriteConfig(
                knowledge_bases=[],
                settings=Settings(index_path=Path(d) / "test.db"),
            )
            db = PyriteDB(config.settings.index_path)
            try:
                svc = KBService(config, db)
                with pytest.raises(KBNotFoundError):
                    svc.delete_entry("id", "nonexistent")
            finally:
                db.close()

    def test_create_entry_read_only(self):
        from pyrite.config import KBConfig, KBType, PyriteConfig, Settings
        from pyrite.services.kb_service import KBService
        from pyrite.storage.database import PyriteDB

        with tempfile.TemporaryDirectory() as d:
            kb_path = Path(d) / "ro"
            kb_path.mkdir()
            config = PyriteConfig(
                knowledge_bases=[
                    KBConfig(name="ro", path=kb_path, kb_type=KBType.RESEARCH, read_only=True),
                ],
                settings=Settings(index_path=Path(d) / "test.db"),
            )
            db = PyriteDB(config.settings.index_path)
            try:
                svc = KBService(config, db)
                with pytest.raises(KBReadOnlyError):
                    svc.create_entry("ro", "id", "title", "note")
            finally:
                db.close()
