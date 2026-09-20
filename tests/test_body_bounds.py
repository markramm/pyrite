"""Bounded agent-facing reads (ADR-0034 rules 1, 3, 4).

Three numbers, all configuration:

  PYRITE_BODY_CHUNK_DEFAULT   8000    default chunk per body
  PYRITE_BODY_CHUNK_MAX      20000    per-body ceiling, clamps a caller's body_limit
  PYRITE_BODY_RESPONSE_BUDGET 40000   per-response budget across all bodies

The invariants under test:

  * a parameter that reduces output (`fields`) never disables another bound
    (rule 1) -- this is #58, where `body_limit=6000` plus `fields=[...,"body"]`
    returned 171,189 characters;
  * bodies are capped at the default chunk whether or not the caller passed
    `body_limit`, on every read path (rule 3);
  * truncation is never silent: the marker keys survive projection (rule 2's
    first half, which rule 1 depends on to be observable);
  * invalid configuration fails loudly at start (rule 4).
"""

import tempfile
from contextlib import contextmanager
from pathlib import Path

import pytest

from pyrite.config import KBConfig, PyriteConfig, Settings
from pyrite.exceptions import ConfigError
from pyrite.server.mcp_server import PyriteMCPServer
from pyrite.services.body_bounds import BodyBounds, load_body_bounds

MARKER_KEYS = ("body_truncated", "body_length", "body_offset", "body_chunk_size")


# ---------------------------------------------------------------------------
# Configuration loading
# ---------------------------------------------------------------------------


class TestBodyBoundsConfig:
    """PYRITE_BODY_* are read at server start; invalid values fail loudly."""

    def test_defaults_when_unset(self, monkeypatch):
        for var in (
            "PYRITE_BODY_CHUNK_DEFAULT",
            "PYRITE_BODY_CHUNK_MAX",
            "PYRITE_BODY_RESPONSE_BUDGET",
        ):
            monkeypatch.delenv(var, raising=False)
        bounds = load_body_bounds()
        assert bounds.default_chunk == 8000
        assert bounds.max_chunk == 20000
        assert bounds.response_budget == 40000

    def test_env_overrides_each_number(self, monkeypatch):
        monkeypatch.setenv("PYRITE_BODY_CHUNK_DEFAULT", "100")
        monkeypatch.setenv("PYRITE_BODY_CHUNK_MAX", "500")
        monkeypatch.setenv("PYRITE_BODY_RESPONSE_BUDGET", "900")
        bounds = load_body_bounds()
        assert (bounds.default_chunk, bounds.max_chunk, bounds.response_budget) == (100, 500, 900)

    @pytest.mark.parametrize(
        "var",
        [
            "PYRITE_BODY_CHUNK_DEFAULT",
            "PYRITE_BODY_CHUNK_MAX",
            "PYRITE_BODY_RESPONSE_BUDGET",
        ],
    )
    @pytest.mark.parametrize("bad", ["abc", "", "0", "-1", "8000.5", " "])
    def test_invalid_value_fails_loudly_naming_the_variable(self, monkeypatch, var, bad):
        monkeypatch.setenv(var, bad)
        with pytest.raises(ConfigError) as exc:
            load_body_bounds()
        # The message must name the variable and echo what was given, or an
        # operator cannot tell which of three variables they mistyped.
        assert var in str(exc.value)
        assert repr(bad) in str(exc.value) or bad in str(exc.value)

    def test_default_above_max_fails_loudly(self, monkeypatch):
        monkeypatch.setenv("PYRITE_BODY_CHUNK_DEFAULT", "30000")
        monkeypatch.setenv("PYRITE_BODY_CHUNK_MAX", "20000")
        with pytest.raises(ConfigError) as exc:
            load_body_bounds()
        msg = str(exc.value)
        assert "PYRITE_BODY_CHUNK_DEFAULT" in msg and "PYRITE_BODY_CHUNK_MAX" in msg

    def test_default_equal_to_max_is_allowed(self, monkeypatch):
        monkeypatch.setenv("PYRITE_BODY_CHUNK_DEFAULT", "20000")
        monkeypatch.setenv("PYRITE_BODY_CHUNK_MAX", "20000")
        assert load_body_bounds().default_chunk == 20000

    def test_server_start_fails_on_invalid_config(self, monkeypatch):
        monkeypatch.setenv("PYRITE_BODY_CHUNK_MAX", "nope")
        with tempfile.TemporaryDirectory() as tmpdir:
            config = PyriteConfig(
                knowledge_bases=[],
                settings=Settings(index_path=Path(tmpdir) / "index.db"),
            )
            with pytest.raises(ConfigError) as exc:
                PyriteMCPServer(config, tier="read")
            assert "PYRITE_BODY_CHUNK_MAX" in str(exc.value)


