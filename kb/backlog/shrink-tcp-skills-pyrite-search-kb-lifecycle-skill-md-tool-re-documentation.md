---
id: shrink-tcp-skills-pyrite-search-kb-lifecycle-skill-md-tool-re-documentation
title: Shrink tcp-skills pyrite-search/kb-lifecycle SKILL.md tool re-documentation
type: backlog_item
tags:
- docs
- agent-dx
- tcp-skills
importance: 5
kind: task
status: proposed
priority: medium
effort: S
rank: 0
---

## Problem

docs-operational-contracts-travel-with-tool item 7 (the last step in
its own sequence) calls for shrinking pyrite-search and kb-lifecycle
SKILL.md files in ~/tcp-skills once the canonical in-repo docs exist
to point at instead (docs/json-contracts.md, `pyrite orient`'s
operational_contracts field, kb/standards/api-design.md -- all landed
this session).

Investigated the actual files (2026-07-03):

- **pyrite-search/SKILL.md**: mostly domain knowledge (KB inventory,
  capturecascade.org URL conventions, 4-step research strategy) --
  only ~5 lines (the "Key flags" line + CLI Search Tools section) are
  genuine tool re-documentation that could instead point at
  `pyrite search --help`. Smaller edit than the ticket implied.
- **kb-lifecycle/SKILL.md**: has a CONFIRMED stale-syntax bug, exactly
  as the parent ticket predicted ("already stale on `orient` syntax").
  Verified against real `--help` output: `pyrite orient {kb-name}` and
  `pyrite kb health {kb-name}` are wrong -- both require `--kb`/`-k`
  as a named option, not positional. `index sync`/`index build`/
  `recent` also use `--kb`/`-k`, not positional, contrary to how the
  doc shows them. `qa validate` takes an optional positional
  `[KB_NAME]`; `qa assess`/`qa stale` take a required positional
  `KB_NAME` -- so the doc's uniform `{kb-name}` positional treatment
  is right for some qa subcommands and wrong for others.

## Why not done this session

~/tcp-skills is a separate git repo with its own uncommitted
in-progress work on a non-default branch
(`retier-conductors-sonnet5-opus48`) at the time this was
investigated -- editing it risked colliding with concurrent work in
a repo this session has no visibility into. Per the multi-session git
hazard now documented in pyrite's own CLAUDE.md, the safe default is
not to touch another actively-modified repo without checking in
first; an AskUserQuestion on scope went unanswered (60s timeout).

## Fix

1. Fix the confirmed stale syntax in kb-lifecycle/SKILL.md (orient,
   kb health, index sync, index build, recent all need `--kb`/`-k`).
2. Replace the "Key flags" / CLI Search Tools re-documentation section
   in pyrite-search/SKILL.md with a pointer to `pyrite search --help`
   and `docs/json-contracts.md` (once published somewhere tcp-skills
   consumers can reach it -- may need a README link or a copy, since
   tcp-skills doesn't vendor the pyrite repo directly).
3. Verify no other pyrite CLI commands referenced in tcp-skills have
   drifted the same way (this investigation only checked the two
   files named in the parent ticket).

## Acceptance criteria

- kb-lifecycle/SKILL.md's command examples all match real `--help`
  output (verified command-by-command, not just orient).
- pyrite-search/SKILL.md's flag documentation is replaced with a
  pointer, not duplicated content.
