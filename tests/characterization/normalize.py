"""Normalise the volatile fields out of a golden case before it is compared
or recorded (ADR-0037 theme 0's "say what you normalised").

Three kinds of value in a response body are not stable across a
regeneration, a machine, or a run, and would make every golden fail for a
reason that has nothing to do with authorization or error-shape behaviour:

1. **Timestamps** -- ``created_at``/``updated_at``/``date``-shaped ISO 8601
   strings (ADR-0037's world always seeds fixed dates for entry ``date``, but
   a handler may still report `datetime.now()` for a write's timestamp).
2. **Generated ids** -- job ids, session tokens, commit hashes: strings this
   harness's own fixture setup does not choose (contrast with entry ids like
   ``READABLE_ENTRY``, which are fixed and NOT normalised, because a
   changed entry id in a body would be a real behaviour change to catch).
3. **Filesystem paths** -- the world's `tmp_path_factory` directory appears
   verbatim in some error messages (`ConfigSaveRefusedError.config_file`,
   `BrandingInvalidError`'s str()) and changes on every run.

The list is short and explicit on purpose: a normaliser that is too clever
(e.g. "replace anything that looks like a number") would launder a real
status-code or error-code change into a false pass, which is exactly the
failure mode the mutation-check in the report proves does not happen.
"""

from __future__ import annotations

import re
from typing import Any

_ISO_TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:?\d{2})?")

# `QAService._maybe_validate` (pyrite/services/qa_service.py) mints an
# auto-assessment id of the shape `qa-{entry_id}-{ms epoch timestamp}` on
# every create -- e.g. `qa-private-note-1790384135890` -- a real product
# behaviour (an id that must be unique across repeated assessments of the
# same entry), not a bug, but the millisecond timestamp inside it makes the
# id itself, and so any body that names it (a cross-KB tool's pair list,
# `kb_batch_suggest`'s `source_id`/`target_id`), different on every run.
# Matched by shape rather than by key, because it appears embedded inside
# `source_id`/`target_id`/free-text `snippet` fields, not only as a bare id.
_QA_ASSESSMENT_ID = re.compile(r"qa-[a-zA-Z0-9_-]+?-\d{13}")
_JOB_OR_TOKEN_KEYS = {
    "job_id",
    "id",  # only ever normalised when the key name says "job"/"token"/"hash", see below
    "token",
    "session_token",
    "commit_hash",
    "commit",
}

# Field names whose value is a generated id/token, wherever they appear in a
# body -- normalised by KEY, not by shape, because a shape-based rule (any
# hex string) would also swallow a stable, meaningful entry id.
GENERATED_ID_KEYS = {"job_id", "token", "session_token", "commit_hash"}

# Field names whose numeric value is a computed score that legitimately
# varies in its low-order digits between index builds (FTS5 BM25's `rank` on
# a search hit) -- not authorization-relevant, and not reproducible byte for
# byte across a rebuilt index. Normalised to a fixed placeholder rather than
# rounded, so the golden diff never has to be re-tuned for a rounding change.
VOLATILE_SCORE_KEYS = {"rank"}

# `GET /api/kbs`'s per-KB `entries`/`indexed`/`last_indexed`/`source` fields
# specifically -- not an authorization signal at all, only a content one.
# Kept as its own small, always-applied rule (distinct from the REST
# enumeration-sensitive table below, which is keyed by route because most
# routes' content shape is route-specific) because these four leaf names
# appear inside `GET /api/kbs`'s nested per-KB dicts, and REST_ENUMERATION_
# SENSITIVE_FIELDS below already handles `GET /api/kbs`'s top-level `total`.
VOLATILE_CONTENT_KEYS = {"entries", "indexed", "last_indexed", "source"}

NORMALISED_TIMESTAMP = "<TIMESTAMP>"
NORMALISED_ID = "<GENERATED_ID>"
NORMALISED_PATH = "<TMPDIR>"
NORMALISED_SCORE = "<SCORE>"
NORMALISED_QA_ID = "qa-<GENERATED_ID>"
NORMALISED_CONTENT = "<CONTENT_STATE>"