# ---------------------------------------------------------------------------
# chunk_body
# ---------------------------------------------------------------------------


class TestChunkBody:
    """The per-body bound, including the ceiling."""

    def test_small_body_unchanged_no_marker(self):
        bounds = BodyBounds(default_chunk=8000, max_chunk=20000, response_budget=40000)
        entry = {"id": "e", "body": "short"}
        out = bounds.chunk_body(entry)
        assert out["body"] == "short"
        for key in MARKER_KEYS:
            assert key not in out

    def test_none_body_untouched(self):
        bounds = BodyBounds(default_chunk=8000, max_chunk=20000, response_budget=40000)
        out = bounds.chunk_body({"id": "e", "body": None})
        assert out["body"] is None
        assert "body_truncated" not in out

    def test_missing_body_untouched(self):
        bounds = BodyBounds(default_chunk=8000, max_chunk=20000, response_budget=40000)
        out = bounds.chunk_body({"id": "e"})
        assert out == {"id": "e"}

    def test_caller_limit_clamped_to_ceiling(self):
        bounds = BodyBounds(default_chunk=8000, max_chunk=20000, response_budget=40000)
        entry = {"id": "e", "body": "x" * 50000}
        out = bounds.chunk_body(entry, limit=999_999)
        assert len(out["body"]) == 20000
        assert out["body_truncated"] is True
        assert out["body_length"] == 50000
        assert out["body_chunk_size"] == 20000

    def test_ceiling_is_20000_not_50000(self):
        """The shipped ceiling drops 50,000 -> 20,000 (ADR-0034 rule 4)."""
        bounds = load_body_bounds()
        entry = {"id": "e", "body": "x" * 60000}
        out = bounds.chunk_body(entry, limit=50000)
        assert len(out["body"]) == 20000

    def test_offset_past_end_gives_empty_chunk_with_marker(self):
        bounds = BodyBounds(default_chunk=8000, max_chunk=20000, response_budget=40000)
        out = bounds.chunk_body({"id": "e", "body": "x" * 100}, offset=500)
        assert out["body"] == ""
        assert out["body_truncated"] is True
        assert out["body_length"] == 100
        assert out["body_offset"] == 500
        assert out["body_chunk_size"] == 0

    def test_negative_offset_is_clamped_to_zero(self):
        """A negative offset must not slice from the END of the body.

        Python's `body[-3:]` returns the last three characters; reporting
        those as `body_offset: -3` would hand a caller the tail of an entry
        while telling it it read the head.
        """
        bounds = BodyBounds(default_chunk=8000, max_chunk=20000, response_budget=40000)
        out = bounds.chunk_body({"id": "e", "body": "abcdefghij"}, offset=-3)
        assert out["body"] == "abcdefghij"
        assert "body_truncated" not in out

    def test_negative_offset_clamped_on_a_truncated_body(self):
        bounds = BodyBounds(default_chunk=10, max_chunk=20000, response_budget=40000)
        out = bounds.chunk_body({"id": "e", "body": "abcdefghij" * 3}, offset=-5)
        assert out["body"] == "abcdefghij"
        assert out["body_offset"] == 0
        assert out["body_truncated"] is True

    def test_negative_limit_yields_empty_not_reversed_slice(self):
        bounds = BodyBounds(default_chunk=8000, max_chunk=20000, response_budget=40000)
        out = bounds.chunk_body({"id": "e", "body": "x" * 100}, limit=-5)
        assert out["body"] == ""
        assert out["body_chunk_size"] == 0
        assert out["body_length"] == 100

    def test_zero_length_remaining_budget_still_marks(self):
        bounds = BodyBounds(default_chunk=8000, max_chunk=20000, response_budget=40000)
        out = bounds.chunk_body({"id": "e", "body": "x" * 100}, limit=0)
        assert out["body"] == ""
        assert out["body_truncated"] is True
        assert out["body_length"] == 100
        assert out["body_chunk_size"] == 0

    def test_empty_body_never_marked(self):
        """An empty body is complete, not truncated -- even at limit 0."""
        bounds = BodyBounds(default_chunk=8000, max_chunk=20000, response_budget=40000)
        out = bounds.chunk_body({"id": "e", "body": ""}, limit=0)
        assert out["body"] == ""
        assert "body_truncated" not in out

    def test_does_not_mutate_input(self):
        bounds = BodyBounds(default_chunk=8000, max_chunk=20000, response_budget=40000)
        entry = {"id": "e", "body": "x" * 30000}
        bounds.chunk_body(entry)
        assert len(entry["body"]) == 30000
        assert "body_truncated" not in entry


