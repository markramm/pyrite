---
id: extension-registry
title: "Extension Registry and Public KB Directory"
type: backlog_item
tags:
- feature
- infrastructure
- community
- extensions
kind: feature
priority: medium
effort: M
status: planned
links:
- launch-plan
- bhag-self-configuring-knowledge-infrastructure
- roadmap
---

## Problem

Users who discover Pyrite need to find extensions for their domain and public KBs they can subscribe to. Without a registry, the extension ecosystem is invisible — you'd have to know about each extension's git repo individually. Additionally, there's no way to browse what other people have built with Pyrite.

## Solution

An extension registry and public KB directory — itself managed as a Pyrite KB. This is the ultimate dogfooding: the registry of Pyrite extensions is a Pyrite knowledge base with typed entries for each extension and public KB.

### Entry Types (for the registry KB)

- `extension` — name, description, author, repo URL, version, compatible Pyrite version, entry types provided, install command, download count, category
- `public_kb` — name, description, maintainer, repo URL, KB type, entry count, last updated, subscribe command, category
- `category` — domain category for browsing (software, research, journalism, PKM, etc.)

### Features

- **Browse by category**: software, journalism, research, PKM, etc.
- **Search extensions**: full-text and semantic search across extension descriptions and entry types
- **Install instructions**: each extension entry includes the exact `pyrite extension install` command
- **Subscribe to public KBs**: each public KB entry includes the clone/subscribe command
- **Community contributions**: submit your extension/KB via PR to the registry repo (standard GitHub workflow)

### Implementation Approach

The registry is a public git repo containing a Pyrite KB with the extension and public_kb entry types. The demo site (see [[demo-site-deployment]]) hosts a browsable web UI for the registry. The registry KB itself uses Pyrite's existing infrastructure — no new code needed beyond the entry types.

### CLI Integration (future)

- `pyrite registry search <query>` — search the registry from the command line
- `pyrite registry install <extension-name>` — fetch and install an extension by name
- `pyrite registry publish <path>` — submit an extension to the registry

## Prerequisites

- Demo site running (to host the browsable registry)
- Extension install CLI working (0.5, already done)
- At least 3 extensions to populate the registry (software, journalism, PKM — all planned)

## Success Criteria

- Registry KB with entries for all shipped extensions and public KBs
- Browsable via demo site web UI
- Each extension entry has working install instructions
- Community can submit extensions via PR
- Search works across extension names, descriptions, and provided entry types

## Launch Context

Ships alongside wave 1 (0.8 alpha). Even with just the built-in extensions, having a registry demonstrates the ecosystem story. As waves 2-4 ship their plugins, the registry grows — each new plugin is proof that the platform works for diverse domains.
