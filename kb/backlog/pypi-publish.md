---
id: pypi-publish
title: "Publish pyrite and pyrite-mcp to PyPI"
type: backlog_item
tags:
- feature
- packaging
- agent-infrastructure
kind: feature
priority: high
effort: S
status: proposed
---

## Problem

Installing Pyrite currently requires cloning the git repo and running `pip install -e "."`. This is a human workflow. An autonomous agent declaring Pyrite as a dependency needs `pip install pyrite` or `pip install pyrite-mcp` to work from PyPI.

For the MCP-first agent story, `pip install pyrite-mcp` is the most important packaging step — it's what gets declared as a dependency in an OpenClaw skill's requirements.txt or a Claude Code plugin manifest.

## Proposed Solution

1. **Publish `pyrite` to PyPI** with the existing optional dependency groups (`[all]`, `[ai]`, `[semantic]`, `[server]`, `[cli]`).
2. **Publish `pyrite-mcp` to PyPI** as the standalone MCP server package (backlog #52 already built the packaging; this is the actual publish step).
3. **Verify `pip install pyrite && pyrite init` works from a clean venv** with no repo clone.
4. **Set up GitHub Actions for automated PyPI publishing** on tagged releases.
5. **Update README** install instructions to show `pip install pyrite` as the primary path.

## Related

- [[standalone-mcp-packaging]] — Built the pyrite-mcp package structure
- [[bhag-self-configuring-knowledge-infrastructure]] — PyPI publish enables agent-as-user
