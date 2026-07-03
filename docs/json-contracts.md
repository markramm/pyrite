# JSON Contracts

Canonical shapes returned by the pyrite CLI (`--format json`), MCP tools,
and REST API. Written down here so agents and extension authors can rely
on a stable contract instead of re-deriving it from source or an
operator's memory — see `docs-operational-contracts-travel-with-tool`.

## Error shape

Every error surface (CLI `cli_error`, MCP tool `_error`, REST
`PyriteError` handler) returns the same structure:

```json
{
  "error": "human-readable message",
  "error_code": "MACHINE_CODE",
  "suggestion": "optional fix hint",
  "retryable": false
}
```

- `error` — always present, human-readable.
- `error_code` — always present, machine-readable (`QUERY_SYNTAX`,
  `KB_NOT_FOUND`, `INVALID_TIER`, etc.). Match on this, not on `error`
  text.
- `suggestion` — omitted entirely when there's no applicable fix hint.
  Don't assume the key exists.
- `retryable` — always present. `true` means the same request could
  succeed on retry (e.g. a transient lock); `false` means the request
  itself needs to change first (e.g. a malformed query).

Source of truth: `pyrite/utils/errors.py` (`build_error`).

## Search result envelope

```json
{
  "query": "the search string",
  "count": 3,
  "results": [ { "...": "entry dict" } ]
}
```

`count` is `len(results)`, not a total-matches count — there is no
separate total. Paginated list endpoints (`kb_list_entries`,
`kb_recent`, `kb_backlinks`, `kb_tags`) instead include `has_more: bool`
(`True` when the page was full, i.e. more may exist past this page —
not an exact remaining count).

## Entry envelope

A single entry (`kb_get`, `pyrite get`) returns the entry dict directly
— not wrapped in an `{"entry": ...}` key. `outlinks` and `backlinks` are
included when resolvable.

## Body truncation

Entries with large bodies may come back chunked. When truncated, the
entry dict gains:

```json
{
  "body": "...(chunk, not the full body)...",
  "body_truncated": true,
  "body_length": 15234,
  "body_offset": 0,
  "body_chunk_size": 4000
}
```

`body_truncated` is only present when truncation actually happened —
don't assume its absence means anything other than "not truncated".
Use `kb_read_body` (offset-based continuation) to read past the first
chunk; stop once `body_offset + body_chunk_size >= body_length`.

## Exit codes (CLI)

- `0` — success.
- `1` — any error surfaced via `cli_error` (parses the JSON error shape
  above from stdout/stderr depending on `--format`).

## `--format` defaults

Most commands default to `--format json`. A few interactive/status
commands (`task` subcommands, `config`) default to a rich terminal
view instead — pass `--format json` explicitly when scripting against
those.

## Related contracts

These aren't JSON shapes but are part of the same "don't relearn this
the hard way" surface — also returned in `pyrite orient`'s
`operational_contracts` field:

- **Indexing**: entries are only searchable once indexed. Writes made
  directly to files under a KB's path (bypassing `pyrite create`/
  `update`) need `pyrite index sync` afterward — incremental and cheap.
- **Search auto-quote rule**: special-char tokens (hyphens, dots,
  colons) are auto-quoted only when the query has no `AND`/`OR`/`NOT`
  operator and no existing quote. Once you use an operator or a phrase
  quote, quote special-char tokens yourself or the query can fail with
  `error_code: QUERY_SYNTAX` (deterministic, not retryable).
- **Task claims**: atomic. A lost race means the task is already
  claimed by someone else — don't override; re-run the task list and
  pick a different item.