def normalize(value: Any, *, tmpdir: str) -> Any:
    """Recursively normalise `value` (a JSON-shaped dict/list/str/scalar)."""
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            if k in GENERATED_ID_KEYS and isinstance(v, str):
                out[k] = NORMALISED_ID
            elif k in VOLATILE_SCORE_KEYS and isinstance(v, int | float):
                out[k] = NORMALISED_SCORE
            elif k in VOLATILE_CONTENT_KEYS:
                out[k] = NORMALISED_CONTENT
            else:
                out[k] = normalize(v, tmpdir=tmpdir)
        return out
    if isinstance(value, list):
        return [normalize(v, tmpdir=tmpdir) for v in value]
    if isinstance(value, str):
        text = value.replace(tmpdir, NORMALISED_PATH)
        text = _ISO_TIMESTAMP.sub(NORMALISED_TIMESTAMP, text)
        text = _QA_ASSESSMENT_ID.sub(NORMALISED_QA_ID, text)
        return text
    return value


NORMALISATION_LIST = [
    "timestamps: any ISO-8601-shaped date/time substring anywhere in a string value, "
    "including inside a message -> '<TIMESTAMP>'",
    "generated ids: the value of a 'job_id', 'token', 'session_token' or 'commit_hash' "
    "key, anywhere in the body -> '<GENERATED_ID>' (entry ids and KB names are NOT "
    "normalised -- they are fixed by the world's fixtures and a change in them is real)",
    "paths: the session's tmp_path_factory directory, verbatim, wherever it appears "
    "in a string (e.g. ConfigSaveRefusedError.config_file, a branding.yaml parse "
    "error) -> '<TMPDIR>'",
    "search rank: the value of a 'rank' key (FTS5 BM25 score on a search hit), which "
    "varies in its low-order digits between index builds -> '<SCORE>'",
    "QA auto-assessment ids: any 'qa-<id>-<13-digit ms timestamp>' substring "
    "(QAService's auto-assessment id, minted fresh on every create) -> 'qa-<GENERATED_ID>'",
    "content state: the value of an 'entries', 'indexed', 'last_indexed' or 'source' key "
    "(how much content a KB holds right now, not an authorization signal) -> "
    "'<CONTENT_STATE>' -- these change with every write any case in this shared-world "
    "suite makes, not only the case whose golden shows them",
    "REST enumeration content: for a route in REST_ENUMERATION_SENSITIVE_FIELDS (a "
    "count/list/search/validate/health-style route whose success body enumerates "
    "'everything in a KB' rather than naming one row), its listed top-level fields -> "
    "'<ENUMERATION_CONTENT>' on a success body only -- a refusal's detail/code/message "
    "is never touched. Mirrors normalize_mcp_result's ENUMERATION_SENSITIVE_FIELDS for MCP.",
    "MCP enumeration content: for a tool in ENUMERATION_SENSITIVE_FIELDS (a "
    "count/list/search-style tool whose success body enumerates 'everything in a KB' "
    "rather than one named row/entry), its listed top-level fields -> "
    "'<ENUMERATION_CONTENT>' on a success body only -- a refusal's error/error_code/"
    "retryable/suggestion envelope is never touched.",
    "a review row's auto-increment id: POST /api/reviews's 'id' field (a DB primary "
    "key, not a caller-chosen or world-fixture id) -> '<ENUMERATION_CONTENT>', since its "
    "value depends on how many other reviews any other case already created in the "
    "same process, not on this case's own authorization outcome.",
]

