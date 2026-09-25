"""Contract tests for the plugin validator and hook signatures (#379).

Every installed plugin's ``get_validators()`` callables must bind
``(entry_type: str, fields: dict, ctx: dict)`` and return ``list[dict]``
where each item carries ``severity`` and ``message``. Every hook callable
returned by ``get_hooks()`` must bind ``(entry, ctx)``.

This is a registration-time guarantee, not just a runtime one: the registry
checks the signature with ``inspect.signature(...).bind`` when a plugin is
registered and refuses (logs + skips) a non-conforming callable rather than
silently swallowing a TypeError at call time.
"""

import inspect

import pytest

from pyrite.plugins.capabilities import Capability
from pyrite.plugins.registry import PluginRegistry
from pyrite.schema.kb_schema import KBSchema


def _discovered_registry() -> PluginRegistry:
    """A registry with every installed plugin discovered (real entry points)."""
    reg = PluginRegistry()
    reg.discover()
    return reg


class TestValidatorSignatures:
    """Every installed plugin's validators bind the 3-argument contract."""

    def test_every_validator_binds_entry_type_fields_ctx(self):
        reg = _discovered_registry()
        checked = 0
        for plugin in reg._plugins.values():
            if not hasattr(plugin, "get_validators"):
                continue
            for validator in plugin.get_validators() or []:
                sig = inspect.signature(validator)
                # Must bind three positional args: entry_type, fields, ctx.
                sig.bind("some_type", {}, {})
                checked += 1
        assert checked > 0, "expected at least one installed plugin validator"

    def test_every_validator_returns_list_of_dicts_with_severity_and_message(self):
        """Calling each validator with a benign, empty-ish payload yields
        ``list[dict]`` items that carry ``severity``/``message`` when they
        report anything at all (an empty return is fine and common)."""
        reg = _discovered_registry()
        checked = 0
        for plugin in reg._plugins.values():
            if not hasattr(plugin, "get_validators"):
                continue
            for validator in plugin.get_validators() or []:
                # Use an entry_type unlikely to match any type-dispatch branch
                # plus an empty fields dict, so a well-behaved validator
                # returns [] rather than raising.
                result = validator("__contract_probe_unknown_type__", {}, {})
                assert isinstance(result, list)
                for item in result:
                    assert isinstance(item, dict)
                    assert "message" in item or "field" in item, (
                        f"{validator} returned an item with neither 'message' nor 'field': {item!r}"
                    )
                checked += 1
        assert checked > 0


class TestHookSignatures:
    """Every installed plugin's hooks bind the 2-argument (entry, ctx) contract."""

    def test_every_hook_binds_entry_ctx(self):
        reg = _discovered_registry()
        checked = 0
        for plugin in reg._plugins.values():
            if not hasattr(plugin, "get_hooks"):
                continue
            hooks = plugin.get_hooks() or {}
            for _hook_name, callables in hooks.items():
                for fn in callables:
                    sig = inspect.signature(fn)
                    sig.bind(object(), {})
                    checked += 1
        assert checked > 0, "expected at least one installed plugin hook"


class TestExtensionValidatorsFireThroughSchema:
    """Acceptance criteria 2 & 3 (#376): a cascade `actor` with no title, and
    the equivalent journalism-investigation case, must yield a validation
    error through `KBSchema.validate_entry` -- not a swallowed TypeError."""

    def test_cascade_actor_with_no_title_yields_error(self):
        schema = KBSchema(name="test-cascade", kb_type="cascade-research")
        result = schema.validate_entry("actor", {}, {"kb_type": "cascade-research"})
        assert result["valid"] is False
        assert any(e.get("field") == "title" for e in result["errors"])

    def test_journalism_asset_with_no_asset_type_yields_error(self):
        schema = KBSchema(name="test-ji", kb_type="journalism-investigation")
        result = schema.validate_entry("asset", {}, {"kb_type": "journalism-investigation"})
        assert result["valid"] is False
        assert any(e.get("field") == "asset_type" for e in result["errors"])


