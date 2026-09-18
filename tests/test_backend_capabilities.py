"""Tests for backend capability declarations (Tier A r1400 / Option B).

Locked design (commit 3777cb5):

- BackendCapability StrEnum with the 3 subsystems ENTITY, SEARCH and
  EMBEDDING, plus FILTERED_SEMANTIC (#56), a refinement of EMBEDDING
  rather than a fourth subsystem.
- Each dispatched method on the SearchBackend Protocol maps to a
  capability via `_METHOD_CAPABILITIES`.
- Backend classes declare ``capabilities: ClassVar[set[BackendCapability]]``.
- A backend dispatcher consults the declared set before calling each
  method; calls to methods whose capability isn't declared are skipped.
- A backend returning non-empty from an undeclared-capability method
  triggers a WARNING by default (warn-and-skip), raises BackendError
  under ``strict_backends=True``.

Mirrors the r1500 plugin Capability tests at
tests/test_plugin_integration.py::TestCapabilityEnum and friends.
"""

from __future__ import annotations


# =========================================================================
# Capability enum
# =========================================================================


class TestBackendCapabilityEnum:
    """The 3 subsystems of the locked design (decision #1), plus refinements.

    ENTITY, SEARCH and EMBEDDING are the subsystem split. FILTERED_SEMANTIC
    (#56) is a refinement of EMBEDDING — how *well* a backend implements
    ``search_semantic``, not whether it implements it. The headcount stays
    pinned so a new member is a deliberate edit here, with its kind stated.
    """

    def test_has_the_expected_members(self):
        from pyrite.storage.backends.capabilities import BackendCapability

        assert {c.name for c in BackendCapability} == {
            "ENTITY",
            "SEARCH",
            "EMBEDDING",
            "FILTERED_SEMANTIC",
        }

    def test_filtered_semantic_refines_embedding(self):
        """A backend claiming the refinement must claim the subsystem too.

        FILTERED_SEMANTIC says ``search_semantic`` honours the keyword leg's
        filters; a backend that cannot do semantic search at all must not
        claim it.
        """
        from pyrite.storage.backends.capabilities import BackendCapability
        from pyrite.storage.backends.postgres_backend import PostgresBackend
        from pyrite.storage.backends.sqlite_backend import SQLiteBackend

        for cls in (SQLiteBackend, PostgresBackend):
            caps = cls.capabilities
            assert BackendCapability.FILTERED_SEMANTIC in caps, cls.__name__
            assert BackendCapability.EMBEDDING in caps, cls.__name__

    def test_is_string_enum(self):
        """StrEnum so backends can declare {BackendCapability.ENTITY}
        and the dispatcher can compare by string in config-derived
        capability sets if needed."""
        from pyrite.storage.backends.capabilities import BackendCapability

        assert isinstance(BackendCapability.ENTITY, str)


# =========================================================================
# Method-to-capability map
# =========================================================================


class TestBackendMethodCapabilitiesMap:
    """`_METHOD_CAPABILITIES` maps each dispatched SearchBackend method
    to its BackendCapability. The map is the spec for "which capability
    authorizes calling which method"; future contributors adding a new
    dispatched method must add an entry here or a test fails."""

    def test_every_value_is_a_capability(self):
        from pyrite.storage.backends import capabilities as cap_mod
        from pyrite.storage.backends.capabilities import BackendCapability

        mapping = cap_mod._METHOD_CAPABILITIES
        assert isinstance(mapping, dict)
        assert len(mapping) >= 30, f"expected ~38 dispatched-method mappings; got {len(mapping)}"
        assert all(isinstance(v, BackendCapability) for v in mapping.values())

    def test_canonical_methods_in_each_capability(self):
        """Anchor each capability with its canonical methods per the
        ticket body's three-responsibility breakdown."""
        from pyrite.storage.backends import capabilities as cap_mod
        from pyrite.storage.backends.capabilities import BackendCapability

        m = cap_mod._METHOD_CAPABILITIES
        # ENTITY — CRUD
        assert m.get("upsert_entry") == BackendCapability.ENTITY
        assert m.get("get_entry") == BackendCapability.ENTITY
        assert m.get("delete_entry") == BackendCapability.ENTITY
        assert m.get("list_entries") == BackendCapability.ENTITY
        assert m.get("count_entries") == BackendCapability.ENTITY
        # SEARCH — keyword + tag + date variants
        assert m.get("search") == BackendCapability.SEARCH
        assert m.get("search_by_tag") == BackendCapability.SEARCH
        assert m.get("search_by_date_range") == BackendCapability.SEARCH
        # EMBEDDING — vectors
        assert m.get("upsert_embedding") == BackendCapability.EMBEDDING
        assert m.get("search_semantic") == BackendCapability.EMBEDDING
        assert m.get("has_embeddings") == BackendCapability.EMBEDDING
        assert m.get("embedding_stats") == BackendCapability.EMBEDDING


# =========================================================================
# Dispatch-skip helper
# =========================================================================


