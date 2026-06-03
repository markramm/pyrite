---
id: task-cross-kb-query
type: backlog_item
title: "Support cross-KB task queries (`--all-kbs` flag) for multi-KB workflow visibility"
kind: feature
status: proposed
priority: medium
effort: M
tags: [task-system, cli, multi-kb, query, conductor-workflow, ux]
---

## Problem

`pyrite task list -k <kb>` requires explicit KB selection. For users who maintain tasks across multiple KBs (the cascade-research / drafts / detention-pipeline-research / pyrite split is common in Mark's workflow), getting cross-KB visibility requires:

```bash
for kb in cascade-research drafts detention-pipeline-research pyrite; do
  pyrite task list -k $kb --status open --format json | python3 -c "..."
done
```

This is verbose and produces fragmented output. For questions like:
- "What's open P9+ anywhere right now?"
- "Show me all tasks waiting on a Mark editorial decision across all KBs"
- "What did agents file in any KB in the last 24h?"

...there's no clean CLI answer.

This session (2026-06-02) hit it specifically when filing the Bannon-Epstein discipline-flag (P9 in drafts KB) and tracking it alongside cascade-research-side work — the conductor couldn't easily check "any P9+ tasks I should know about across all my KBs."

## Proposed solution

Add `--all-kbs` flag (and/or `--kbs <list>` for multi-KB-but-not-all):

```
pyrite task list --all-kbs --status open --priority 9+
pyrite task list --kbs cascade-research,drafts,pyrite --status open
pyrite task list --all-kbs --assignee 'mark-*' --status open
```

Output includes a `kb:` column so the user knows which KB each result came from. JSON output includes the KB name on each record.

Design considerations:
- KB-discovery: respect `~/.pyrite/config.yaml` registered-KBs list (whatever's registered there is queryable)
- Performance: cross-KB queries fan out; consider whether to parallelize internally
- Tag scoping: tag names may collide across KBs (`detention-pipeline` may mean different things in different KBs); document the convention

## Related

- `consistent-kb-flag-across-commands.md` — paper-cut adjacent; same `-k` consistency story
- The dual-registry friction Mark already documented in `bug_pyrite_kb_create_dual_registry` (user memory) suggests the `~/.pyrite/config.yaml` + `~/kb/config.yaml` split needs attention here too
- Pairs with `task-status-children-tree-view.md` — could `pyrite task status --children` cross-KB-resolve children whose parent is in another KB?

## Effort

M — fan-out execution + result aggregation + KB-column display + JSON shape decision. Non-trivial but bounded.
