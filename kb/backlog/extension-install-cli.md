---
id: extension-install-cli
title: "pyrite extension install CLI Command"
type: backlog_item
tags:
- feature
- cli
- extensions
- agent-infrastructure
kind: feature
priority: medium
effort: S
status: done
---

## Problem

Installing an extension currently requires `pip install -e extensions/my-extension`, which assumes the agent knows the absolute path, the correct pip binary (`.venv/bin/pip`), and the `-e` flag. This is fragile for autonomous agents working from different directories.

## Proposed Solution

```bash
# Install an extension by path
pyrite extension install extensions/legal

# Install and verify
pyrite extension install extensions/legal --verify

# List installed extensions
pyrite extension list

# Uninstall
pyrite extension uninstall legal
```

### Behavior

- Resolves the path to the extension's pyproject.toml
- Runs `pip install -e <path>` using the correct Python environment
- With `--verify`: imports the plugin, checks it registers correctly, runs its tests
- `pyrite extension list`: shows installed plugins with their registered types, tools, and hooks
- `--format json` for all subcommands

## Related

- [[extension-init-cli]] — Creates the extension; this command installs it
- [[bhag-self-configuring-knowledge-infrastructure]] — Agent self-installation loop
