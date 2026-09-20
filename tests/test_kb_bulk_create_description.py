"""`kb_bulk_create`'s MCP tool description is the copy every agent reads at
connect time -- it must not repeat #95's false "best-effort" claim: one
malformed entry currently rejects the whole batch (schema validation runs
before the best-effort service logic), not per-entry independent
success/failure. Regression for #229 item 5."""

import jsonschema
import pytest

from pyrite.server.tool_schemas import WRITE_TOOLS


def test_description_does_not_claim_best_effort():
    description = WRITE_TOOLS["kb_bulk_create"]["description"]
    assert "best-effort" not in description.lower() or "not best-effort" in description.lower()


def test_malformed_entry_still_rejects_whole_batch_at_schema_level():
    """Pins the behavior the description now states. If this starts
    passing (i.e. schema validation stops rejecting the whole batch), the
    description should be revisited -- and #95 could be closed."""
    schema = WRITE_TOOLS["kb_bulk_create"]["inputSchema"]
    args = {
        "kb_name": "pyrite",
        "entries": [
            {"entry_type": "note", "title": "valid entry"},
            {"entry_type": "note"},  # missing required "title"
        ],
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(args, schema)
