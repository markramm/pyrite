"""ADR-0034 rule 2: a truncated body is never valid input to a write.

A bounded read hands an agent the first `body_chunk_size` characters of a body
plus `body_truncated: true`. An agent that edits what it received and writes the
entry back replaces the whole body with that chunk -- silent data loss produced
by the safety feature. Every write surface that can receive a body refuses an
input carrying the marker.

The round-trip tests are the ones that matter: read over MCP, feed exactly what
came back into the write path, assert the write is refused AND the stored body
is unchanged. The negative tests matter just as much -- a guard that refuses
everything passes a naive test and breaks the product.
"""

import contextlib

import pytest

pytest.importorskip("fastapi", reason="fastapi not installed")

from pyrite.server.mcp_server import DEFAULT_BODY_CHUNK

from .test_mcp_server import _make_mcp_server

BIG = "A" * 20000


# ---------------------------------------------------------------------------
# MCP harness -- the proven helper from test_mcp_server.py, one generic KB.
# ---------------------------------------------------------------------------


@contextlib.contextmanager
def _mcp(tier="admin"):
    """An admin-tier MCP server over one writable generic KB."""
    with _make_mcp_server([{"name": "test", "kb_type": "generic"}], tier=tier) as ctx:
        yield ctx["server"]


def _create(server, title, body):
    """Create an entry and return its id."""
    res = server._dispatch_tool(
        "kb_create",
        {"kb_name": "test", "entry_type": "note", "title": title, "body": body},
    )
    assert res.get("created"), res
    return res["entry_id"]


def _stored_body(server, entry_id):
    """The full body on disk, bypassing any read-side bound."""
    res = server._dispatch_tool(
        "kb_read_body",
        {"entry_id": entry_id, "kb_name": "test", "body_limit": 1_000_000},
    )
    assert "error" not in res, res
    return res["body"]


def _assert_refusal(res):
    """The MCP flat error envelope for a refused truncated write."""
    assert res.get("error_code") == "VALIDATION_FAILED", res
    assert res.get("retryable") is False, res
    msg = f"{res.get('error', '')} {res.get('suggestion', '')}"
    assert "body_truncated" in msg, msg
    # The error must teach: name the way to get the whole body.
    assert "kb_read_body" in msg or "body_offset" in msg, msg


# ---------------------------------------------------------------------------
# The round trip -- the test that matters most
# ---------------------------------------------------------------------------


def test_mcp_round_trip_kb_get_into_kb_update_is_refused_and_body_survives():
    """Read truncated over kb_get, write it straight back: refused, body intact."""
    with _mcp() as server:
        entry_id = _create(server, "Big Entry", BIG)

        got = server._dispatch_tool("kb_get", {"entry_id": entry_id, "kb_name": "test"})
        entry = got["entry"]
        assert entry["body_truncated"] is True
        assert len(entry["body"]) == DEFAULT_BODY_CHUNK

        # Exactly what came back, plus the id -- the naive agent round trip.
        res = server._dispatch_tool("kb_update", {**entry, "entry_id": entry_id})

        _assert_refusal(res)
        assert _stored_body(server, entry_id) == BIG


def test_mcp_round_trip_kb_batch_read_into_kb_create_is_refused():
    """The marker arriving via kb_batch_read is refused by kb_create too."""
    with _mcp() as server:
        entry_id = _create(server, "Batch Source", BIG)

        got = server._dispatch_tool(
            "kb_batch_read", {"entries": [{"entry_id": entry_id, "kb_name": "test"}]}
        )
        entry = got["entries"][0]
        assert entry["body_truncated"] is True

        res = server._dispatch_tool(
            "kb_create",
            {
                "kb_name": "test",
                "entry_type": "note",
                "title": "Copy of Batch Source",
                "body": entry["body"],
                "body_truncated": entry["body_truncated"],
                "body_length": entry["body_length"],
            },
        )

        _assert_refusal(res)
        listed = server._dispatch_tool("kb_list_entries", {"kb_name": "test"})
        titles = [e.get("title") for e in listed.get("entries", [])]
        assert "Copy of Batch Source" not in titles


# ---------------------------------------------------------------------------
# MCP regimes: true / false / absent / "true" / marker without a body
# ---------------------------------------------------------------------------