class TestBackendDispatchHelper:
    """`backend_declares(backend, method_name) -> bool` returns True if
    the backend's declared capability set covers the method's required
    capability. Used by the dispatch layer to skip calls a backend
    didn't claim.

    The locked design (decision #2) keeps two questions separate:
      - class attribute = "can in principle do X"
      - runtime is_available() = "is the dependency installed now"
    This helper handles ONLY the first question.
    """

    @staticmethod
    def _backend(capabilities_set):
        """Build a stub backend with explicit capabilities."""
        from typing import ClassVar

        class _StubBackend:
            capabilities: ClassVar[set] = capabilities_set

        return _StubBackend()

    def test_declared_capability_allows_method(self):
        from pyrite.storage.backends.capabilities import (
            BackendCapability,
            backend_declares,
        )

        backend = self._backend({BackendCapability.ENTITY})
        assert backend_declares(backend, "get_entry") is True

    def test_undeclared_capability_blocks_method(self):
        from pyrite.storage.backends.capabilities import (
            BackendCapability,
            backend_declares,
        )

        # ENTITY-only backend: search_semantic (EMBEDDING) is not allowed.
        backend = self._backend({BackendCapability.ENTITY})
        assert backend_declares(backend, "search_semantic") is False

    def test_missing_capabilities_attribute_defaults_to_empty_set(self):
        """A backend class without `capabilities` declared is treated
        as the empty set — every dispatch-gated method is skipped.
        Safe failure mode mirrors the r1500 plugin contract."""
        from pyrite.storage.backends.capabilities import backend_declares

        class _LegacyBackend:
            pass  # no `capabilities` attribute

        backend = _LegacyBackend()
        # `get_entry` is an ENTITY method; not declared -> blocked.
        assert backend_declares(backend, "get_entry") is False

    def test_method_not_in_map_is_treated_as_always_allowed(self):
        """Methods not in `_METHOD_CAPABILITIES` (e.g. `close` lifecycle
        or future ungated helpers) are allowed even with empty
        capabilities. Otherwise innocuous infrastructure calls would
        silently disappear."""
        from pyrite.storage.backends.capabilities import backend_declares

        class _LegacyBackend:
            pass

        backend = _LegacyBackend()
        # `close` is intentionally NOT in _METHOD_CAPABILITIES (it's a
        # lifecycle method, not a capability-gated dispatch target).
        assert backend_declares(backend, "close") is True


# =========================================================================
# In-tree backends declare correct capabilities (regression)
# =========================================================================


class TestInTreeBackendDeclarations:
    """Both in-tree backends (SQLite, Postgres) declare all 3
    capabilities since both implement the full Protocol today. The
    declaration is the structural-vs-implicit win documented in the
    locked design; dispatch-skip kicks in mostly for future read-only
    backends that opt into a subset.

    These tests guard against a future contributor accidentally
    dropping a capability from one of the backend classes.
    """

    def test_sqlite_backend_declares_all_three(self):
        from pyrite.storage.backends.capabilities import BackendCapability
        from pyrite.storage.backends.sqlite_backend import SQLiteBackend

        declared = getattr(SQLiteBackend, "capabilities", set())
        assert BackendCapability.ENTITY in declared
        assert BackendCapability.SEARCH in declared
        assert BackendCapability.EMBEDDING in declared

    def test_postgres_backend_declares_all_three(self):
        """If postgres deps aren't installed in this env, the import
        fails and the test skips — we still pin the contract for
        environments where postgres ships."""
        try:
            from pyrite.storage.backends.postgres_backend import PostgresBackend
        except ImportError:
            import pytest

            pytest.skip("PostgresBackend requires psycopg2; not installed")

        from pyrite.storage.backends.capabilities import BackendCapability

        declared = getattr(PostgresBackend, "capabilities", set())
        assert BackendCapability.ENTITY in declared
        assert BackendCapability.SEARCH in declared
        assert BackendCapability.EMBEDDING in declared


# =========================================================================
# Overlay — delegated capabilities (#56)
# =========================================================================


class TestOverlayCapabilities:
    """The overlay declares the intersection of its two halves.

    It is only as capable as its weaker half for anything it combines, so the
    intersection is the honest answer. FILTERED_SEMANTIC survives it because
    ``search_semantic`` delegates straight to main with every filter passed
    through, and both in-tree backends declare it — without this, a user on an
    overlay index would silently lose the semantic leg on every filtered
    search.
    """

    @staticmethod
    def _overlay(main_caps, diff_caps):
        from pyrite.storage.backends.overlay_backend import OverlaySearchBackend

        class _Half:
            def __init__(self, caps):
                self.capabilities = caps

        return OverlaySearchBackend(_Half(main_caps), _Half(diff_caps))

    def test_declares_filtered_semantic_when_both_halves_do(self):
        from pyrite.storage.backends.capabilities import BackendCapability

        caps = {BackendCapability.EMBEDDING, BackendCapability.FILTERED_SEMANTIC}
        assert BackendCapability.FILTERED_SEMANTIC in self._overlay(caps, caps).capabilities

    def test_drops_a_capability_a_half_lacks(self):
        from pyrite.storage.backends.capabilities import BackendCapability

        full = {BackendCapability.EMBEDDING, BackendCapability.FILTERED_SEMANTIC}
        overlay = self._overlay(full, {BackendCapability.EMBEDDING})
        assert BackendCapability.FILTERED_SEMANTIC not in overlay.capabilities
        assert BackendCapability.EMBEDDING in overlay.capabilities

    def test_a_half_that_declares_nothing_yields_nothing(self):
        """Safe failure mode, same as ``backend_declares``: undeclared is empty."""

        class _Bare:
            pass

        from pyrite.storage.backends.overlay_backend import OverlaySearchBackend

        assert OverlaySearchBackend(_Bare(), _Bare()).capabilities == set()
