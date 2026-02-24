---
type: component
title: "KB Service"
kind: service
path: "pyrite/services/kb_service.py"
owner: "markr"
dependencies: ["pyrite.config", "pyrite.storage", "pyrite.plugins", "pyrite.models"]
tags: [core, service]
---

# KB Service

`KBService` is the central orchestrator for all knowledge-base and entry operations. It sits between the transport layers (REST API, CLI, MCP) and the storage/indexing layer, enforcing read-only checks, running plugin hooks, and managing ephemeral KB lifecycles.

## Key Files

| File | Purpose |
|------|---------|
| `pyrite/services/kb_service.py` | `KBService` class (all operations) |

## Constructor

```python
KBService(config: PyriteConfig, db: PyriteDB)
```

Stores config, the database handle, and creates an `IndexManager`. The embedding service is lazy-loaded on first use via `_get_embedding_svc()`.

## KB Operations

- **`list_kbs()`** -- Returns all configured KBs with stats (entry count, last indexed).
- **`get_kb(name)`** -- Retrieves a `KBConfig` by name.
- **`get_kb_stats(name)`** -- Delegates to `PyriteDB.get_kb_stats()`.

## Entry CRUD

- **`create_entry(kb_name, entry_id, title, entry_type, body, **kwargs)`** -- Builds an `Entry` via the model factory, runs `before_save` hooks, saves to disk via `KBRepository`, indexes, auto-embeds, then runs `after_save` hooks. Raises `KBNotFoundError` / `KBReadOnlyError`.
- **`update_entry(entry_id, kb_name, **updates)`** -- Loads from disk, applies updates, stamps `updated_at`, runs hooks, saves, re-indexes, and auto-embeds.
- **`delete_entry(entry_id, kb_name)`** -- Runs `before_delete` hooks, deletes from file system and index, then runs `after_delete` hooks.
- **`add_link(source_id, source_kb, target_id, relation, target_kb, note)`** -- Adds a wikilink to the source entry's frontmatter and re-indexes. Deduplicates existing links.

## Query Operations (read-only)

- **`list_entries(kb_name, entry_type, tag, sort_by, sort_order, limit, offset)`** -- Paginated entry listing.
- **`count_entries(kb_name, entry_type, tag)`** -- Filtered count.
- **`get_distinct_types(kb_name)`** -- Unique entry types in the index.
- **`get_timeline(date_from, date_to, min_importance, kb_name)`** -- Date-ordered timeline events.
- **`get_tags(kb_name, limit)`** / **`get_tag_tree(kb_name)`** / **`search_by_tag_prefix(prefix, kb_name)`** -- Tag queries.
- **`get_graph(center, center_kb, kb_name, entry_type, depth, limit)`** -- Graph data for the knowledge-graph visualization.
- **`get_backlinks(entry_id, kb_name)`** / **`get_outlinks(entry_id, kb_name)`** -- Link queries.
- **`get_refs_to(entry_id, kb_name)`** / **`get_refs_from(entry_id, kb_name)`** -- Object-reference queries.

## Cross-KB Resolution

- **`resolve_entry(target, kb_name)`** -- Resolves a wikilink target. Supports `shortname:entry-id` and `kb-name:entry-id` syntax by looking up KBs via `config.get_kb_by_shortname()` or `config.get_kb()`. Falls back to title-based matching.
- **`resolve_batch(targets, kb_name)`** -- Batch-resolves a list of wikilink targets. Cross-KB targets are resolved individually; same-KB targets use an `IN` query for efficiency.
- **`get_wanted_pages(kb_name, limit)`** -- Returns link targets that have no corresponding entry (wanted pages), ordered by reference count.

## Ephemeral KB Lifecycle

- **`create_ephemeral_kb(name, ttl, description)`** -- Creates a temporary KB directory under `workspace_path/ephemeral/`, registers it in config and database with `ephemeral=True`, `ttl`, and `created_at_ts`.
- **`gc_ephemeral_kbs()`** -- Garbage-collects expired ephemeral KBs by checking `created_at_ts + ttl < now`. Removes files, unregisters from DB, and removes from config. Returns list of removed names.

## Hook Integration

- **`_run_hooks(hook_name, entry, context)`** -- Dispatches `before_save`, `after_save`, `before_delete`, `after_delete` to the plugin registry. Passes a `PluginContext` with config, db, kb_name, user, and operation. Pyrite exceptions propagate; other exceptions are logged and swallowed.

## Other Operations

- **`list_entry_titles(kb_name, query, limit)`** -- Lightweight ID+title listing for wikilink autocomplete.
- **`list_daily_dates(kb_name, month)`** -- Dates with daily notes for calendar views.
- **`load_entry_from_disk(entry_id, kb_name)`** / **`index_entry_from_disk(entry, kb_name)`** -- Low-level disk access.
- **`get_entry_versions(entry_id, kb_name, limit)`** / **`get_entry_at_version(entry_id, kb_name, commit_hash)`** -- Git-based version history.
- **`sync_index(kb_name)`** / **`get_index_stats()`** -- Index synchronization and health.
- **`get_setting(key)`** / **`set_setting(key, value)`** / **`get_all_settings()`** / **`delete_setting(key)`** -- Key-value settings store.

## Design Notes

- All mutating operations check `read_only` and raise `KBReadOnlyError` before doing any work.
- Auto-embedding is best-effort: failures are logged at debug level and silently ignored.
- The service never imports `EmbeddingService` at module level; it is lazy-loaded to avoid hard dependency on `sentence-transformers`.
- Hook dispatch uses `PluginContext` dataclass, not a raw dict.

## Consumers

- **REST API endpoints** (`pyrite/server/endpoints/`) -- all entry and KB endpoints delegate to `KBService`.
- **CLI commands** -- entry create/update/delete, index sync, KB management.
- **MCP server tools** -- tool implementations call `KBService` methods.

## Related

- [[config-system]] -- provides `PyriteConfig` consumed by `KBService`
- [[storage-layer]] -- `PyriteDB` and `IndexManager` used internally
- [[plugin-system]] -- hooks dispatched via plugin registry
- [[entry-model]] -- `Entry` objects built by `models.factory.build_entry`
- [[rest-api]] -- primary transport consumer
