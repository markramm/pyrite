# Social

Example plugin. `social` exists to show how a Pyrite plugin adds entry types,
CLI commands, MCP tools and a preset; it is a reference for plugin authors,
not a supported product.

## What this example demonstrates

An Everything2-inspired community knowledge base, built as a Pyrite plugin:

- **Entry types:** `writeup` (a user-authored piece — essay, story, review,
  how-to or opinion) and `user_profile`.
- **CLI commands:** `pyrite social`.
- **MCP tools:** `social_top`, `social_newest`, `social_reputation` (read
  tier); `social_vote`, `social_post` (write tier).
- **Lifecycle hooks:** `before_save` enforces author-only editing,
  `after_save` updates writeup counts, `after_delete` adjusts reputation.
- **Custom DB tables:** vote and reputation-log tables, prefixed
  `social_*` per the extension-development standard.
- **Preset:** `social`, for `pyrite init --template social`.

Read `extensions/social/src/pyrite_social/plugin.py` for the full
`SocialPlugin` implementation, and `entry_types.py`, `hooks.py`,
`validators.py`, `tables.py` for how each piece is built.

## Install

```bash
pip install -e extensions/social
```

## See also

`kb/standards/extension-development.md` — the package layout and rules this
example follows, and the standard a new plugin author should read alongside
this code.