# ---------------------------------------------------------------------------
# fill_budget
# ---------------------------------------------------------------------------


class TestFillBudget:
    """The per-response budget across several bodies."""

    def test_bodies_within_budget_untouched(self):
        bounds = BodyBounds(default_chunk=8000, max_chunk=20000, response_budget=40000)
        entries = [{"id": f"e{i}", "body": "x" * 100} for i in range(5)]
        out = bounds.fill_budget(entries)
        assert [len(e["body"]) for e in out] == [100] * 5
        assert all("body_truncated" not in e for e in out)

    def test_total_never_exceeds_budget(self):
        bounds = BodyBounds(default_chunk=8000, max_chunk=20000, response_budget=40000)
        entries = [{"id": f"e{i}", "body": "x" * 20000} for i in range(20)]
        out = bounds.fill_budget(entries, limit=20000)
        assert sum(len(e["body"]) for e in out) <= 40000

    def test_request_order_earlier_entries_fill_first(self):
        bounds = BodyBounds(default_chunk=100, max_chunk=100, response_budget=250)
        entries = [{"id": f"e{i}", "body": "x" * 100} for i in range(4)]
        out = bounds.fill_budget(entries)
        assert [len(e["body"]) for e in out] == [100, 100, 50, 0]

    def test_entries_past_the_budget_get_zero_with_the_marker(self):
        """Not dropped, not reported not_found: zero characters plus the marker."""
        bounds = BodyBounds(default_chunk=100, max_chunk=100, response_budget=100)
        entries = [{"id": "first", "body": "a" * 100}, {"id": "second", "body": "b" * 4321}]
        out = bounds.fill_budget(entries)
        assert out[1]["id"] == "second"
        assert out[1]["body"] == ""
        assert out[1]["body_truncated"] is True
        assert out[1]["body_length"] == 4321  # its TRUE length, not zero
        assert out[1]["body_offset"] == 0
        assert out[1]["body_chunk_size"] == 0

    def test_first_body_alone_exceeding_budget_is_truncated_to_it(self):
        bounds = BodyBounds(default_chunk=8000, max_chunk=20000, response_budget=40000)
        entries = [{"id": "big", "body": "x" * 500000}]
        out = bounds.fill_budget(entries, limit=20000)
        assert len(out[0]["body"]) == 20000
        assert out[0]["body_truncated"] is True

    def test_empty_and_none_bodies_consume_no_budget(self):
        """50 empty/None bodies: no marker, no division by zero, budget intact."""
        bounds = BodyBounds(default_chunk=8000, max_chunk=20000, response_budget=40000)
        entries = [{"id": f"e{i}", "body": "" if i % 2 else None} for i in range(50)]
        entries.append({"id": "real", "body": "y" * 8000})
        out = bounds.fill_budget(entries)
        assert all("body_truncated" not in e for e in out[:50])
        assert len(out[-1]["body"]) == 8000
        assert "body_truncated" not in out[-1]

    def test_empty_entry_list(self):
        bounds = BodyBounds(default_chunk=8000, max_chunk=20000, response_budget=40000)
        assert bounds.fill_budget([]) == []

    def test_entries_without_body_key_consume_no_budget(self):
        bounds = BodyBounds(default_chunk=100, max_chunk=100, response_budget=100)
        entries = [{"id": "meta-only"}, {"id": "has-body", "body": "z" * 100}]
        out = bounds.fill_budget(entries)
        assert out[0] == {"id": "meta-only"}
        assert len(out[1]["body"]) == 100

    def test_offset_accounting_charges_only_returned_characters(self):
        """body_offset shifts the window; the budget charges what is returned."""
        bounds = BodyBounds(default_chunk=100, max_chunk=100, response_budget=150)
        entries = [{"id": f"e{i}", "body": "x" * 1000} for i in range(3)]
        out = bounds.fill_budget(entries, offset=500)
        assert [len(e["body"]) for e in out] == [100, 50, 0]
        assert all(e["body_offset"] == 500 for e in out)
        assert all(e["body_length"] == 1000 for e in out)


