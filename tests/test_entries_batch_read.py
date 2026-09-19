"""REST `POST /entries/batch` parity with the MCP `kb_batch_read` contract (#134).

The MCP handler got this in #126/#137/#169; the REST twin is the same contract.
Before the fix: a malformed spec reached the SQL layer as a 500, and a `fields`
list that omitted `id`/`kb_name` made `found: 2` sit next to a `not_found` that
listed the same two entries.
"""

import pytest

pytest.importorskip("fastapi", reason="fastapi not installed")

_BATCH = "/api/entries/batch"


def _batch(client, entries, fields=None):
    payload = {"entries": entries}
    if fields is not None:
        payload["fields"] = fields
    return client.post(_BATCH, json=payload)


def test_fields_projection_keeps_found_and_not_found_consistent(rest_api_env, sample_events):
    client = rest_api_env["client"]
    kb = rest_api_env["events_kb"].name
    first, second = sample_events[0], sample_events[1]

    resp = _batch(
        client,
        [
            {"entry_id": first.id, "kb_name": kb},
            {"entry_id": second.id, "kb_name": kb},
        ],
        fields=["title"],
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["found"] == 2
    assert body["not_found"] == []
    for entry in body["entries"]:
        assert entry["id"] and entry["kb_name"]
        assert set(entry) == {"id", "kb_name", "title"}


def test_missing_entry_is_still_reported_not_found_with_fields(rest_api_env, sample_events):
    client = rest_api_env["client"]
    kb = rest_api_env["events_kb"].name
    present = sample_events[0]

    resp = _batch(
        client,
        [
            {"entry_id": present.id, "kb_name": kb},
            {"entry_id": "no-such-entry", "kb_name": kb},
        ],
        fields=["title"],
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["found"] == 1
    assert body["not_found"] == [{"entry_id": "no-such-entry", "kb_name": kb}]


@pytest.mark.parametrize(
    "spec",
    [
        {"kb_name": "test-events"},
        {"entry_id": "abc"},
        {"entry_id": None, "kb_name": "test-events"},
        {"entry_id": "", "kb_name": "test-events"},
        {"entry_id": 42, "kb_name": "test-events"},
        {"entry_id": "abc", "kb_name": ""},
        {"entry_id": "abc", "kb_name": 7},
    ],
)
def test_malformed_spec_is_a_structured_validation_error(rest_api_env, spec):
    resp = _batch(rest_api_env["client"], [spec])

    assert resp.status_code == 400, resp.text
    detail = resp.json()["detail"]
    assert detail["code"] == "VALIDATION_FAILED"
    assert "entries[0]" in detail["message"]


@pytest.mark.parametrize("entries", [5, "abc", [1], [None]])
def test_non_list_or_non_dict_entries_is_a_structured_validation_error(rest_api_env, entries):
    resp = _batch(rest_api_env["client"], entries)

    assert resp.status_code == 400, resp.text
    detail = resp.json()["detail"]
    assert detail["code"] == "VALIDATION_FAILED"


def test_error_names_the_bad_position(rest_api_env, sample_events):
    client = rest_api_env["client"]
    kb = rest_api_env["events_kb"].name
    first = sample_events[0]

    resp = _batch(
        client,
        [
            {"entry_id": first.id, "kb_name": kb},
            {"entry_id": first.id, "kb_name": kb},
            {"kb_name": kb},
        ],
    )

    assert resp.status_code == 400, resp.text
    assert "entries[2]" in resp.json()["detail"]["message"]
