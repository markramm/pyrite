- Error codes now live on the exception classes (`pyrite/exceptions.py`)
  instead of being decided separately per transport. Where MCP's code used
  to differ from REST's (`NOT_FOUND` vs `ENTRY_NOT_FOUND`/`KB_NOT_FOUND`,
  `READ_ONLY` vs `KB_READ_ONLY`, `VALIDATION_FAILED` vs `VALIDATION_ERROR`,
  `CONFIG_ERROR` vs `CONFIG_CONFLICT`, `REQUEST_REFUSED` vs `STORAGE_ERROR`,
  and others), MCP now reports REST's code and carries its own previous
  code for one release in a new `legacy_error_code` field, so an existing
  MCP caller matching on the old string keeps working through the
  transition. The next release removes `legacy_error_code` and MCP's code
  becomes the same string REST reports. REST's wire shape is unchanged
  (`{"detail": {"code", "message", "retryable", "hint"?}}`); `docs/json-contracts.md`
  now documents it accurately. (ADR-0037 theme 2)