def test_mcp_update_without_marker_still_works():
    """A normal write is unaffected -- the guard must not refuse everything."""
    with _mcp() as server:
        entry_id = _create(server, "Normal Entry", "short body")

        res = server._dispatch_tool(
            "kb_update", {"entry_id": entry_id, "kb_name": "test", "body": "rewritten body"}
        )

        assert res.get("updated") is True, res
        assert _stored_body(server, entry_id) == "rewritten body"


def test_mcp_update_with_marker_false_is_allowed():
    """body_truncated: false means nothing was truncated -- allow the write."""
    with _mcp() as server:
        entry_id = _create(server, "False Marker", "short body")

        res = server._dispatch_tool(
            "kb_update",
            {
                "entry_id": entry_id,
                "kb_name": "test",
                "body": "rewritten body",
                "body_truncated": False,
            },
        )

        assert res.get("updated") is True, res
        assert _stored_body(server, entry_id) == "rewritten body"


def test_mcp_marker_as_string_true_is_refused():
    """A JSON-ish client that sends the string "true" is still refused."""
    with _mcp() as server:
        entry_id = _create(server, "String Marker", BIG)

        res = server._dispatch_tool(
            "kb_update",
            {
                "entry_id": entry_id,
                "kb_name": "test",
                "body": "A" * 8000,
                "body_truncated": "true",
            },
        )

        _assert_refusal(res)
        assert _stored_body(server, entry_id) == BIG


def test_mcp_marker_without_a_body_is_allowed():
    """A metadata-only update carrying the marker writes no body -- allow it."""
    with _mcp() as server:
        entry_id = _create(server, "Metadata Only", BIG)

        res = server._dispatch_tool(
            "kb_update",
            {
                "entry_id": entry_id,
                "kb_name": "test",
                "tags": ["reviewed"],
                "body_truncated": True,
            },
        )

        assert res.get("updated") is True, res
        assert _stored_body(server, entry_id) == BIG


def test_mcp_marker_nested_in_metadata_is_refused():
    """The marker relayed inside `metadata` alongside a body is still refused."""
    with _mcp() as server:
        entry_id = _create(server, "Nested Marker", BIG)

        res = server._dispatch_tool(
            "kb_update",
            {
                "entry_id": entry_id,
                "kb_name": "test",
                "body": "A" * 8000,
                "metadata": {"body_truncated": True, "body_length": 20000},
            },
        )

        _assert_refusal(res)
        assert _stored_body(server, entry_id) == BIG


def test_mcp_body_exactly_chunk_size_without_marker_is_allowed():
    """A body whose length equals the chunk size, unmarked, writes normally."""
    with _mcp() as server:
        entry_id = _create(server, "Exact Chunk", "seed")
        exact = "B" * DEFAULT_BODY_CHUNK

        res = server._dispatch_tool(
            "kb_update", {"entry_id": entry_id, "kb_name": "test", "body": exact}
        )

        assert res.get("updated") is True, res
        assert _stored_body(server, entry_id) == exact


# ---------------------------------------------------------------------------
# MCP: kb_bulk_create -- per-item refusal, per its existing contract
# ---------------------------------------------------------------------------


def test_mcp_bulk_create_refuses_only_the_marked_item():
    """One marked item of three is refused per-item; the others are created."""
    with _mcp() as server:
        res = server._dispatch_tool(
            "kb_bulk_create",
            {
                "kb_name": "test",
                "entries": [
                    {"entry_type": "note", "title": "Bulk Clean One", "body": "fine"},
                    {
                        "entry_type": "note",
                        "title": "Bulk Marked",
                        "body": "A" * 8000,
                        "body_truncated": True,
                        "body_length": 20000,
                    },
                    {"entry_type": "note", "title": "Bulk Clean Two", "body": "also fine"},
                ],
            },
        )

        assert res["total"] == 3, res
        assert res["created"] == 2, res
        assert res["failed"] == 1, res
        results = res["results"]
        assert results[0]["created"] is True
        assert results[2]["created"] is True
        assert results[1]["created"] is False
        assert "body_truncated" in results[1]["error"]

        listed = server._dispatch_tool("kb_list_entries", {"kb_name": "test", "limit": 50})
        titles = [e.get("title") for e in listed.get("entries", [])]
        assert "Bulk Clean One" in titles
        assert "Bulk Clean Two" in titles
        assert "Bulk Marked" not in titles


