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

## Connection Management: session vs _raw_conn

`PyriteDB` has **two separate** database connections that don't share transaction state:

- `db.session` — SQLAlchemy ORM session (used by `execute_sql()`, ORM models)
- `db._raw_conn` — Raw `sqlite3` connection (used by `conn` property, legacy code)

**The gotcha:** ORM writes via `session` are NOT visible to `_raw_conn` until committed. They use different connections from different engines.

```python
# This will NOT see uncommitted ORM writes:
db._raw_conn.execute("SELECT * FROM entry WHERE id = ?", (entry_id,))

# This WILL see ORM writes (goes through session):
db.execute_sql("SELECT * FROM entry WHERE id = ?", (entry_id,))
```

**Rules:**
- Use `db.execute_sql()` for reads that need to see ORM writes
- `db.conn` property returns `_raw_conn` — treat it as deprecated
- In tests, if you must use `_raw_conn`, ensure prior ORM operations are committed first

## Hybrid Search Pagination: Both Legs Must Over-Fetch

`_hybrid_search()` in `search_service.py` uses Reciprocal Rank Fusion to combine keyword and semantic results. Both legs fetch `max(limit * 2, offset + limit)` candidates because:

1. RRF needs full ranked lists from both legs to compute scores correctly
2. The fused result set is sliced at `[offset : offset + limit]` after scoring
3. If either leg fetches too few candidates, pagination at high offsets returns empty

**When this bites you:** Adding a new search mode or modifying the hybrid pipeline. Always ensure both legs fetch enough to cover `offset + limit`.

## `list_files()` Skips Files with "template" in the Filename

`KBRepository.list_files()` (repository.py:244) filters out any `.md` file whose name contains the substring `"template"`. This is a broad substring check, not a prefix/suffix match.

**When this bites you:** Creating KB entries with filenames like `templated-foo.md`, `template-bar.md`, or `path-templates.md`. They silently won't be indexed. Rename to avoid the word entirely (e.g., `dynamic-foo.md`).

## Closing a Backlog Item: Use `status=done`, and Beware Auto-Replacement to `kb/notes/`

Two traps when closing a `backlog_item`, both load-bearing:

**Trap 1 — the status value.** Use `status=done`, **never** `status=completed`.
`completed` is off-enum for backlog items (the type declares `proposed`/`planned`/
`in_progress`/`done`; the board maps both `done` and `completed` to the Done column,
which masks the problem). It passes silently but drifts the board — this exact mistake
once stranded 75 items on an undetected `completed` status (see `index.py:703`). As of
this writing 380 items use `done` and 0 use `completed`. `done` is canonical.

**Trap 2 — file placement.** Largely **fixed** (commit on the
`update-relocates-entry-to-type-default-subdir` ticket): `pyrite update` now preserves an
entry's existing subdirectory instead of relocating it to the type default. A
`backlog_item` already in `kb/backlog/` or `kb/backlog/done/` **stays put** on
`status=done` — no more manual `mv` after updates.

Residual nuance: `pyrite create -t backlog_item` still lands new items in `kb/notes/`
(not `kb/backlog/`), because `backlog_item` isn't a schema-declared type in pyrite's
`kb.yaml` and falls to the generic default. So the workflow is:

```bash
# create lands in kb/notes/ — move it into the backlog convention once:
git mv kb/notes/<id>.md kb/backlog/<id>.md   # (or kb/backlog/done/ when closing)
.venv/bin/pyrite index sync
```

After that initial placement, updates keep it there. To remove the residual create-side
quirk entirely, declare `backlog_item` with `subdirectory: backlog` in the KB schema.

## `pyrite sw new-adr` Takes a Positional TITLE and Misfiles Without `-k`

Two traps in one command:

1. **`TITLE` is a positional argument, not `--title`.** `pyrite sw new-adr --title "X"`
   fails. Correct: `pyrite sw new-adr "X" -k pyrite --status accepted`. (Note this differs
   from `pyrite create`, which *does* take `--title` — the inconsistency is real.)
2. **Without `-k`, the file is written to `./adrs/` relative to your current directory**,
   not the KB's `kb/adrs/`. The command resolves the KB path only when `--kb` is passed;
   otherwise it falls back to `Path(".")` (`cli.py:135-141` in the software-kb extension).
   It reports `Created ADR-NNNN` and exits 0, so the misplacement is silent — the file is
   never indexed and `pyrite sw adrs` never shows it. The next-number lookup *does* default
   the KB, so you get a correctly-numbered ADR in the wrong place.

**Always pass `-k pyrite`.** If you forget, `mv ./adrs/<file> kb/adrs/`, remove the stray
`./adrs/`, then `pyrite index sync`.

## A `from ... import X` Anywhere Inside a Function Makes `X` Local for the Whole Function

Hit while fixing `search-query-syntax-error-contract`: added `from ..utils.errors import
cli_error` at module level in `search_commands.py`, then added a new `except` branch that
called `cli_error(...)`. Got `UnboundLocalError: cannot access local variable 'cli_error'
where it is not associated with a value` — even though the module-level import should have
made it a global.

Root cause: the `search()` function already had a *local* `from ..utils.errors import
cli_error` inside an earlier `if` branch (a deliberate lazy-import pattern used elsewhere in
this file). Python's scoping is lexical and whole-function: any assignment (including an
`import`) to a name anywhere in a function body makes that name local for the **entire**
function, from its first line — even before the local import statement executes. The
module-level import at the top of the file is shadowed for the whole `search()` function
body, not just after the local import line.

**Fix:** either import at module level only (remove all local imports of that name in the
function), or match the existing lazy-import pattern and add a local import at your new call
site too. Don't mix module-level and local imports of the same name within one function.

**How to catch this:** if you add a module-level import and a function that already does
local (lazy) imports starts raising `UnboundLocalError` on a name you just imported, search
the whole function body (not just nearby) for another `import` of that name.

**Status:** ticketed — backlog item `new-adr-writes-to-cwd-without-kb-flag`.

## `pre-commit run --all-files` Is Repo-Wide, Not Scoped to a Backlog Item's Files

Hit while fixing `ci-make-green-and-load-bearing`: CI's lint step only checks `ruff check
pyrite/ tests/` and `ruff format --check pyrite/ tests/` — so I fixed formatting drift there,
confirmed CI's exact lint step passes, and committed. Then, separately, ran `pre-commit run
--all-files` to verify the newly-installed hooks work. That command has **no directory scope**
— `.pre-commit-config.yaml`'s hooks apply to the whole repo by default (`extensions/`,
`scripts/`, `benchmarks/`, `deploy/`, `kb/*.md`, `ui_streamlit.py`, ...), not just what CI
lints or what the current ticket touches. It auto-fixed 76 ruff errors (some behavioral —
unused-variable removal, not just formatting) and reformatted 66 more files across the repo,
producing an 85-file, 3000+-line diff far outside the ticket's scope, mixed with real (if
minor) behavioral changes I hadn't reviewed.

**Fix:** `git checkout -- <files>` to revert everything the stray run touched, keep only the
intentional change (`pyproject.toml`'s new dependency).

**How to avoid:** when verifying a newly-installed pre-commit hook works, either scope it to
specific files (`pre-commit run --files <paths>`) or just trust `pre-commit install` succeeding
— don't run `--all-files` unless the task is explicitly "clean up the whole repo's pre-commit
compliance." A repo-wide hook run is a different, larger task than a CI-lint-scoped fix.
