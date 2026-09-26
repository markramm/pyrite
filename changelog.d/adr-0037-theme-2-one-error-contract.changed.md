- Error codes now live on the exception classes (`pyrite/exceptions.py`)
  instead of being decided separately per transport, closing the gap where
  the same exception answered a different code on different surfaces.

  **REST.** The central `PyriteError` handler's wire shape is unchanged
  (`{"detail": {"code", "message", "retryable", "hint"?}}`); its status
  codes are unchanged. What changes is which `code` string a handful of
  classes get when the handler answers them directly (most callers see no
  difference, since 91 of 124 `HTTPException` sites already answer their
  own code and are untouched):
  - `UndeclaredTypeError`, `EntryExistsError`, `SchemaViolationError` and
    `InvalidGitRefError` now answer their own codes (`UNDECLARED_TYPE`,
    `ENTRY_EXISTS`, `SCHEMA_VIOLATION`, `INVALID_REF`) where the central
    handler previously answered the generic `VALIDATION_ERROR` for all
    four (their status codes are unchanged).
  - `ClipperBlockedHostError` now answers `CLIPPER_BLOCKED_HOST` where the
    central handler previously answered `INTERNAL_ERROR` (both 500).
  - A bare `ValidationError` (not one of the above) still answers
    `VALIDATION_FAILED`, unchanged from before — REST's write pipeline
    (`server/endpoints/write_refusal.py`, `services/kb_service.py`'s bulk
    per-item results) already used that spelling; only the *central
    handler's* now-fixed second, disagreeing spelling (`VALIDATION_ERROR`)
    is gone.
  - The central handler's body was flat (`{"code", "message"}`, no wrapper,
    no `retryable`) before this release; it is now the same
    `{"detail": {...}}` shape every `HTTPException(detail={...})` site
    already answered.

  **MCP.** Where MCP's code used to differ from REST's (`NOT_FOUND` vs
  `ENTRY_NOT_FOUND`/`KB_NOT_FOUND`, `READ_ONLY` vs `KB_READ_ONLY`,
  `CONFIG_ERROR` vs `CONFIG_CONFLICT`/`CONFIG_SAVE_REFUSED`,
  `REQUEST_REFUSED` vs `STORAGE_ERROR`/`PLUGIN_ERROR`, and
  `VALIDATION_FAILED` vs `INVALID_FRONTMATTER` for `FrontmatterError`
  specifically), MCP now reports REST's code and carries its own previous
  code for one release in a new `legacy_error_code` field, so an existing
  MCP caller matching on the old string keeps working through the
  transition. The next release removes `legacy_error_code` and MCP's code
  becomes the same string REST reports. `kb_bulk_create`'s and
  `POST /api/entries/import`'s per-item results, and every extension's
  `CREATE_FAILED` fallback, now emit the exception class's own code the
  same way — for the common case (a bare `ValidationError`, e.g. a missing
  title) that code is `VALIDATION_FAILED`, unchanged.

  **CLI.** No CLI write command has adopted the new class-level codes yet
  (`cli_error_from`, added by this release, has no call site); the CLI's
  visible behavior is unchanged in this release. A future change wiring
  CLI commands to `cli_error_from` will emit the exception's own code
  (e.g. `ENTRY_NOT_FOUND` for a missing entry) where several commands
  today emit the generic `ERROR` (`#481`).

  **Server log.** The central handler's Python logger name changed from
  `pyrite.server.api` to `pyrite.server.errors` (the handler moved to its
  own module); anything grepping or filtering server logs by logger name
  for this handler's lines needs to match the new name.

  **`StorageError`, `PluginError` and `ConfigError`** now have a fixed,
  safe `public_message` (ADR-0037 §3) shown over REST and MCP instead of
  `str(exc)`, which could carry server-side detail (a database driver's
  own text, a plugin's traceback fragment, a real filesystem path) at some
  raise sites; the real detail still reaches the server log. Their
  subclasses that already had their own `public_message`
  (`ConfigSaveRefusedError`/`ConfigFileUnreadableError`, #377) are
  unaffected. The CLI's generic error path does not read `public_message`
  at all (see above), so this is a REST/MCP-only visible change for now.

  (ADR-0037 theme 2)
