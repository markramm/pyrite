# Pyrite Gotchas and Known Pitfalls

Things that look right but will bite you. Read this before your first extension or before debugging a confusing issue.

## Hooks: DB Access via PluginContext

**Status:** Resolved via PluginContext dependency injection.

Plugins receive a `PluginContext` via `set_context(ctx)` at startup. The context provides `ctx.db`, `ctx.config`, and `ctx.services`. Hooks can access the DB through the plugin instance's stored context:

```python
class MyPlugin:
    def set_context(self, ctx):
        self._ctx = ctx

    def get_hooks(self):
        return {"after_save": [self._after_save]}

    def _after_save(self, entry, context):
        self._ctx.db.execute_sql("UPDATE ...")  # Works
```

**Gotcha:** Hooks defined as standalone functions (not methods) still don't have DB access. Always use instance methods that can reach the plugin's stored context.

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

## _resolve_entry_type Silently Maps Core Types to Plugin Subtypes

When you call `kb_create(type="event")`, the entry type gets silently resolved to a plugin subtype (e.g., `cascade_event`) if a plugin provides one. This happens in `kb_service.py:_resolve_entry_type()`.

**Consequences:**
- `type(entry).__name__` won't be `Event` — it'll be `CascadeEvent`
- The entry's dataclass fields come from the plugin class, not the core class
- `isinstance(entry, Event)` still works (inheritance), but exact type checks fail

**When this bites you:** Writing tests that construct entries directly vs going through `build_entry()`. Direct construction uses the core class; the factory uses the resolved plugin class. Behavior differs if the plugin overrides `from_frontmatter` or adds custom fields.

## build_entry: Unknown kwargs Go to metadata, Not Top-Level Frontmatter

The `build_entry()` factory in `factory.py` introspects the resolved entry class's dataclass fields. Any kwargs that aren't recognized dataclass fields get collected into the `metadata` dict.

**Consequence:** If you add a new field to a plugin entry class's dataclass but forget to handle it in `from_frontmatter()`, the field's value silently ends up in `metadata` instead of the proper field. The entry appears to save correctly but the field is "invisible" to code that reads the dataclass attribute.

**How to verify:** After creating an entry, check both `entry.my_field` and `entry.metadata.get("my_field")`. If the value is in metadata but not the field, your `from_frontmatter()` isn't extracting it.

## Hybrid Search Pagination: Both Legs Must Over-Fetch

`_hybrid_search()` in `search_service.py` uses Reciprocal Rank Fusion to combine keyword and semantic results. Both legs fetch `max(limit * 2, offset + limit)` candidates because:

1. RRF needs full ranked lists from both legs to compute scores correctly
2. The fused result set is sliced at `[offset : offset + limit]` after scoring
3. If either leg fetches too few candidates, pagination at high offsets returns empty

**When this bites you:** Adding a new search mode or modifying the hybrid pipeline. Always ensure both legs fetch enough to cover `offset + limit`.