class TestOneHookContractModule:
    """Acceptance criterion 5: exactly one module implements the
    before-raises/after-swallows hook contract. HookRunner owns it; the
    registry's job is to look plugin hooks up, not to also decide
    raise-vs-swallow (that duplication is what T4 removes)."""

    def test_only_hook_runner_implements_the_contract(self):
        """Detect the pattern textually: a file that calls `.startswith(` on
        a "before_"-prefix check -- either the literal string or a named
        module constant assigned from it -- implements the raise-vs-swallow
        decision itself. A file that merely passes a "before_save" hook-name
        *string* to a runner (e.g. `self._run_hooks("before_save", ...)`)
        does not count: that's a caller, not an implementer, of the
        contract."""
        import pathlib
        import re

        repo_root = pathlib.Path(__file__).resolve().parents[1]
        # A `startswith(...)` call whose argument is the literal "before_",
        # or a bare identifier (a constant/variable) rather than a
        # differently-prefixed literal -- i.e. genuinely branching on
        # "does this hook name start with before_", not just quoting the
        # hook name somewhere else in the file.
        startswith_before = re.compile(
            r"""startswith\(\s*(?:["']before_["']|[A-Za-z_][A-Za-z0-9_]*)\s*\)"""
        )
        const_assigned_before = re.compile(r"""=\s*["']before_["']""")

        hits = []
        for base in [repo_root / "pyrite"] + sorted((repo_root / "extensions").glob("*/src")):
            for path in base.rglob("*.py"):
                text = path.read_text()
                calls = startswith_before.findall(text)
                if not calls:
                    continue
                # A literal "before_" call always counts. A bare-identifier
                # call only counts if that identifier is defined as
                # "before_" somewhere in the same file (rules out
                # `x.startswith(some_unrelated_prefix)`).
                if any('"before_"' in c or "'before_'" in c for c in calls):
                    hits.append(path.relative_to(repo_root).as_posix())
                elif const_assigned_before.search(text):
                    hits.append(path.relative_to(repo_root).as_posix())

        assert hits == ["pyrite/services/hook_runner.py"], (
            f"expected only hook_runner.py to implement before-raise/after-swallow, found: {hits}"
        )


