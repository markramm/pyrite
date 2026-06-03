---
id: task-create-tags-flag
type: backlog_item
title: "Add `--tags` flag to `pyrite task create` for frontmatter tag-list construction"
kind: feature
status: proposed
priority: low
effort: S
tags: [task-system, cli, ux, paper-cut]
---

## Problem

`pyrite task create` accepts `--priority`, `--assignee`, `--body`, but **not `--tags`**. The standard way to populate the tags list in task frontmatter today is to embed the tag list in the body text and rely on downstream parsing — which is brittle and doesn't surface in `pyrite tags` aggregation.

Documented friction (2026-06-02): a conductor session filed 28 Mark-theme child tasks via a shell loop. Each task needed tags like `kleptocracy / comparative-resistance / case-study / track-a` for downstream conductor non-overlap detection. The shell loop had to embed tags in the body as "TAGS: kleptocracy, comparative-resistance, case-study, track-a" lines because no `--tags` flag exists; the tags then don't appear in `pyrite tags` listing and aren't queryable through normal tag-search routes.

This is structurally distinct from automation-friction — it's a paper-cut in the schema-CLI alignment. The frontmatter has a tags field; the create command can't populate it.

## Proposed solution

```
pyrite task create "Title" -k cascade-research \
  --priority 7 \
  --assignee investigation-conductor:case-study-poland-2026-06-02 \
  --tags kleptocracy,comparative-resistance,case-study,track-a \
  --body "Task body text"
```

Behavior:
- Comma-separated string, no spaces required
- Empty string OK (no tags)
- Writes to `tags:` field in frontmatter as YAML list
- Tag names normalized (lowercase, hyphen-separated; same convention as `pyrite tags` aggregation)
- Multiple `--tags` invocations append (so `--tags foo --tags bar,baz` yields `[foo, bar, baz]`) — or pick one convention

## Related

- `task-update-comment-flag.md` — similar shape (CLI flag → frontmatter field)
- Consider whether `pyrite task update --tags add:foo,remove:bar` syntax would be useful (probably yes; file separately if anyone wants it)

## Effort

S — single flag, standard parsing, schema field already exists.
