"""Tests for HookRunner — the extracted hook orchestration peer service.

Background: KBService used to host hook orchestration as a static method
(_run_hooks) plus a module-level _CORE_HOOKS dict. The behavior contract was
informally documented in the docstring:

- before_save / before_delete: hooks may raise; raise aborts persistence and
  propagates to the caller (no swallowing).
- after_save / after_delete: hook exceptions are logged but swallowed; the
  operation is still considered successful (the entry is already committed).

These tests pin the contract before we move the responsibility into
pyrite/services/hook_runner.py so the move is structurally safe.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from pyrite.exceptions import ValidationError


class TestHookRunnerExists:
    """The first RED: assert HookRunner is importable from the new module."""

    def test_hook_runner_module_importable(self):
        import pyrite.services.hook_runner  # noqa: F401

    def test_hook_runner_class_importable(self):
        from pyrite.services.hook_runner import HookRunner  # noqa: F401


class TestHookRunnerInterface:
    """Pin the public interface from the ticket."""

    def test_has_register_core_hook(self):
        from pyrite.services.hook_runner import HookRunner

        assert hasattr(HookRunner, "register_core_hook")

    def test_has_before_after_dispatch_methods(self):
        from pyrite.services.hook_runner import HookRunner

        for name in (
            "run_before_save",
            "run_after_save",
            "run_before_delete",
            "run_after_delete",
        ):
            assert hasattr(HookRunner, name), f"HookRunner missing {name}"


class TestBeforeSaveContract:
    """before_* hooks must raise; failures abort the operation."""

    def test_before_save_propagates_validation_error(self):
        from pyrite.services.hook_runner import HookRunner

        def bad_hook(entry, ctx):
            raise ValidationError("nope")

        runner = HookRunner()
        runner.register_core_hook("before_save", bad_hook)

        with pytest.raises(ValidationError, match="nope"):
            runner.run_before_save(MagicMock(), {})

    def test_before_save_propagates_arbitrary_exception(self):
        """Any exception in a before_* hook aborts the operation, not just
        domain ones — this is what makes hooks usable for atomic guards."""
        from pyrite.services.hook_runner import HookRunner

        def crashy(entry, ctx):
            raise RuntimeError("kaboom")

        runner = HookRunner()
        runner.register_core_hook("before_save", crashy)

        with pytest.raises(RuntimeError, match="kaboom"):
            runner.run_before_save(MagicMock(), {})

    def test_before_save_returns_entry_when_hooks_succeed(self):
        from pyrite.services.hook_runner import HookRunner

        sentinel = MagicMock(name="entry-sentinel")

        def passthrough(entry, ctx):
            return entry

        runner = HookRunner()
        runner.register_core_hook("before_save", passthrough)

        assert runner.run_before_save(sentinel, {}) is sentinel

    def test_before_save_hook_can_replace_entry(self):
        """If a hook returns a different entry, the runner uses it. This is
        the existing contract — hooks that mutate-by-returning."""
        from pyrite.services.hook_runner import HookRunner

        original = MagicMock(name="original")
        replacement = MagicMock(name="replacement")

        def swap(entry, ctx):
            return replacement

        runner = HookRunner()
        runner.register_core_hook("before_save", swap)

        assert runner.run_before_save(original, {}) is replacement


class TestAfterSaveContract:
    """after_* hooks must swallow + log. Operation is already committed."""

    def test_after_save_swallows_exception(self):
        from pyrite.services.hook_runner import HookRunner

        def crashy(entry, ctx):
            raise RuntimeError("post-save side effect blew up")

        runner = HookRunner()
        runner.register_core_hook("after_save", crashy)

        # Must NOT raise — the entry is already persisted; bubbling would
        # surface a "save failed" error to a caller whose save actually
        # succeeded.
        entry = MagicMock()
        result = runner.run_after_save(entry, {})
        assert result is entry  # entry is returned unchanged

    def test_after_save_logs_failure_at_warning_or_higher(self, caplog):
        import logging

        from pyrite.services.hook_runner import HookRunner

        def crashy(entry, ctx):
            raise RuntimeError("post-save blew up")

        runner = HookRunner()
        runner.register_core_hook("after_save", crashy)

        with caplog.at_level(logging.WARNING, logger="pyrite.services.hook_runner"):
            runner.run_after_save(MagicMock(), {})

        # The swallow-but-log contract: silent failures are the bug we're
        # avoiding.
        assert any(
            "post-save blew up" in rec.getMessage() or rec.levelno >= logging.WARNING
            for rec in caplog.records
        )

    def test_after_save_continues_subsequent_hooks_on_failure(self):
        """One failing after_save hook must NOT prevent later ones from running.
        This is the after_save contract: the operation is committed; each hook
        is its own side effect; isolation between them matters."""
        from pyrite.services.hook_runner import HookRunner

        ran = []

        def crashy(entry, ctx):
            ran.append("crashy")
            raise RuntimeError("boom")

        def benign(entry, ctx):
            ran.append("benign")
            return entry

        runner = HookRunner()
        runner.register_core_hook("after_save", crashy)
        runner.register_core_hook("after_save", benign)

        runner.run_after_save(MagicMock(), {})

        assert ran == ["crashy", "benign"]


class TestDeleteHookContract:
    """Same shape as save: before raises, after swallows."""

    def test_before_delete_propagates(self):
        from pyrite.services.hook_runner import HookRunner

        def bad(entry, ctx):
            raise ValidationError("cannot delete")

        runner = HookRunner()
        runner.register_core_hook("before_delete", bad)

        with pytest.raises(ValidationError):
            runner.run_before_delete(MagicMock(), {})

    def test_after_delete_swallows(self):
        from pyrite.services.hook_runner import HookRunner

        def crashy(entry, ctx):
            raise RuntimeError("cleanup failed")

        runner = HookRunner()
        runner.register_core_hook("after_delete", crashy)

        runner.run_after_delete(MagicMock(), {})  # must not raise


class TestKBServiceWiring:
    """Step 2 of the extraction: KBService delegates to a HookRunner instance.

    These tests pin the structural wiring (KBService owns a HookRunner) and the
    behavioral equivalence (the existing core hooks — task validation and
    parent rollup — are registered on the runner KBService actually uses). They
    do NOT re-test hook semantics (covered above); they assert the wiring is
    in place.
    """

    def test_kb_service_has_hook_runner_attribute(self):
        """KBService instances expose a `hook_runner` attribute holding a
        HookRunner instance — not None, not a static class."""
        from unittest.mock import MagicMock

        from pyrite.services.hook_runner import HookRunner
        from pyrite.services.kb_service import KBService

        svc = KBService(config=MagicMock(), db=MagicMock())
        assert isinstance(svc.hook_runner, HookRunner)

    def test_core_hooks_registered_on_runner(self):
        """The two core hooks (task validation and parent rollup) must be
        registered on the runner KBService owns. Step 3 will move them out of
        kb_service.py, but step 2 keeps the behavior — the runner must carry
        them either way."""
        from unittest.mock import MagicMock

        from pyrite.services.kb_service import KBService

        svc = KBService(config=MagicMock(), db=MagicMock())

        before_save = svc.hook_runner.core_hooks("before_save")
        after_save = svc.hook_runner.core_hooks("after_save")

        # before_save must include task transition validation; after_save
        # must include the parent rollup. Check by function name to keep the
        # assertion robust against the later move into task_service.
        before_names = {getattr(fn, "__name__", "") for fn in before_save}
        after_names = {getattr(fn, "__name__", "") for fn in after_save}

        assert "_task_validate_transition" in before_names, (
            f"expected _task_validate_transition in before_save hooks, got {before_names}"
        )
        assert "_parent_rollup" in after_names, (
            f"expected _parent_rollup in after_save hooks, got {after_names}"
        )

    def test_kb_service_core_dispatch_goes_through_runner(self):
        """KBService's _run_hooks must delegate core-hook dispatch to
        self.hook_runner. A hook registered on the runner via
        register_core_hook must fire when KBService runs its hooks.

        This pins step 2's structural change: even though _run_hooks survives
        as a thin instance method, the core-dispatch loop has moved out of
        KBService and into HookRunner.
        """
        from unittest.mock import MagicMock

        from pyrite.services.kb_service import KBService

        svc = KBService(config=MagicMock(), db=MagicMock())

        fired: list[str] = []

        def probe(entry, ctx):
            fired.append("probe-ran")
            return entry

        svc.hook_runner.register_core_hook("before_save", probe)

        # Run hooks via KBService's own dispatch — the probe must fire,
        # proving the dispatch went through the runner.
        svc._run_hooks("before_save", MagicMock(), {})
        assert fired == ["probe-ran"]
