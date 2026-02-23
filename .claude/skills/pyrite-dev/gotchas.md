# Pyrite Gotchas and Known Pitfalls

Things that look right but will bite you. Read this before your first extension or before debugging a confusing issue.

## Hooks Cannot Access DB Instance

**Status:** Known gap, backlog item `hooks-db-access-gap`

Lifecycle hooks receive `(entry, context)` where context has `kb_name`, `user`, `kb_schema`, `operation`. But **not the DB instance**. If your hook needs to query or update the database, you're stuck.

**Current workaround:** Log the intended action and handle it elsewhere, or create a new DB connection inside the hook (not ideal):

```python
def after_save_update_counts(entry, context):
    # Can't do: context["db"].update(...)
    # Workaround: log it
    logger.info("Should update count for %s", entry.id)
```

**Future fix:** Plugin dependency injection (backlog item `plugin-dependency-injection`) will provide DB access to hooks.

## generate_entry_id Is Title-Based

`generate_entry_id("My Great Note")` returns `"my-great-note"`. This means:

- Two entries with the same title get the same ID
- Changing a title changes the ID
- Empty title → empty ID (which can cause silent issues)

**Always check** `meta.get("id", "")` first. Only call `generate_entry_id()` as fallback:

```python
entry_id = meta.get("id", "")
if not entry_id:
    entry_id = generate_entry_id(meta.get("title", ""))
```

## Validator Signature: 3 Arguments

Validators receive `(entry_type, data, context)` — not an Entry object, raw dicts.

```python
# Correct
def validate_my_type(entry_type: str, data: dict, context: dict) -> list[dict]:
    ...

# Wrong — will crash at runtime
def validate_my_type(entry: Entry) -> list[dict]:
    ...
```

The `context` dict contains: `kb_name`, `kb_schema`, `user`, `existing_entry` (for updates).

## Plugin Validators Always Run

In `pyrite/schema.py`, plugin validators run for **all entries** during schema validation, not just entries of the plugin's declared types. This is by design — it allows cross-type validation rules.

**Consequence:** Your validator MUST check `entry_type` and return `[]` for types it doesn't handle:

```python
def validate_my_type(entry_type, data, context):
    if entry_type != "my_type":
        return []  # CRITICAL: don't validate other types
    # ... actual validation
```

If you forget this check, your validator will generate errors for every entry in the KB.

## DB Table Names Can Collide

Plugin tables all live in the same SQLite database. If two plugins define a table with the same name, one will silently override the other.

**Rule:** Prefix table names with your extension name:

```python
# Good
{"name": "encyclopedia_review", ...}

# Bad — might collide
{"name": "review", ...}
```

## CLI Commands: Lazy Import

Plugin CLI commands should use lazy imports to avoid circular dependencies and slow startup:

```python
def get_cli_commands(self):
    from .cli import my_app  # Lazy import
    return [("my-cmd", my_app)]
```

If you import at module level, the CLI module may try to import pyrite components that aren't ready yet during plugin discovery.

## Two-Tier Durability

Pyrite has two data tiers. Mixing them up leads to data loss or bloated repos.

| Tier | Storage | Git-tracked? | Examples |
|------|---------|-------------|----------|
| **Content** | Markdown + YAML frontmatter | Yes | Entries, links, tags, sources |
| **Engagement** | SQLite (custom DB tables) | No | Votes, reviews, view counts, reputation |

**Content tier:** Knowledge that should survive across clones and be version-controlled. This is the entry's markdown file.

**Engagement tier:** Operational data local to this install. Created via `get_db_tables()`. Lost if the SQLite DB is deleted.

**Rule of thumb:** If a user clones the repo fresh, will they need this data? Yes → content tier. No → engagement tier.

**Common mistake:** Putting engagement data in entry metadata. This bloats the git history with frequent small changes (vote counts, view counts).

## Entry Subclass from_frontmatter

When subclassing an entry type (e.g., `ZettelEntry(NoteEntry)`), your `from_frontmatter` must set **all** base class fields explicitly. You can't rely on `super().from_frontmatter()` because `from_frontmatter` is a `@classmethod` that constructs the object directly.

```python
@classmethod
def from_frontmatter(cls, meta, body):
    # Must include ALL base class fields
    return cls(
        id=...,
        title=...,
        body=body,
        summary=...,
        tags=...,
        sources=parse_sources(meta.get("sources")),
        links=parse_links(meta.get("links")),
        provenance=...,
        metadata=...,
        created_at=parse_datetime(meta.get("created_at")),
        updated_at=parse_datetime(meta.get("updated_at")),
        # Plus your custom fields
        my_field=meta.get("my_field", ""),
    )
```

If you forget a base field, it silently gets the dataclass default (often empty string or None), and the data appears to "vanish" on roundtrip.

## MCP Tool Handlers: Import Inside Handler

MCP tool handlers run in a separate context. Import pyrite modules inside the handler, not at the top of the plugin file:

```python
def _mcp_inbox(self, args):
    # Import here, not at module level
    from pyrite.config import load_config
    from pyrite.storage.database import PyriteDB

    config = load_config()
    db = PyriteDB(config.settings.index_path)
    try:
        # ... use db
        return result
    finally:
        db.close()  # Always close
```

## Pydantic Schemas vs DB Nulls

API response schemas (Pydantic models in `pyrite/server/schemas.py`) must account for NULL values in the database. If a field is typed as `str` but the DB row has `NULL`, Pydantic will raise a validation error.

```python
# Will crash on NULL file_path
class EntryResponse(BaseModel):
    file_path: str

# Correct — handles NULL
class EntryResponse(BaseModel):
    file_path: str | None = None
```

## SPA Fallback Catches API Routes

The static file serving uses SPA fallback: any non-file request returns `index.html`. If an API route isn't mounted with the `/api` prefix, the SPA fallback will catch it and return HTML instead of JSON.

**Symptom:** API endpoint returns `<!DOCTYPE html>` instead of JSON.
**Fix:** Ensure all API routes use the `/api` prefix via `APIRouter(prefix="/api")`.

## Relationship Types Need Inverse Pairs

When defining relationship types in `get_relationship_types()`, always define both the relationship and its inverse:

```python
# Good — both sides defined
{
    "elaborates": {"inverse": "elaborated_by", "description": "..."},
    "elaborated_by": {"inverse": "elaborates", "description": "..."},
}

# Bad — inverse references a type that doesn't exist
{
    "elaborates": {"inverse": "elaborated_by", "description": "..."},
    # Missing elaborated_by definition
}
```

`get_inverse_relation()` in `schema.py` will look up the inverse, and it must exist in the merged relationship types.
