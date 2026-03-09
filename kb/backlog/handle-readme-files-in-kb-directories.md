---
id: handle-readme-files-in-kb-directories
title: Handle README.md Files in KB Directories Gracefully
type: backlog_item
tags:
- enhancement
- indexing
- dx
kind: feature
status: accepted
priority: medium
effort: S
---

## Problem

KB directories commonly contain `README.md` files (for GitHub display, onboarding, etc.) that lack YAML frontmatter. The indexer tries to parse these as entries, fails, and emits noisy error traces:

```
Entry load failed for .../blank/README.md, trying EventEntry fallback
ValueError: Invalid entry format: missing YAML frontmatter
Could not parse .../blank/README.md: Invalid entry format: missing YAML frontmatter
```

This happens for every KB with a README and on every sync. It's confusing for new users and clutters logs.

## Options

Several approaches, not mutually exclusive:

1. **Skip README.md by default** — The indexer ignores files named `README.md` (case-insensitive). Simple, handles the 90% case. READMEs are for GitHub/humans, not for the KB index. Could be overridden via config if someone genuinely wants to index a README.

2. **Frontmatter-optional README type** — Add a `readme` entry type that auto-generates an ID from the directory name and has no required frontmatter. The indexer detects `README.md` files and wraps them in a synthetic entry. Pros: READMEs become searchable KB content. Cons: adds complexity, READMEs may not fit the entry model well.

3. **Add frontmatter to existing READMEs** — Put valid frontmatter on each README.md so it indexes normally. Simple but requires manual maintenance and fights the convention that READMEs are plain markdown.

4. **Configurable ignore patterns** — Add an `ignore` list to kb.yaml (e.g., `ignore: ["README.md", "*.draft.md"]`). More general solution that also handles other non-entry files. README.md would be in the default ignore list.

## Recommendation

Option 4 (configurable ignore patterns) with `README.md` in the default list. It solves the immediate problem and generalizes to other cases. Option 1 is the minimum viable fix if we want something quick.

## Success Criteria

- `pyrite index sync` produces no errors/warnings for README.md files
- READMEs in demo KBs (blank, boyd, wardley, kb-ideas) don't trigger parse failures
- Users can override the behavior if they want READMEs indexed
