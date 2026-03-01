---
id: mcp-submission-update
title: "Update MCP_SUBMISSION.md with Current Stats"
type: backlog_item
tags:
- documentation
- mcp
- launch
kind: improvement
priority: high
effort: XS
status: planned
links:
- launch-plan
- roadmap
---

## Problem

MCP_SUBMISSION.md has stale test counts, tool counts, and configuration examples. This is the first document MCP registry reviewers see. Inaccurate numbers undermine credibility.

## Solution

Update MCP_SUBMISSION.md with current stats:

### Items to Update

1. **Test count**: Currently says some older number — actual count is 1780+ and growing
2. **MCP tool count**: Enumerate all current tools across read/write/admin tiers
3. **Configuration examples**: Verify `claude_desktop_config.json` examples are accurate
4. **Feature list**: Add recent features (task tools, QA tools, programmatic schema provisioning, bulk create, etc.)
5. **Screenshots**: Update if web UI has changed significantly

### Verification

After updating, run `pyrite-mcp --help` and cross-check tool list against what's documented.

## Prerequisites

None — this is a documentation update.

## Success Criteria

- All numbers accurate as of current codebase
- Configuration examples tested and working
- Tool list matches actual MCP server output
- Submission ready for MCP registry review

## Launch Context

Must be done before 0.8 launch. This is the Pyrite listing in the MCP tool registry — the discovery path for Claude Desktop and Claude Code users.
