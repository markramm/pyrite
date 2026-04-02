---
id: sw-new-adr-dry-run-bug
title: "Bug: `pyrite sw new-adr` prints instructions but does not create file"
type: backlog_item
tags: [software-kb, cli, bug]
kind: bug
status: done
priority: high
effort: S
---

# Bug: `pyrite sw new-adr` prints instructions but does not create file

## Problem

Running `pyrite sw new-adr "Some Title" --status accepted` prints the file path and frontmatter to stdout but does not actually create the markdown file on disk. The user is left to create the file manually.

## Expected Behavior

The command should create the ADR file in the KB's `adrs/` directory with correct frontmatter and a body template (Context/Decision/Consequences sections), then index the new entry.

## Steps to Reproduce

```bash
pyrite sw new-adr "Test ADR" --status proposed
# Output shows file path and frontmatter but no file is created
ls kb/adrs/  # No new file
```

## Fix

The `new_adr` command in `extensions/software-kb/src/pyrite_software_kb/cli.py` needs to actually write the file using KBRepository or KBService, not just print instructions.
