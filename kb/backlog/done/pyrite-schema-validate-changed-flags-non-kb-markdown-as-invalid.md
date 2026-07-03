---
id: pyrite-schema-validate-changed-flags-non-kb-markdown-as-invalid
title: pyrite schema validate --changed flags non-KB markdown as invalid
type: backlog_item
tags:
- bug
- cli
- pre-commit
importance: 5
status: done
priority: 2
effort: S
rank: 0
---

## Problem

`pyrite schema validate --changed` (the pre-commit hook backing it, `pyrite-schema-validate`) collects every changed `.md` file in the repo via `git diff --name-only` with no KB-path filtering, then validates each one as if it were a KB entry. Any non-KB markdown that changes in the same commit -- docs, `.claude/skills/*.md`, top-level `README.md`-adjacent files -- gets flagged as an error ("No YAML frontmatter found") even though it was never meant to be a KB entry.

Found while fixing ci-make-green-and-load-bearing: the hook itself was also broken (`python -m pyrite` -- `pyrite` has no `__main__.py`, so this has never actually run; fixed separately in that ticket to call the `pyrite` console script directly). Once that was fixed, the first real run immediately flagged `.claude/skills/pyrite-dev/gotchas.md` as invalid.

Root cause: `_get_git_changed_md_files()` in `pyrite/cli/schema_commands.py` returns all changed `.md` paths repo-wide with `git diff --name-only --diff-filter=ACMR` (staged + unstaged), never filtered against `config.knowledge_bases` paths before being handed to the validator.

## Fix

Filter `_get_git_changed_md_files()`'s result to paths that resolve under a configured KB's `path` before validating -- same pattern already used a few lines later in `schema_validate()` for schema *detection* (`f.resolve().relative_to(kb.path.resolve())`), just apply it as an inclusion filter, not only for schema lookup.

## Acceptance criteria

- `pyrite schema validate --changed` with a change to a non-KB markdown file (e.g. a doc, a skill file) does not flag it.
- A change to a real KB entry with missing frontmatter is still caught.
- Regression test: stage/change one KB `.md` file (with a validation error) and one non-KB `.md` file (no frontmatter, e.g. a plain doc) in the same commit; assert only the KB file is reported.
