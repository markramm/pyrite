---
id: pyrite-ci-command
title: "pyrite ci — Schema + QA Validation for CI/CD"
type: backlog_item
tags:
- feature
- corporate
- ci-cd
- qa
kind: feature
priority: medium
effort: S
status: planned
links:
- permissions-model
- qa-agent-workflows
- roadmap
---

## Problem

Corporate teams need enforcement at the git layer — PR checks that validate schema compliance and QA rules before merging. Currently, Pyrite validates on write through the API/CLI, but there's no single command optimized for CI pipelines. Teams want to add Pyrite validation to their GitHub Actions / GitLab CI the same way they add linting.

## Solution

A `pyrite ci` CLI command that runs all schema and QA validation checks, outputs machine-readable results, and exits non-zero on failure. Teams add one line to their CI config.

### Usage

```bash
# In GitHub Actions or any CI pipeline
pyrite ci                          # validate all KBs in the repo
pyrite ci --kb research            # validate specific KB
pyrite ci --format json            # machine-readable output
pyrite ci --severity error         # only fail on errors, not warnings
```

### What It Validates

1. **Schema compliance**: All entries conform to their type definitions (required fields, field types, controlled vocabulary)
2. **QA structural rules**: Missing titles, empty bodies, broken links, orphans, invalid dates, importance range
3. **Extension validators**: Any custom validators from installed extensions
4. **Frontmatter integrity**: Valid YAML, recognized types, no unknown required fields

### Output

```
pyrite ci — 3 KBs, 247 entries validated
  research-kb: 142 entries, 0 errors, 3 warnings
  project-kb: 89 entries, 1 error, 0 warnings
    ERROR: kb/backlog/stale-item.md — missing required field 'priority'
  notes-kb: 16 entries, 0 errors, 0 warnings

Result: FAIL (1 error)
```

### GitHub Action (future convenience)

```yaml
# .github/workflows/pyrite-ci.yml
- uses: pyrite/ci-action@v1
  with:
    severity: error
```

## Prerequisites

- QA Phase 1 (structural validation) — already done
- Schema validation on write paths — already done
- This is mostly wiring existing validation into a CI-optimized command

## Success Criteria

- `pyrite ci` runs all validation checks and exits non-zero on failure
- Output is clear and actionable for developers reviewing CI results
- `--format json` produces machine-readable output for integration with other tools
- Runs in under 10 seconds for a 500-entry KB
- Documented in the Getting Started tutorial

## Launch Context

This is a quick win for corporate team adoption. Ships as part of 0.8 or shortly after. The framing from the permissions model: "Git is your access control. Pyrite is your quality control." `pyrite ci` is how quality control gets enforced at the git layer — before a full application-level permission system exists.