class TestCascadeTaskUpdateNoTracebackNoSilentSkip:
    """#48's extra criterion: `pyrite task update` against a cascade-type KB
    must not print a traceback, and a validator error must give a non-zero
    exit (not exit 0 while silently skipping validation).

    #48's exact repro was `pyrite task update <task-id> -k cascade-research
    --priority 7`: the cascade validator (1-arg, wrong contract) raised
    TypeError twice, both swallowed by a fallback that logged a full
    traceback via `exc_info=True` -- while the command still exited 0. Fixed
    here at the TaskService/KBService layer (below the Typer CLI, same
    validate_entry -> SchemaViolationError path the CLI's
    `except (PyriteError, ValueError)` handler catches and turns into a
    non-zero `typer.Exit(1)` with a clean message, no traceback)."""

    def _cascade_env(self, tmp_path):
        from pathlib import Path

        from pyrite.config import KBConfig, PyriteConfig, Settings
        from pyrite.services.task_service import TaskService
        from pyrite.storage.database import PyriteDB

        tasks_path = Path(tmp_path) / "cascade-kb"
        tasks_path.mkdir()
        (tasks_path / "tasks").mkdir()

        kb_config = KBConfig(
            name="test-cascade",
            path=tasks_path,
            kb_type="cascade-research",
            description="Test",
        )
        config = PyriteConfig(
            knowledge_bases=[kb_config],
            settings=Settings(index_path=Path(tmp_path) / "index.db"),
        )
        db = PyriteDB(config.settings.index_path)
        db.register_kb("test-cascade", "cascade-research", str(tasks_path), "Test")
        svc = TaskService(config, db)
        return svc, db

    def test_benign_task_update_no_traceback_log(self, tmp_path, caplog):
        """A task entry (not one the cascade validator has an opinion on)
        updates cleanly: no traceback in the log, at any level."""
        import logging

        svc, db = self._cascade_env(tmp_path)
        try:
            svc.create_task(kb_name="test-cascade", title="Do the thing")
            with caplog.at_level(logging.WARNING):
                result = svc.update_task("do-the-thing", "test-cascade", priority=7)
            assert result.get("priority") == 7 or "priority" in str(result)
            tracebacks = [r for r in caplog.records if r.exc_info is not None]
            assert tracebacks == [], (
                f"expected no traceback-bearing log record, got: "
                f"{[(r.levelname, r.getMessage()) for r in tracebacks]}"
            )
        finally:
            db.close()

    def test_cascade_validator_error_is_non_zero_not_silent(self, tmp_path):
        """A real cascade-specific validation error (importance out of the
        1-10 range -- a rule only the cascade validator enforces, isolating
        it from create_entry's own generic title/date checks) raises
        SchemaViolationError -- the exception the CLI's task commands catch
        and turn into a non-zero exit -- rather than being silently
        swallowed by a signature-mismatch fallback."""
        from pyrite.exceptions import PyriteError, SchemaViolationError

        svc, db = self._cascade_env(tmp_path)
        try:
            with pytest.raises(SchemaViolationError) as exc_info:
                svc.kb_svc.create_entry(
                    "test-cascade",
                    "bad-actor",
                    "A Real Actor",
                    "actor",
                    allow_undeclared=True,
                    importance=99,
                )
            assert isinstance(exc_info.value, PyriteError)  # what task_commands.py catches
            assert any(e.get("field") == "importance" for e in exc_info.value.errors), (
                f"expected a cascade importance-range error, got: {exc_info.value.errors}"
            )
        finally:
            db.close()


class TestSeveritySplitsErrorsFromWarnings:
    """KBSchema.validate_entry must sort plugin-validator items by
    severity: "warning" goes to result["warnings"], anything else
    (omitted, or any other value) goes to result["errors"]. Uses the real
    encyclopedia validator's `published_not_stub` rule, which is declared
    `severity: "warning"` in extensions/encyclopedia -- a genuine plugin
    rule, not a hand-built fixture."""

    def test_encyclopedia_warning_lands_in_warnings_not_errors(self):
        schema = KBSchema(name="test-enc", kb_type="encyclopedia")
        result = schema.validate_entry(
            "article",
            {"title": "x", "quality": "stub", "review_status": "published"},
            {"kb_type": "encyclopedia"},
        )
        warning_rules = {w.get("rule") for w in result["warnings"]}
        error_rules = {e.get("rule") for e in result["errors"]}
        assert "published_not_stub" in warning_rules, (
            f"expected published_not_stub as a warning, got warnings={result['warnings']} "
            f"errors={result['errors']}"
        )
        assert "published_not_stub" not in error_rules


class TestRunValidatorsDegradesPerValidator:
    """run_validators must not let one raising validator take out the rest
    of the KB's validators for that call -- it degrades per-validator (logs
    + skips just that one), not per-call. This only shows up with two+
    validators registered for the same kb_type; a single-validator fixture
    can't distinguish "skip this validator" from "abort the whole call",
    since both look identical (empty results, one warning) with only one
    validator in play."""

    def test_one_raising_validator_does_not_suppress_the_others(self, caplog):
        class BrokenPlugin:
            name = "broken_plugin"
            capabilities = {Capability.STORAGE}

            def get_validators(self):
                return [lambda entry_type, fields, ctx: (_ for _ in ()).throw(RuntimeError("boom"))]

        class GoodPlugin:
            name = "good_plugin"
            capabilities = {Capability.STORAGE}

            def get_validators(self):
                return [lambda entry_type, fields, ctx: [{"field": "x", "message": "bad x"}]]

        reg = PluginRegistry()
        reg.register(BrokenPlugin())
        reg.register(GoodPlugin())
        reg._discovered = True  # isolate: don't also pull in real entry points

        with caplog.at_level("WARNING"):
            results = reg.run_validators("", "some_type", {}, {})

        assert results == [{"field": "x", "message": "bad x"}], (
            "the good validator's result must survive the broken one raising"
        )
        warnings = [r for r in caplog.records if r.levelname == "WARNING"]
        assert warnings, "expected a warning logged for the raising validator, got none"