# ---------------------------------------------------------------------------
# MCP read paths
# ---------------------------------------------------------------------------


@contextmanager
def _server(tier="write"):
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        kb_path = tmpdir / "test"
        kb_path.mkdir()
        kbc = KBConfig(name="test", path=kb_path, kb_type="generic")
        config = PyriteConfig(
            knowledge_bases=[kbc],
            settings=Settings(index_path=tmpdir / "index.db"),
        )
        server = PyriteMCPServer(config, tier=tier)
        server.index_mgr.index_all()
        try:
            yield server
        finally:
            server.close()


def _create(server, title, body):
    server._dispatch_tool(
        "kb_create",
        {"kb_name": "test", "entry_type": "note", "title": title, "body": body},
    )
    found = server._dispatch_tool(
        "kb_search", {"query": f'"{title}"', "kb_name": "test", "limit": 50}
    )
    for r in found["results"]:
        if r.get("title") == title:
            return r["id"]
    raise AssertionError(f"entry {title!r} not found after create")


class TestFieldsNeverDefeatsTheBound:
    """#58: `fields` including `body` skipped chunking entirely."""

    def test_kb_get_fields_with_body_limit_holds_the_bound(self):
        with _server() as server:
            eid = _create(server, "Huge One", "x" * 30000)
            result = server._dispatch_tool(
                "kb_get",
                {
                    "entry_id": eid,
                    "kb_name": "test",
                    "body_limit": 6000,
                    "fields": ["id", "title", "body"],
                },
            )
            entry = result["entry"]
            assert len(entry["body"]) == 6000
            for key in MARKER_KEYS:
                assert key in entry, f"{key} must survive projection"
            assert entry["body_truncated"] is True
            assert entry["body_length"] == 30000

    def test_kb_batch_read_fields_with_body_limit_holds_the_bound(self):
        with _server() as server:
            ids = [_create(server, f"Batch Huge {i}", "x" * 30000) for i in range(2)]
            result = server._dispatch_tool(
                "kb_batch_read",
                {
                    "entries": [{"entry_id": i, "kb_name": "test"} for i in ids],
                    "body_limit": 6000,
                    "fields": ["id", "title", "body"],
                },
            )
            assert result["found"] == 2
            for entry in result["entries"]:
                assert len(entry["body"]) == 6000
                assert entry["body_truncated"] is True
                assert entry["body_length"] == 30000

    def test_kb_get_fields_without_body_limit_still_bounded(self):
        """Rule 3: bounded by default, whether or not body_limit was passed."""
        with _server() as server:
            eid = _create(server, "Default Bound", "x" * 30000)
            entry = server._dispatch_tool(
                "kb_get",
                {"entry_id": eid, "kb_name": "test", "fields": ["id", "body"]},
            )["entry"]
            assert len(entry["body"]) == 8000
            assert entry["body_truncated"] is True

    def test_projection_without_body_carries_no_marker(self):
        with _server() as server:
            eid = _create(server, "No Body Asked", "x" * 30000)
            entry = server._dispatch_tool(
                "kb_get",
                {"entry_id": eid, "kb_name": "test", "fields": ["id", "title"]},
            )["entry"]
            assert "body" not in entry
            for key in MARKER_KEYS:
                assert key not in entry

    def test_projection_keeps_identity_fields(self):
        """The existing identity-pair contract is not broken by the marker keys."""
        with _server() as server:
            eid = _create(server, "Identity Kept", "x" * 30000)
            entry = server._dispatch_tool(
                "kb_get", {"entry_id": eid, "kb_name": "test", "fields": ["body"]}
            )["entry"]
            assert entry["id"] == eid
            assert entry["kb_name"] == "test"

    def test_small_body_with_fields_unchanged(self):
        with _server() as server:
            eid = _create(server, "Tiny", "just a little body")
            entry = server._dispatch_tool(
                "kb_get",
                {"entry_id": eid, "kb_name": "test", "fields": ["id", "body"]},
            )["entry"]
            assert entry["body"] == "just a little body"
            for key in MARKER_KEYS:
                assert key not in entry

    def test_kb_search_include_body_is_bounded(self):
        """kb_search has no body_limit; include_body must still be bounded."""
        with _server() as server:
            _create(server, "Searchable Huge", "x" * 30000)
            results = server._dispatch_tool(
                "kb_search",
                {"query": '"Searchable Huge"', "kb_name": "test", "include_body": True},
            )["results"]
            body_rows = [r for r in results if r.get("body")]
            assert body_rows, "expected a row with a body"
            for row in body_rows:
                assert len(row["body"]) <= 8000
                if row["body_length"] > 8000:
                    assert row["body_truncated"] is True

    def test_kb_search_fields_with_body_is_bounded(self):
        with _server() as server:
            _create(server, "Projected Huge", "x" * 30000)
            results = server._dispatch_tool(
                "kb_search",
                {"query": '"Projected Huge"', "kb_name": "test", "fields": ["id", "body"]},
            )["results"]
            for row in results:
                if row.get("body"):
                    assert len(row["body"]) <= 8000

    def test_kb_list_entries_is_bounded(self):
        with _server() as server:
            _create(server, "Listed Huge", "x" * 30000)
            entries = server._dispatch_tool("kb_list_entries", {"kb_name": "test"})["entries"]
            for entry in entries:
                if entry.get("body"):
                    assert len(entry["body"]) <= 8000

    def test_kb_recent_is_bounded(self):
        with _server() as server:
            _create(server, "Recent Huge", "x" * 30000)
            entries = server._dispatch_tool("kb_recent", {"kb_name": "test"})["entries"]
            for entry in entries:
                if entry.get("body"):
                    assert len(entry["body"]) <= 8000

    def test_kb_get_negative_body_offset_does_not_return_the_tail(self):
        with _server() as server:
            eid = _create(server, "Tail Probe", "HEAD" + "m" * 29992 + "TAIL")
            entry = server._dispatch_tool(
                "kb_get", {"entry_id": eid, "kb_name": "test", "body_offset": -4}
            )["entry"]
            assert entry["body"].startswith("HEAD")
            assert entry["body_offset"] == 0

    def test_kb_read_body_negative_offset_does_not_return_the_tail(self):
        """The continuation tool slices directly; it needs the same clamp."""
        with _server() as server:
            eid = _create(server, "Continuation Tail", "HEAD" + "m" * 29992 + "TAIL")
            result = server._dispatch_tool(
                "kb_read_body", {"entry_id": eid, "kb_name": "test", "body_offset": -4}
            )
            assert result["body"].startswith("HEAD")
            assert result["body_offset"] == 0
            assert result["has_more"] is True

    def test_kb_read_body_clamps_to_the_ceiling(self):
        with _server() as server:
            eid = _create(server, "Read Body Huge", "x" * 60000)
            result = server._dispatch_tool(
                "kb_read_body",
                {"entry_id": eid, "kb_name": "test", "body_limit": 999999},
            )
            assert len(result["body"]) == 20000
            assert result["body_length"] == 60000
            assert result["has_more"] is True