# -- MCP enumeration-sensitive tools -----------------------------------------
#
# A KB-bearing MCP tool's success body is either IDENTITY-BASED (its content
# depends only on the one row/entry/task the call names -- kb_get, kb_update,
# task_status, zettel_graph, every _MUTATES_ITS_ENTRY tool, ...) or
# ENUMERATION-SENSITIVE (its content is a count, list or aggregate over
# "everything in a KB" or "everything matching a filter" -- kb_search,
# kb_stats, kb_batch_suggest, investigation_find_duplicates, task_list, ...).
#
# The matrix's own write-tool cases (kb_create, task_create, social_post, ...)
# permanently add rows to the shared world for the rest of the test session,
# and each one also triggers QAService's auto-assessment side effect (another
# new row). An enumeration-sensitive tool's result is therefore a function of
# *which other cases already ran in the same process* -- not just of
# (tool, principal, kb_state) -- which is exactly wrong for a golden: under
# pytest-xdist, each parametrized principal gets its own worker process with
# its own freshly-built world, so the same call sees a different amount of
# accumulated content depending on process/worker layout, not on anything
# this harness is meant to characterize.
#
# The fix is not to prevent the side effects (every write tool's job IS to
# add content) but to stop pinning their downstream *count/list contents*,
# which were never the point -- only whether the call was AUTHORIZED (let
# through with a normal success envelope vs refused with a given error code)
# is. So every enumeration-sensitive tool's listed fields are replaced with a
# fixed marker before a golden is compared or recorded; the refusal shape
# (`error`/`error_code`/`retryable`/`suggestion`) is untouched and still fully
# pinned, since ENUMERATION_SENSITIVE_FIELDS is only consulted on a result
# that has none of those keys (see `normalize_mcp_result`).
NORMALISED_ENUMERATION_CONTENT = "<ENUMERATION_CONTENT>"

ENUMERATION_SENSITIVE_FIELDS: dict[str, tuple[str, ...]] = {
    "cascade_actors": ("count", "actors"),
    "cascade_capture_lanes": ("count", "lanes"),
    "cascade_timeline": ("count", "events"),
    "investigation_claims": ("count", "claims", "summary"),
    "investigation_entities": ("count", "entities", "summary"),
    "investigation_export_pack": ("content",),
    "investigation_find_duplicates": ("duplicates",),
    "investigation_ftm_export": ("entities",),
    "investigation_qa_report": ("source_tiers", "claims", "quality_score", "warnings"),
    "investigation_search_all": ("total_count", "groups"),
    "investigation_sources": ("count", "sources", "summary"),
    "investigation_status": (
        "summary",
        "entity_count",
        "event_count",
        "claim_count",
        "source_count",
        "claim_breakdown",
        "unverified_claims",
    ),
    "investigation_timeline": ("count", "events", "summary"),
    "kb_backlinks": ("backlink_count", "has_more", "backlinks"),
    "kb_batch_suggest": ("count", "pairs"),
    "kb_discover_neighbors": ("count", "discoveries"),
    "kb_find_by_assignee": ("entries", "count"),
    "kb_find_by_location": ("entries", "count"),
    "kb_find_by_status": ("entries", "count"),
    "kb_find_overdue": ("entries", "count"),
    "kb_index_sync": ("synced", "added", "updated", "removed"),
    "kb_list": ("knowledge_bases",),
    "kb_list_entries": ("entries", "total", "has_more"),
    "kb_orient": ("total_entries", "types", "top_tags", "recent"),
    "kb_qa_assess": ("assessed", "skipped", "results"),
    "kb_qa_status": (
        "total_entries",
        "total_issues",
        "issues_by_severity",
        "issues_by_rule",
        "coverage",
    ),
    "kb_qa_validate": ("issues", "count", "truncated"),
    "kb_recent": ("entries", "count"),
    "kb_search": ("count", "has_more", "results"),
    "kb_stats": ("kbs", "total_entries", "total_tags", "total_links", "type_counts"),
    "kb_tags": ("tag_count", "has_more", "tags"),
    "kb_timeline": ("count", "has_more", "events"),
    "social_newest": ("count", "newest"),
    "social_top": ("count", "top"),
    "solidarity_timeline": ("count", "events"),
    "sw_adrs": ("count", "total", "has_more", "adrs"),
    "sw_backlog": ("count", "total", "has_more", "items"),
    "sw_board": ("lanes",),
    "sw_component": ("count", "total", "has_more", "components"),
    "sw_epics": ("count", "epics"),
    "sw_milestones": ("count", "milestones"),
    "sw_pull_next": ("recommendation", "reason", "wip_status"),
    "sw_refine": ("summary", "items"),
    "sw_review_queue": ("items", "count", "over_limit"),
    "task_list": ("count", "tasks"),
    "wiki_quality_stats": (
        "total_articles",
        "quality_distribution",
        "review_status_distribution",
        "review_queue_size",
    ),
    "wiki_review_queue": ("count", "queue"),
    "wiki_stubs": ("count", "stubs"),
    "zettel_inbox": ("count", "inbox"),
}


