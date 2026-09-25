---
id: codeql-models-pyrites-non-web-input-surfaces
title: "CodeQL treats Pyrite's non-web input surfaces as untrusted (MCP, CLI, subscribed-repo content)"
type: backlog_item
tags:
- security
- ci
kind: enhancement
status: proposed
priority: low
effort: M
---

The maintainer, 2026-09-25: keep on the backlog, unscheduled ("not sure if it is a big win, but I didn't want to lose track of it").

CodeQL's default "remote" threat model models FastAPI request data, but not:
- MCP tool arguments, which reach `_dispatch_tool` and plugin handlers through the MCP SDK;
- CLI arguments, environment variables or stdio (these are `local`);
- content from subscribed or forked repositories: frontmatter, `kb.yaml`, `.pyrite/config.yaml`;
- pages the clipper fetches.

Sketch:
1. Advanced setup (`codeql.yml` plus `.github/codeql/codeql-config.yml`) with `threat-models: [remote, local]`.
2. A small custom `.qll` marking those sources as remote.
3. A canary: the config must flag a known, since-fixed bug at its pre-fix commit (the #360 rule applied to the scanner).

Separately, CodeQL needs re-enabling on pyrite-wiki/pyrite (a repo setting); the last analysis was on 2026-09-20.
