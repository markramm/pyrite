# Encyclopedia

Example plugin. `encyclopedia` exists to show how a Pyrite plugin adds entry
types, CLI commands, MCP tools and a preset; it is a reference for plugin
authors, not a supported product.

## What this example demonstrates

A Wikipedia-inspired collaborative knowledge base, built as a Pyrite plugin:

- **Entry types:** `article` (with a `quality` level, `review_status` and
  `protection_level`) and `talk_page`.
- **CLI commands:** `pyrite wiki`.
- **MCP tools:** `wiki_quality_stats`, `wiki_review_queue`, `wiki_stubs`
  (read tier); `wiki_submit_review`, `wiki_assess_quality` (write tier);
  `wiki_protect` (admin tier) — showing tier-gated tool registration.
- **Workflow:** `article_review`, a draft -> under_review -> published
  state machine.
- **Custom DB tables:** an `encyclopedia_review` table, prefixed per the
  extension-development standard.
- **Preset:** `encyclopedia`, for `pyrite init --template encyclopedia`.

Read `extensions/encyclopedia/src/pyrite_encyclopedia/plugin.py` for the
full `EncyclopediaPlugin` implementation, and `entry_types.py`,
`workflows.py`, `validators.py` for how quality assessment and review are
modeled.

## Install

```bash
pip install -e extensions/encyclopedia
```

## See also

`kb/standards/extension-development.md` — the package layout and rules this
example follows, and the standard a new plugin author should read alongside
this code.