class TestBatchResponseBudget:
    """kb_batch_read is bounded per response, not only per body."""

    def test_many_large_entries_bounded_by_the_response_budget(self):
        with _server() as server:
            ids = [_create(server, f"Budget Entry {i}", "x" * 20000) for i in range(6)]
            result = server._dispatch_tool(
                "kb_batch_read",
                {
                    "entries": [{"entry_id": i, "kb_name": "test"} for i in ids],
                    "body_limit": 20000,
                },
            )
            total = sum(len(e.get("body") or "") for e in result["entries"])
            assert total <= 40000, f"response carried {total} body characters"
            assert result["found"] == 6

    def test_entries_past_the_budget_come_back_with_zero_and_the_marker(self):
        with _server() as server:
            ids = [_create(server, f"Zeroed {i}", "x" * 20000) for i in range(4)]
            result = server._dispatch_tool(
                "kb_batch_read",
                {
                    "entries": [{"entry_id": i, "kb_name": "test"} for i in ids],
                    "body_limit": 20000,
                },
            )
            assert result["not_found"] == []
            assert len(result["entries"]) == 4
            starved = [e for e in result["entries"] if e.get("body") == ""]
            assert starved, "expected at least one entry starved of budget"
            for entry in starved:
                assert entry["body_truncated"] is True
                assert entry["body_length"] == 20000
                assert entry["body_chunk_size"] == 0

    def test_budget_applies_through_fields_too(self):
        with _server() as server:
            ids = [_create(server, f"Fielded Budget {i}", "x" * 20000) for i in range(6)]
            result = server._dispatch_tool(
                "kb_batch_read",
                {
                    "entries": [{"entry_id": i, "kb_name": "test"} for i in ids],
                    "body_limit": 20000,
                    "fields": ["id", "body"],
                },
            )
            total = sum(len(e.get("body") or "") for e in result["entries"])
            assert total <= 40000

    def test_small_bodies_are_untouched_by_the_budget(self):
        with _server() as server:
            ids = [_create(server, f"Small Budget {i}", f"tiny body {i}") for i in range(10)]
            result = server._dispatch_tool(
                "kb_batch_read",
                {"entries": [{"entry_id": i, "kb_name": "test"} for i in ids]},
            )
            for entry in result["entries"]:
                assert "body_truncated" not in entry
                assert entry["body"].startswith("tiny body")


