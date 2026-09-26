- Error codes now live on the exception classes (`pyrite/exceptions.py`)
  instead of being decided separately per transport, closing the gap where
  the same exception answered a different code on different surfaces.

  **REST.** A `PyriteError` that reaches the central handler now answers
  in the same `{"detail": {"code", "message", "retryable", "hint"?}}` shape
  every `HTTPException(detail={...})` site already used. **Before this
  release the central handler answered a flat `{"code", "message"}` body**,
  so a client reading `body["code"]` from those responses must now read
  `body["detail"]["code"]`. Status codes are unchanged. Most responses are
  unaffected: 91 of 124 `HTTPException` sites already answer their own
  code in the `detail` shape and are untouched. The code string changes
  for these classes when the central handler answers them:
  - `UndeclaredTypeError`, `EntryExistsError`, `SchemaViolationError` and
    `InvalidGitRefError` now answer their own codes (`UNDECLARED_TYPE`,
    `ENTRY_EXISTS`, `SCHEMA_VIOLATION`, `INVALID_REF`) where the central
    handler previously answered the generic `VALIDATION_ERROR` for all
    four (their status codes are unchanged).
  - `ClipperBlockedHostError` now answers `CLIPPER_BLOCKED_HOST` where the
    central handler previously answered `INTERNAL_ERROR` (both 500).
  - A bare `ValidationError` (and any subclass without its own code, e.g.
    `TruncatedBodyError`) answered by the central handler now answers
    `VALIDATION_FAILED` where it previously answered `VALIDATION_ERROR`.
    `VALIDATION_FAILED` is the spelling REST's write pipeline
    (`server/endpoints/write_refusal.py`, bulk per-item results) and MCP
    already used; the central handler's disagreeing second spelling is
    gone.

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

  **CLI.** Core CLI write commands have not adopted the class-level codes
  yet (`cli_error_from`, added by this release, has no call site), so their
  output is unchanged; wiring them will emit the exception's own code (e.g.
  `ENTRY_NOT_FOUND`) where several commands today emit the generic `ERROR`
  (`#481`). The **extension** CLI create commands (zettelkasten,
  software-kb) do change: they read the exception's `error_code` and fell
  back to `CREATE_FAILED`, and since every `PyriteError` now carries a code
  (the base's is `INTERNAL_ERROR`), a failed create there now reports the
  exception's own code instead of `CREATE_FAILED`.

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
  unaffected. The fixed message replaces the raw text wherever these
  classes reach a caller:
  - MCP: the `error` of `kb_orient`, `kb_create`, `kb_bulk_create` (whole
    call and each item), `kb_update`, `kb_delete`, `kb_link`,
    `task_decompose`, `task_checkpoint`, schema set, `kb_commit`,
    `kb_push` and `kb_registry_add`; the social create tool, the
    journalism-investigation create/log-source/promote tools, and the
    software-kb reorder and backlog-create tools.
  - REST: each item of `POST /api/entries/import`, publish's
    `push_error`, the batch link write-back's per-position error, and the
    index job `error` field (admin `GET /index/jobs`, MCP
    `kb_index_job_status`).
  - CLI: `zettel new`, `sw new-adr` and bulk create print the fixed
    message; the raw text still reaches the terminal through the log on
    stderr.

  (ADR-0037 theme 2)