def test_mcp_bulk_create_without_markers_is_unaffected():
    """A clean bulk create still creates every item."""
    with _mcp() as server:
        res = server._dispatch_tool(
            "kb_bulk_create",
            {
                "kb_name": "test",
                "entries": [
                    {"entry_type": "note", "title": "Clean A", "body": "a"},
                    {"entry_type": "note", "title": "Clean B", "body": "b"},
                ],
            },
        )
        assert res["created"] == 2, res
        assert res["failed"] == 0, res


def test_mcp_task_create_with_marker_is_refused():
    """Every write tool that takes a body is covered, not just the kb_* three."""
    with _mcp() as server:
        res = server._dispatch_tool(
            "task_create",
            {
                "kb_name": "test",
                "title": "Truncated Task",
                "body": "A" * 8000,
                "body_truncated": True,
            },
        )
        _assert_refusal(res)


def test_mcp_allowed_false_marker_is_not_persisted_as_frontmatter():
    """`body_truncated: false` is read transport, not entry content.

    kb_create forwards every unrecognised argument into the entry's
    frontmatter, so an allowed false marker would otherwise be written to disk
    and come back on the next read -- where it would then be echoed into a
    write and start tripping the guard.
    """
    with _mcp() as server:
        res = server._dispatch_tool(
            "kb_create",
            {
                "kb_name": "test",
                "entry_type": "note",
                "title": "False Marker Create",
                "body": "short",
                "body_truncated": False,
                "body_length": 5,
            },
        )
        assert res.get("created") is True, res

        got = server._dispatch_tool("kb_get", {"entry_id": res["entry_id"], "kb_name": "test"})[
            "entry"
        ]
        assert "body_truncated" not in got, got
        assert got.get("metadata", {}).get("body_truncated") is None, got


def test_mcp_bulk_create_allowed_false_marker_is_not_persisted():
    """The same, on the bulk path's own extra-kwargs forwarding."""
    with _mcp() as server:
        res = server._dispatch_tool(
            "kb_bulk_create",
            {
                "kb_name": "test",
                "entries": [
                    {
                        "entry_type": "note",
                        "title": "Bulk False Marker",
                        "body": "short",
                        "body_truncated": False,
                    }
                ],
            },
        )
        assert res["created"] == 1, res

        got = server._dispatch_tool(
            "kb_get", {"entry_id": res["results"][0]["entry_id"], "kb_name": "test"}
        )["entry"]
        assert "body_truncated" not in got, got
        assert got.get("metadata", {}).get("body_truncated") is None, got


def test_mcp_read_tools_are_not_guarded():
    """The marker is a legal *read* parameter shape; reads must not be refused."""
    with _mcp() as server:
        entry_id = _create(server, "Readable", BIG)
        res = server._dispatch_tool(
            "kb_get", {"entry_id": entry_id, "kb_name": "test", "body_truncated": True}
        )
        assert "error" not in res, res


# ---------------------------------------------------------------------------
# REST -- must go through TestClient: the pydantic models would otherwise
# drop the key before any check could see it.
# ---------------------------------------------------------------------------


def _rest_refusal(resp):
    assert resp.status_code == 400, resp.text
    detail = resp.json()["detail"]
    assert detail["code"] == "VALIDATION_FAILED", detail
    msg = f"{detail.get('message', '')} {detail.get('hint', '')}"
    assert "body_truncated" in msg, msg
    assert "body_offset" in msg or "kb_read_body" in msg, msg


def test_rest_post_entries_refuses_marked_body(rest_api_env):
    client = rest_api_env["client"]
    kb = rest_api_env["events_kb"].name

    resp = client.post(
        "/api/entries",
        json={
            "kb": kb,
            "entry_type": "note",
            "title": "Truncated REST Create",
            "body": "A" * 8000,
            "body_truncated": True,
            "body_length": 20000,
        },
    )

    _rest_refusal(resp)
    listing = client.get("/api/entries", params={"kb": kb, "limit": 200})
    titles = [e["title"] for e in listing.json()["entries"]]
    assert "Truncated REST Create" not in titles