class TestToolDescriptionsReportEffectiveValues:
    """Rule 4, final sentence: descriptions state the loaded numbers."""

    def test_descriptions_carry_the_defaults(self):
        with _server(tier="read") as server:
            tools = {t["name"]: t for t in server.get_tools_list()}
            get_desc = tools["kb_get"]["description"]
            assert "8000" in get_desc
            assert "50000" not in get_desc
            limit_desc = tools["kb_get"]["inputSchema"]["properties"]["body_limit"]["description"]
            assert "8000" in limit_desc and "20000" in limit_desc
            batch_desc = tools["kb_batch_read"]["description"]
            assert "40000" in batch_desc

    def test_descriptions_follow_the_environment(self, monkeypatch):
        monkeypatch.setenv("PYRITE_BODY_CHUNK_DEFAULT", "1234")
        monkeypatch.setenv("PYRITE_BODY_CHUNK_MAX", "4321")
        monkeypatch.setenv("PYRITE_BODY_RESPONSE_BUDGET", "7777")
        with _server(tier="read") as server:
            tools = {t["name"]: t for t in server.get_tools_list()}
            limit_desc = tools["kb_get"]["inputSchema"]["properties"]["body_limit"]["description"]
            assert "1234" in limit_desc and "4321" in limit_desc
            assert "8000" not in limit_desc
            assert "7777" in tools["kb_batch_read"]["description"]

    def test_fields_description_no_longer_promises_chunking_is_skipped(self):
        with _server(tier="read") as server:
            tools = {t["name"]: t for t in server.get_tools_list()}
            for name in ("kb_get", "kb_batch_read"):
                desc = tools[name]["inputSchema"]["properties"]["fields"]["description"]
                assert "chunking is skipped" not in desc

    def test_effective_numbers_follow_the_environment_per_server(self, monkeypatch):
        """Two servers in one process can hold different bounds."""
        monkeypatch.setenv("PYRITE_BODY_CHUNK_DEFAULT", "500")
        with _server(tier="write") as server:
            eid = _create(server, "Env Bound", "x" * 5000)
            entry = server._dispatch_tool("kb_get", {"entry_id": eid, "kb_name": "test"})["entry"]
            assert len(entry["body"]) == 500
            assert entry["body_truncated"] is True