def normalize_mcp_result(tool_name: str, result: Any, *, tmpdir: str) -> Any:
    """`normalize(result, ...)`, plus: for a tool in
    `ENUMERATION_SENSITIVE_FIELDS`, blank its listed top-level fields to
    `NORMALISED_ENUMERATION_CONTENT` -- but only on a SUCCESS body. A refusal
    (`_dispatch_tool`'s `error`/`error_code`/`retryable`/`suggestion`
    envelope) never has any of those field names, so this only ever touches
    a call that was let through -- the authorization outcome itself (was
    this call allowed, and with what shape) is exactly what stays pinned.
    """
    normalised = normalize(result, tmpdir=tmpdir)
    fields = ENUMERATION_SENSITIVE_FIELDS.get(tool_name)
    if fields and isinstance(normalised, dict) and "error" not in normalised:
        normalised = dict(normalised)
        for field in fields:
            if field in normalised:
                normalised[field] = NORMALISED_ENUMERATION_CONTENT
    return normalised


# -- REST enumeration-sensitive routes ---------------------------------------
#
# The same problem as the MCP table above, for REST: a route's success body
# is either IDENTITY-BASED (depends only on the one row the call names --
# `GET /api/entries/{entry_id}` against `rest_calls._entry_for`'s fixed
# fixture id, `PUT`/`PATCH` against `_writable_target`'s disposable-but-
# stable-per-case id) or ENUMERATION-SENSITIVE (a count, list or aggregate
# over "everything in a KB" -- `GET /api/entries`, `GET /api/tags`, `GET
# /api/stats`, every QA/search/link-discovery route). 33 of the 66 KB-bearing
# REST routes are enumeration-sensitive by this test; keyed by `(method,
# path)`, the same granularity `rest_calls.REST_CALL_SPECS` already uses, so
# the two tables can be read side by side.
#
# Identity-based routes are deliberately absent from this table: their body
# should stay exactly as pinned, because a change in the ONE row's content
# (not its count, its presence) is real information (`GET
# /api/entries/{entry_id}`, `GET /api/daily/{date_str}`, `POST /api/entries`
# and its `PUT`/`PATCH`/`DELETE` siblings, `POST /api/starred`, `POST
# /api/entries/resolve-batch`, `GET /api/entries/resolve`, `GET
# /api/kbs/{kb_name}/schema`, `GET /api/kbs/{kb_name}/orient`'s non-list
# fields, `POST /api/kbs/{kb_name}/export`, `POST /api/tasks/{task_id}/claim`
# -- each names its OWN row/target, not "everything").
NORMALISED_REST_ENUMERATION_CONTENT = "<ENUMERATION_CONTENT>"