def test_rest_put_entries_refuses_marked_body_and_body_survives(rest_api_env, sample_events):
    client = rest_api_env["client"]
    kb = rest_api_env["events_kb"].name
    entry_id = sample_events[0].id

    before = client.get(f"/api/entries/{entry_id}", params={"kb": kb}).json()["body"]

    resp = client.put(
        f"/api/entries/{entry_id}",
        json={"kb": kb, "body": "A" * 8000, "body_truncated": True},
    )

    _rest_refusal(resp)
    after = client.get(f"/api/entries/{entry_id}", params={"kb": kb}).json()["body"]
    assert after == before


def test_rest_put_without_marker_still_works(rest_api_env, sample_events):
    """A normal REST update is unaffected."""
    client = rest_api_env["client"]
    kb = rest_api_env["events_kb"].name
    entry_id = sample_events[0].id

    resp = client.put(
        f"/api/entries/{entry_id}",
        json={"kb": kb, "body": "a perfectly ordinary rewritten body"},
    )

    assert resp.status_code == 200, resp.text
    after = client.get(f"/api/entries/{entry_id}", params={"kb": kb}).json()["body"]
    assert after == "a perfectly ordinary rewritten body"


def test_rest_put_with_marker_false_is_allowed(rest_api_env, sample_events):
    client = rest_api_env["client"]
    kb = rest_api_env["events_kb"].name
    entry_id = sample_events[0].id

    resp = client.put(
        f"/api/entries/{entry_id}",
        json={"kb": kb, "body": "written with an explicit false marker", "body_truncated": False},
    )

    assert resp.status_code == 200, resp.text


def test_rest_patch_body_field_refuses_marked_body(rest_api_env, sample_events):
    """PATCH sets one field by name -- `field: "body"` is a body write too."""
    client = rest_api_env["client"]
    kb = rest_api_env["events_kb"].name
    entry_id = sample_events[0].id

    before = client.get(f"/api/entries/{entry_id}", params={"kb": kb}).json()["body"]

    resp = client.patch(
        f"/api/entries/{entry_id}",
        json={"kb": kb, "field": "body", "value": "A" * 8000, "body_truncated": True},
    )

    _rest_refusal(resp)
    after = client.get(f"/api/entries/{entry_id}", params={"kb": kb}).json()["body"]
    assert after == before


def test_rest_patch_non_body_field_with_marker_is_allowed(rest_api_env, sample_events):
    """PATCH of a non-body field writes no body -- the marker is inert."""
    client = rest_api_env["client"]
    kb = rest_api_env["events_kb"].name
    entry_id = sample_events[0].id

    resp = client.patch(
        f"/api/entries/{entry_id}",
        json={"kb": kb, "field": "importance", "value": "7", "body_truncated": True},
    )

    assert resp.status_code == 200, resp.text


def test_rest_import_refuses_marked_entry_and_imports_the_rest(rest_api_env, tmp_path):
    """POST /entries/import refuses the marked item, imports the clean ones."""
    import json

    client = rest_api_env["client"]
    kb = rest_api_env["events_kb"].name

    payload = [
        {"title": "Import Clean", "entry_type": "note", "body": "fine"},
        {
            "title": "Import Marked",
            "entry_type": "note",
            "body": "A" * 8000,
            "body_truncated": True,
            "body_length": 20000,
        },
    ]
    upload = tmp_path / "import.json"
    upload.write_text(json.dumps(payload))

    with upload.open("rb") as fh:
        resp = client.post(
            "/api/entries/import",
            params={"kb": kb},
            files={"file": ("import.json", fh, "application/json")},
        )

    assert resp.status_code == 200, resp.text
    result = resp.json()
    assert result["imported"] == 1, result
    assert result["errors"] == 1, result
    assert "body_truncated" in result["error_details"][0]["error"], result

    listing = client.get("/api/entries", params={"kb": kb, "limit": 200})
    titles = [e["title"] for e in listing.json()["entries"]]
    assert "Import Clean" in titles
    assert "Import Marked" not in titles
