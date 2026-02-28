---
id: headless-kb-init
title: "Headless KB Initialization with Templates"
type: backlog_item
tags:
- feature
- cli
- agent-infrastructure
kind: feature
priority: high
effort: M
status: proposed
---

## Problem

There is no `pyrite init` command that creates a fully working KB from scratch. Current setup requires manually creating directories, writing `kb.yaml`, and running `pyrite index build`. This is a human workflow — an autonomous agent needs a single atomic command that provisions a ready-to-query KB with zero interactive prompts.

## Proposed Solution

### `pyrite init` command

```bash
# Create a KB with a built-in template
pyrite init --template software --path ./my-project-kb

# Create a KB from an installed extension's preset
pyrite init --template zettelkasten --path ./notes

# Create a minimal empty KB
pyrite init --path ./my-kb

# Create with inline schema (for agent-generated schemas)
pyrite init --path ./legal-kb --schema-file schema.yaml
```

### Behavior

1. Creates the directory structure (including type-specific subdirectories from the preset)
2. Writes `kb.yaml` from the template/preset with types, fields, validation rules
3. Creates example entries (optional, skipped with `--no-examples`)
4. Runs `pyrite index build` automatically
5. Registers the KB in config.yaml
6. Returns JSON confirmation with KB name, path, entry count, and available types

### Templates

- `software` — ADRs, components, backlog items (from software-kb extension preset)
- `zettelkasten` — Zettel notes, literature notes (from zettelkasten extension preset)
- `research` — People, organizations, events, documents, topics (from core types)
- `empty` — Bare kb.yaml with no types defined

### Agent-critical requirements

- **No interactive prompts.** Every option has a default or is specified via flag.
- **`--format json` support.** Returns structured result for agent parsing.
- **Accepts `--schema-file`** for agent-generated schemas (the agent builds a kb.yaml and passes it in).
- **Idempotent.** Running init on an existing KB is a no-op with a warning, not an error.

## Related

- [[bhag-self-configuring-knowledge-infrastructure]] — Headless init is the first step in the agent self-configuration loop
- [[pypi-publish]] — `pip install pyrite && pyrite init --template software` is the golden path