REST_ENUMERATION_SENSITIVE_FIELDS: dict[tuple[str, str], tuple[str, ...]] = {
    ("GET", "/api/collections"): ("collections", "total"),
    ("GET", "/api/daily/dates"): ("dates",),
    ("GET", "/api/entries"): ("entries", "total"),
    ("GET", "/api/entries/export"): ("entries", "total"),
    ("GET", "/api/entries/titles"): ("entries",),
    ("GET", "/api/entries/wanted"): ("count", "pages"),
    ("GET", "/api/entries/{entry_id}/blocks"): ("blocks", "total"),
    ("GET", "/api/entries/{entry_id}/versions"): ("count", "versions"),
    ("GET", "/api/graph"): ("nodes", "edges"),
    ("GET", "/api/kbs"): ("total",),  # per-KB entries/indexed/... via VOLATILE_CONTENT_KEYS
    ("GET", "/api/kbs/{kb_name}"): ("entries", "indexed", "last_indexed", "source"),
    ("GET", "/api/kbs/{kb_name}/changes"): ("changes", "summary"),
    ("GET", "/api/kbs/{kb_name}/health"): ("entry_count", "file_count", "healthy", "last_indexed"),
    ("GET", "/api/kbs/{kb_name}/orient"): ("recent", "top_tags", "total_entries", "types"),
    ("GET", "/api/kbs/{kb_name}/templates"): ("templates", "total"),
    ("GET", "/api/links/batch-suggest"): ("count", "pairs"),
    ("GET", "/api/links/discover-neighbors"): ("count", "discoveries"),
    ("GET", "/api/qa/coverage"): ("assessed", "by_status", "coverage_pct", "total", "unassessed"),
    ("GET", "/api/qa/status"): (
        "issues_by_rule",
        "issues_by_severity",
        "total_entries",
        "total_issues",
    ),
    ("GET", "/api/qa/validate"): ("checked", "issues", "total"),
    ("GET", "/api/qa/validate/{entry_id}"): ("issues",),
    ("GET", "/api/repos"): ("repos",),
    ("GET", "/api/search"): ("count", "results"),
    ("GET", "/api/starred"): ("count", "starred"),
    ("GET", "/api/stats"): ("kbs", "total_entries", "total_links", "total_tags", "type_counts"),
    ("GET", "/api/tags"): ("count", "tags"),
    ("GET", "/api/tags/tree"): ("tree",),
    ("GET", "/api/tasks"): ("count", "tasks"),
    ("GET", "/api/timeline"): ("count", "events"),
    ("POST", "/api/collections/query-preview"): ("entries", "total"),
    ("POST", "/api/entries/batch"): ("entries", "found", "not_found"),
    ("POST", "/api/entries/import"): ("entries", "error_details", "errors", "imported"),
    # Not enumeration content, but the same fix: a DB auto-increment primary
    # key, not a caller-chosen or world-fixture id (contrast READABLE_ENTRY),
    # so its value depends on how many other reviews any other case already
    # created in the same process -- found via a 1-vs-3 mismatch under
    # pytest-xdist -n4 (worker composition changes how many earlier POSTs
    # ran first).
    ("POST", "/api/reviews"): ("id",),
}


def normalize_rest_body(method: str, path: str, body: Any, *, tmpdir: str) -> Any:
    """`normalize(body, ...)`, plus: for `(method, path)` in
    `REST_ENUMERATION_SENSITIVE_FIELDS`, blank its listed top-level fields to
    `NORMALISED_REST_ENUMERATION_CONTENT` -- but only on a body that is not a
    refusal shape. A refusal is `{"detail": ...}` (`HTTPException`) or
    `{"code", "message"}` (the central `PyriteError` handler); neither ever
    carries any of the enumeration-sensitive field names above (they are all
    success-envelope fields), so checking for `"detail"`/`"code"` at the top
    level is enough to tell the two apart without a second lookup table.
    """
    normalised = normalize(body, tmpdir=tmpdir)
    fields = REST_ENUMERATION_SENSITIVE_FIELDS.get((method, path))
    if (
        fields
        and isinstance(normalised, dict)
        and "detail" not in normalised
        and not ("code" in normalised and "message" in normalised)
    ):
        normalised = dict(normalised)
        for field in fields:
            if field in normalised:
                normalised[field] = NORMALISED_REST_ENUMERATION_CONTENT
    return normalised
