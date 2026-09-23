- **MCP write tools now enforce the per-KB write permission REST enforces.**
  Over `/mcp`, a session user's global role chose which tools were offered,
  but nothing checked their role on the KB a write tool targeted, so a user
  whose effective role on a KB was `read` (through its `default_role` or an
  explicit grant) could still create, update and delete entries in it --
  `kb_create`, `kb_update`, `kb_delete`, task tools and every write-tier
  plugin tool. The same writes over REST were already refused. A scoped MCP
  connection now resolves the KBs it may write through the same per-KB rule
  REST uses, and every tool registered above the read tier is refused
  (`FORBIDDEN`) unless each KB it names is writable. Operator API keys and
  global admins are unaffected. Plugin read tools are now registered at the
  read tier on write- and admin-tier servers, so they are rate-limited as
  reads, and the journalism-investigation plugin's `investigation_search_all`
  and `investigation_status`, which only read, are now read-tier tools. **Operators:** if you run the HTTP MCP endpoint with users whose
  per-KB role is narrower than their global role, review recent changes to
  those KBs (`git log` in each KB) for writes those users should not have
  made.
