# Getting Started with Pyrite

Pyrite is a Knowledge-as-Code platform. You keep structured knowledge in markdown files with YAML frontmatter, validated against schemas, versioned in git, and searchable by any AI through MCP. This tutorial walks you from zero to a working knowledge base in about five minutes.

## Install Pyrite

```bash
pip install pyrite
```

Or with AI-powered semantic search and all extras:

```bash
pip install "pyrite[all]"
```

## Create Your First Knowledge Base

```bash
pyrite init --template research --path my-research
cd my-research
```

This creates:

- **`kb.yaml`** — your KB configuration: name, entry types, field schemas
- **`.pyrite/`** — SQLite index and internal state (derived from your files, rebuildable anytime)
- A **git repo** initialized automatically, so every change is versioned from the start

Templates available: `research`, `software`, `zettelkasten`, `intellectual-biography`, `movement`, `empty`.

Your knowledge base is just a directory of markdown files. You can open them in any editor.

## Create Some Entries

Let's add a few entries to build up some content.

**A person:**

```bash
pyrite create -k my-research --type person --title "Ada Lovelace" \
  --body "Mathematician and writer. Wrote the first algorithm intended for a machine." \
  --tags "mathematics,computing"
```

**A note:**

```bash
pyrite create -k my-research --type note --title "Knowledge management principles" \
  --body "Atomic notes. Link liberally. Let structure emerge from connections, not folders."
```

**An event:**

```bash
pyrite create -k my-research --type event --title "Analytical Engine demonstration" \
  --body "Charles Babbage presented the design of the Analytical Engine." \
  --date "1837-01-01"
```

**A note with tags:**

```bash
pyrite create -k my-research --type note --title "Use markdown for all entries" \
  --body "Plain text is portable, diffable, and future-proof. Markdown adds just enough structure." \
  --tags "process"
```

Each command creates a markdown file with YAML frontmatter like this:

```markdown
---
id: ada-lovelace
title: Ada Lovelace
type: person
tags: [mathematics, computing]
created: 2026-03-03T10:00:00
---

Mathematician and writer. Wrote the first algorithm intended for a machine.
```

The `id` is auto-generated from the title. Pyrite validates fields against the type schema on every write.

## Search Your Knowledge Base

**Keyword search** works out of the box:

```bash
pyrite search "algorithm" -k my-research
pyrite search "mathematics" -k my-research --type person
```

**Semantic search** finds conceptually related content, not just keyword matches (requires an OpenAI API key or local embeddings):

```bash
pyrite search "early computer science pioneers" -k my-research --mode semantic
```

**Hybrid mode** combines both:

```bash
pyrite search "computing history" -k my-research --mode hybrid
```

## Connect an AI via MCP

Pyrite includes a built-in MCP server. Add this to your Claude Desktop or Claude Code config:

```json
{
  "mcpServers": {
    "pyrite": {
      "command": "pyrite",
      "args": ["mcp"]
    }
  }
}
```

Your AI can now search, read, and create entries in your knowledge base. It gets 14 read tools, 6 write tools, and 4 admin tools across three permission tiers. For read-only access:

```json
{
  "mcpServers": {
    "pyrite": {
      "command": "pyrite",
      "args": ["mcp", "--tier", "read"]
    }
  }
}
```

See also: [Gemini MCP integration](gemini-mcp-integration.md) | [OpenAI MCP integration](openai-mcp-integration.md)

## Use Presets for Domain-Specific KBs

Presets install extensions with specialized entry types and tools tailored to a domain:

```bash
pyrite init --name my-project --preset software
```

The **software** preset adds ADRs, components, backlog items, standards, and runbooks — everything you need to manage a software project's knowledge. Other presets include:

- **`zettelkasten`** — note maturity workflows (capture, elaborate, question, refine, connect)
- **`encyclopedia`** — articles with review and voting workflows
- **`cascade`** — timeline research with actors and capture lanes

## Launch the Web UI

Pyrite ships an optional web interface for browsing, editing, and visualizing your knowledge base:

```bash
pip install "pyrite[server]"
pyrite serve
```

Visit [http://localhost:8088](http://localhost:8088). The web UI includes a markdown editor with wikilink autocomplete, an interactive knowledge graph, collections with kanban/table/gallery views, and an AI chat sidebar.

## Next Steps

- [Writing a Plugin](tutorials/plugin-writing.md) — extend Pyrite with custom entry types, MCP tools, and CLI commands
- [Awesome Plugins](plugins.md) — community extensions
- [Gemini MCP Integration](gemini-mcp-integration.md) — connect Pyrite to Gemini
- [OpenAI MCP Integration](openai-mcp-integration.md) — connect Pyrite to OpenAI-compatible clients
- [Docker Deployment](../README.md#deploy) — deploy for teams with Railway, Render, Fly.io, or self-hosted