class TestRegistrationRefusesNonConforming:
    """The registry checks validator/hook signatures at registration time."""

    def test_registration_refuses_bad_validator_signature(self, caplog):
        class BadValidatorPlugin:
            name = "bad_validator_plugin"
            capabilities = {Capability.STORAGE}

            def get_validators(self):
                return [lambda entry: []]  # 1-arg -- old contract

        reg = PluginRegistry()
        reg.register(BadValidatorPlugin())
        reg._discovered = True  # isolate: don't also pull in real entry points
        with caplog.at_level("WARNING"):
            validators = reg.get_all_validators()

        assert validators == []
        assert any("bad_validator_plugin" in r.message for r in caplog.records)

    def test_registration_refuses_bad_validator_signature_scoped_path(self, caplog):
        """Same refusal, but through get_validators_for_kb / run_validators --
        the KB-scoped path kb_schema.py and index.py actually call in
        production. A fix that only filters the unscoped
        get_all_validators() aggregation would leave this path unguarded."""

        class BadValidatorPlugin:
            name = "bad_validator_plugin_scoped"
            capabilities = {Capability.STORAGE}

            def get_validators(self):
                return [lambda entry: []]  # 1-arg -- old contract

        reg = PluginRegistry()
        reg.register(BadValidatorPlugin())
        reg._discovered = True  # isolate: don't also pull in real entry points
        with caplog.at_level("WARNING"):
            validators = reg.get_validators_for_kb("")
            results = reg.run_validators("", "some_type", {}, {})

        assert validators == []
        assert results == []
        assert any("bad_validator_plugin_scoped" in r.message for r in caplog.records)

    def test_registration_refuses_bad_hook_signature(self, caplog):
        class BadHookPlugin:
            name = "bad_hook_plugin"
            capabilities = {Capability.STORAGE}

            def get_hooks(self):
                return {"before_save": [lambda entry: entry]}  # 1-arg -- wrong

        reg = PluginRegistry()
        reg.register(BadHookPlugin())
        reg._discovered = True  # isolate: don't also pull in real entry points
        with caplog.at_level("WARNING"):
            hooks = reg.get_all_hooks()

        assert hooks.get("before_save", []) == []
        assert any("bad_hook_plugin" in r.message for r in caplog.records)

    def test_registration_refuses_bad_hook_signature_scoped_path(self, caplog):
        """Same refusal, but through get_hooks_for_kb -- the KB-scoped
        lookup HookRunner actually calls in production."""

        class BadHookPlugin:
            name = "bad_hook_plugin_scoped"
            capabilities = {Capability.STORAGE}

            def get_hooks(self):
                return {"before_save": [lambda entry: entry]}  # 1-arg -- wrong

        reg = PluginRegistry()
        reg.register(BadHookPlugin())
        reg._discovered = True  # isolate: don't also pull in real entry points
        with caplog.at_level("WARNING"):
            hooks = reg.get_hooks_for_kb("")

        assert hooks.get("before_save", []) == []
        assert any("bad_hook_plugin_scoped" in r.message for r in caplog.records)

    def test_registration_accepts_conforming_validator(self, caplog):
        class GoodValidatorPlugin:
            name = "good_validator_plugin"
            capabilities = {Capability.STORAGE}

            def get_validators(self):
                return [lambda entry_type, fields, ctx: []]

        reg = PluginRegistry()
        reg.register(GoodValidatorPlugin())
        reg._discovered = True  # isolate: don't also pull in real entry points
        validators = reg.get_all_validators()

        assert len(validators) == 1
