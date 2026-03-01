---
id: launch-plan
title: "Launch Plan: Content Matrix & User Acquisition Strategy"
type: note
tags:
- launch
- marketing
- strategy
links:
- roadmap
- bhag-self-configuring-knowledge-infrastructure
---

# Launch Plan: Content Matrix & User Acquisition Strategy

Target: 0.8 Announceable Alpha release.

This document maps user types × channels × content pieces into a full matrix of launch content. The goal is to identify every plausible content piece, then edit down and stage for execution.

---

## Messaging Foundation

Every content piece — blog post, video, Reddit post, email — draws from this section. The goal: anyone producing launch content can look here and know exactly what the argument is.

### The Core Insight

**Your AI is already smart. Pyrite makes it knowledgeable.**

Claude, Codex, OpenClaw — they can reason, write code, analyze documents. But they don't *know* anything about your specific domain. They lose context between sessions. They can't validate their own output against your schema. They start from scratch every time.

Pyrite fixes that. Add a knowledge base, and your AI becomes a domain expert — with structured memory, validated facts, and typed relationships. It doesn't just remember things; it knows them *reliably*.

### The Elevator Pitches

**The headline (works everywhere):** "Pyrite turns your AI into a domain expert."

**One sentence:** "Pyrite gives AI agents persistent, structured, validated knowledge — so Claude, Codex, or OpenClaw can become genuine domain experts instead of starting from scratch every session."

**The technical version:** "Pyrite is a knowledge compiler — define a schema, the schema generates infrastructure (validation, search, API surface), and the infrastructure constrains agents to produce quality output."

**For Claude/Cowork users:** "Add a Pyrite KB and give Claude superpowers. It searches structured knowledge instead of hallucinating."

**For agent builders:** "Persistent structured memory for your agent runtime. Schema validation on every write. Your agents don't lose context — they build on it."

### The Four-Wave Story

Each launch wave builds on the same core pitch but demonstrates it for a different audience, progressively widening the aperture from developers to everyone:

**Wave 1 — Platform Launch (0.8):** "Pyrite turns your AI into a domain expert." Here's the platform. Connect it to Claude Desktop, Claude Code, OpenClaw, Codex. Add a KB, get structured memory with validation and search. Instant domain expertise. *Audience: agent builders, MCP users, Python developers.*

**Wave 2 — Software Project Plugin:** "Here's what domain expertise looks like for software teams." Your agents understand your architecture, your backlog, your ADRs, your runbooks. They navigate typed, validated, interconnected project knowledge — not scattered markdown files. Workflows let agents claim tasks, report progress, and collaborate natively. *Audience: dev teams, engineering leads, Claude Code/Codex power users.*

**Wave 3 — Investigative Journalism Plugin:** "And here's a completely different domain." Follow the money. Entities, transactions, relationships, evidence chains, source validation. Same platform, same superpowers, entirely different world. Proof that Pyrite is genuinely general-purpose. *Audience: journalists, OSINT researchers, the HN/Reddit crowd that finds investigations fascinating.*

**Wave 4 — PKM Capture Plugin:** "Now it's for everyone." Snap a photo, paste a URL, record a voice note — Pyrite ingests it, classifies it, extracts structure, and creates typed entries automatically. Mobile access through Claude app and web UI. The knowledge you capture on the go becomes structured, searchable, connected knowledge by the time you sit down. *Audience: PKM power users (Obsidian, Anytype, Logseq), anyone who collects and organizes information.*

Wave 4 is when the aperture goes wide. By this point, three shipping plugins prove the platform works. The PKM crowd isn't hearing "here's a CLI tool, trust us." They're hearing "here's the tool that software teams, journalists, and AI agents all use for structured knowledge — and now it captures your web clippings, voice notes, and photos too."

**The BHAG (implicit in every wave):** "Today you build the KB and the agent becomes an expert. Tomorrow the agent builds the KB itself."

### The Pain Story (before/after)

**Before Pyrite:**

You point an AI agent at a new domain — legal research, threat intelligence, scientific literature. What happens? The agent stuffs findings into flat text files, or a vector database with no schema, or just loses context entirely when the session ends. The next agent that works in that domain starts from scratch. The agent after that, same thing. No validation. No structure. No memory. Every agent reinvents the wheel, and the wheels are bad.

Meanwhile, your team's Confluence hasn't been updated in six months. Nobody trusts the search. The new hire reads three contradictory runbooks before asking a human anyway. Your docs aren't wrong — they're just unvalidated, unsearchable, and disconnected.

**After Pyrite:**

Your agent creates a typed knowledge base: legal cases have jurisdiction, status, and citation fields. Statutes link to the cases that interpret them. Every entry is validated on write — missing fields, broken links, schema violations caught immediately. The next agent that works in this domain inherits structured, queryable, validated knowledge. It doesn't start from scratch. It starts from infrastructure.

Your team's docs live in git. A QA agent catches the stale runbook, the broken link, the missing field. Search actually works — full-text, semantic, and structured queries across everything. The knowledge graph shows how your ADRs connect to your components connect to your backlog. And when someone asks Claude a question about your architecture, it searches the actual KB instead of hallucinating.

### The "Why Now" Argument

The agent explosion is already here. OpenClaw hit 180K GitHub stars in weeks. Tens of thousands of autonomous agents are deployed and that number is growing exponentially. Gartner predicts 40% of enterprise apps will embed agents by end of 2026. Claude Code, Codex, CrewAI, LangGraph, AutoGen — every team is deploying autonomous agents.

But these agents have no persistent memory infrastructure. Vector databases store embeddings without structure. RAG pipelines retrieve without validating. Chat histories lose context between sessions. The tooling assumes humans will always be in the loop to organize knowledge. That assumption is already broken.

Every one of those agents needs what Pyrite provides. The market exists *right now*.

### The "Why Us" Argument

This isn't a prototype or a weekend project. Pyrite has 1780+ tests. Five shipped extensions proving the plugin protocol works. A 4800-entry timeline KB proving it works at scale. 13 architecture decision records documenting every major choice. We use Pyrite to build Pyrite — the project's own knowledge base runs on the tool. The plugin protocol has 15 extension points. The MCP server has three permission tiers. The CLI outputs structured JSON on every command. This is infrastructure you can build on.

### Three Portals, One Knowledge Base

Pyrite isn't a CLI tool, or a web app, or an MCP server. It's all three — three equal interfaces to the same structured knowledge, optimized for different moments:

**CLI** — the agent-native path. OpenClaw, Claude Code, Codex, shell scripts, cron jobs. This is where agents do the heavy lifting: bulk creation, extension management, headless provisioning, JSON pipelines. Every command outputs structured JSON. Agents live here.

**MCP** — the conversational path. Claude Desktop, Cowork, any MCP-compatible client. Humans (and agents) talk to the knowledge base in natural language. "What were the key architecture decisions this quarter?" "Find all entities connected to this organization." Three permission tiers control who can do what. Knowledge becomes accessible without learning query syntax.

**Web UI** — the visual path. Knowledge graph exploration, rich entry editor, QA dashboard, BYOK AI integration. This is where you *see* the knowledge — watch the graph grow as agents populate a KB, explore relationships visually, interact with AI workflows from a browser. Also the demo layer: the public demo site lets people experience Pyrite before installing anything.

These aren't competing interfaces — they're complementary. An agent builds the KB through CLI at 3am. You review what it produced in the web UI over coffee. You ask follow-up questions through Claude Desktop. All hitting the same typed, validated, versioned knowledge.

**Every content piece should reinforce this:** your knowledge base is accessible from everywhere your AI already lives. Claude Desktop users don't need to open a browser. Claude Code users don't need to leave the terminal. And when you want the visual overview, the web UI is right there.

### The BHAG Pitch (closer than you think)

Today, a human defines the schema and agents fill it in. Pyrite is building toward agents defining the schema too:

| Approach | Who Defines Schema | Who Populates | Who Validates |
|----------|-------------------|---------------|---------------|
| Obsidian / Notion | Human | Human | Human |
| Vector databases | Nobody (unstructured) | Agent | Nobody |
| RAG pipelines | Human (retrieval config) | Agent | Human (spot-checks) |
| **Pyrite today** | **Human** | **Human + Agent** | **Schema + QA Agent** |
| **Pyrite BHAG** | **Agent** | **Agent** | **Schema + QA Agent** |

An autonomous agent encounters a domain. It scaffolds a Pyrite extension — typed entries, validators, MCP tools. It tests what it built using TDD. It installs the extension, provisions a KB, and starts working. Every future agent that works in that domain gets structured, validated, queryable knowledge instead of flat files and lost context.

**The schema is the program. Pyrite is the runtime.**

This isn't aspirational — it's almost working today. Here's what already ships:

- `pyrite extension init legal --types case,statute,ruling` — agent scaffolds a full extension in one command
- Extension builder skill files guide the agent through implementation, following the same TDD protocol used to build Pyrite itself
- `pyrite extension install extensions/legal --verify` — installs and optionally runs tests
- `pyrite init --template <domain>` — provisions a KB with zero interactive prompts
- `--format json` on every CLI command — agents consume output programmatically
- QA validation on every write — agents validate their own output against the schema

The gap between "human defines schema" and "agent defines schema" is one skill file and a few CLI commands. The pieces are shipping now. The BHAG isn't a 2-year plan — it's a closing sprint.

### Objection Responses (sharp versions)

**"Can't I just use a vector database?"**
A vector database gives you similarity search over embeddings. Pyrite gives you typed entries with validated fields, relationship graphs, full-text and semantic search, git-native versioning, and a plugin system. A vector database is a feature. Pyrite is infrastructure.

**"How is this different from Obsidian?"**
Obsidian is a fantastic tool for humans writing notes. Pyrite is for agents producing structured knowledge at scale. Obsidian has no schema validation, no programmatic API (MCP/REST), no QA automation, and no plugin protocol for domain extensions. If your use case is "I want to write notes," use Obsidian. If your use case is "I want agents to build and query knowledge bases," that's Pyrite.

**"Why not Notion/Confluence?"**
Notion and Confluence are SaaS tools that own your data. Your docs live in their database, searched by their algorithm, organized by their UI. Pyrite is Knowledge-as-Code: your docs are markdown files in git. You own them. You version them. You review them with PRs. You validate them with CI. And AI agents can read and write them through a real API, not a screen-scraping hack.

**"Is this production-ready?"**
It's an alpha — honest about that. But it's a *tested* alpha: 1780+ tests, six shipped extensions, a 4800-entry KB in daily use. The architecture is solid. The rough edges are in packaging and docs, not in the core.

**"Seems over-engineered for notes"**
It's not for notes. It's for knowledge infrastructure. The difference: notes are for one person to read later. Knowledge infrastructure is for agents to query, validate, extend, and build on. The "over-engineering" is exactly the point — schema validation, plugin protocol, three-tier permissions, QA automation. That's what makes it infrastructure instead of another note-taking app.

### How Launch Features Connect to the BHAG

Every 0.8 launch feature is a step on the path to the BHAG. This connection should be explicit in every content piece:

| Launch Feature | Immediate Value | BHAG Step | Portal |
|---------------|-----------------|-----------|--------|
| QA validation | Catches stale docs, broken links | Agents validate their own output without human review | All three |
| `--format json` on every command | Clean scripting and automation | Agents consume CLI output programmatically | CLI |
| `pyrite init --template` | Quick setup for new KBs | Agents provision KBs non-interactively | CLI |
| `pyrite extension init` | Fast extension scaffolding | Agents build domain-specific extensions | CLI |
| Three-tier MCP | Secure agent access to Claude Desktop/Cowork | Trust tiers let you deploy untrusted agents safely | MCP |
| Web UI + knowledge graph | Visual exploration, see the KB grow | Operators monitor agent-built KBs | Web |
| BYOK AI in UI | Ask questions, trigger workflows from browser | Human-AI collaboration on structured knowledge | Web |
| Extension registry | Discover and install extensions | Agents discover and install domain infrastructure | All three |
| Software plugin (wave 2) | Agents collaborate on your project natively | Domain-specific infrastructure, built on the platform | All three |
| Journalism plugin (wave 3) | Follow-the-money investigation tool | Proves the platform is genuinely general-purpose | All three |
| PKM capture plugin (wave 4) | Ingest anything → structured entries automatically | AI classifies and organizes knowledge without human filing | Web + Mobile |

The blog post, every demo video, and every Reddit post should make at least one of these connections. Don't just show the feature — show where it's going.

### Per-Wave Messaging

**Wave 1 content should say:**
- "Pyrite turns your AI into a domain expert" (headline)
- Here's how it works (platform demo)
- Here's why it matters now (agent explosion, no memory infrastructure)
- Here's where it's going (BHAG — agents building their own knowledge infrastructure)

**Wave 2 content should say:**
- "Your software project, managed by agents that actually understand it" (headline)
- Here's what we built on Pyrite in [X days] (proof the platform works)
- Workflows: agents claim tasks, update status, link evidence
- We use it to build Pyrite itself (dogfooding credibility)
- You could build something like this for your domain too

**Wave 3 content should say:**
- "Follow the money — investigative journalism powered by structured knowledge and AI" (headline)
- Completely different domain, same platform (general-purpose proof)
- The knowledge graph is the investigation (visual payoff)
- Source chains and evidence validation (trust and rigor)
- Imagine what agents could build for *your* domain

**Wave 4 content should say:**
- "Capture anything. Pyrite turns it into structured knowledge." (headline)
- Snap, paste, clip, dictate — AI classifies and files it for you
- Mobile-first capture through Claude app and web UI
- Three plugins already proving the platform works — now it's for everyone
- Your AI doesn't just answer questions about your knowledge — it helps you build it

---

## User Types & What They Care About

### 1. PKM Power Users (Obsidian, Anytype, Logseq, Notion personal)

**Target wave: Wave 4 (PKM Capture Plugin)**. Do not actively target this audience until the capture plugin exists. The PKM crowd will be disappointed by a CLI-first platform without frictionless mobile capture. Waves 1-3 may attract some PKM-adjacent early adopters organically, but don't market to them directly until wave 4.

**Profile:** Individual knowledge workers who maintain personal knowledge bases. Already sold on structured notes and markdown. Pain points: search sucks at scale, no validation, tools are siloed, *capturing new knowledge is high-friction*.

**Hook (wave 4):** "Capture anything — photos, web clippings, voice notes, pasted text — and Pyrite turns it into structured, searchable, connected knowledge automatically."

**Key capabilities to demo (wave 4):**
- Frictionless capture: image → OCR/vision → typed entry; URL → extract → classify → entry; voice → transcribe → entry
- Mobile access through Claude app and web UI
- AI auto-classification and tagging (the killer feature for PKM)
- FTS5 + semantic search across everything you've captured
- Knowledge graph showing connections across your captured knowledge
- Schema validation and QA — your knowledge base stays clean automatically
- Git-native versioning (they already use git for Obsidian vaults)
- Markdown source of truth — no lock-in, portable

**Objections to address:**
- "Why not just use Obsidian with plugins?" — Obsidian doesn't auto-classify, validate, or give your AI agent access to your knowledge
- "I don't want to learn a CLI" — Wave 4 is web/mobile first. The CLI exists for power users and agents, not required for PKM
- "Will this lock me in?" — Markdown files in git. You own everything. Take it anywhere.

---

### 2. Corporate KB Teams (Confluence, Notion team, SharePoint)

**Profile:** Teams maintaining shared knowledge: engineering docs, runbooks, architectural decision records, onboarding guides. Pain points: docs rot, search is keyword-only, no validation, no CI/CD for knowledge.

**Hook:** "Your team's knowledge base with version control, schema validation, and AI search — like upgrading from Google Docs to GitHub for your documentation."

**Key capabilities to demo:**
- Typed entries (ADRs, components, runbooks, standards)
- QA validation — catch stale docs, broken links, missing fields automatically
- Web UI for non-CLI users
- Knowledge graph showing how everything connects
- "We use Pyrite to build Pyrite" — the dogfooding story
- Git workflow for knowledge review (PRs for doc changes)

**Objections to address:**
- "Our team won't use a CLI"
- "How does this integrate with our existing tools?"
- "We already have Confluence/Notion"

---

### 3. Agentic Teams (AI engineers, agent runtime builders)

**Profile:** Developers building autonomous agent systems (OpenClaw, custom Claude Code setups, Codex-based pipelines). Pain points: agents lose context between sessions, no structured memory, no way for agents to validate their own work.

**Hook:** "Persistent, structured, validated memory for your AI agents — and they can build their own extensions for any domain."

**Key capabilities to demo:**
- Self-configuration loop (agent builds extension → tests → installs → populates KB)
- Three-tier MCP permission model (read/write/admin)
- CLI with `--format json` for agent consumption
- QA validation on every write
- Extension scaffolding (`pyrite extension init`)
- Task coordination plugin (when shipped)

**Objections to address:**
- "Can't I just use a vector database?"
- "How does this compare to LangChain memory / MemGPT?"
- "Is this production-ready?"

---

### 4. Python Developers (your network)

**Profile:** Experienced Python devs who appreciate good architecture. May not have an immediate KB need but will recognize quality tooling and see applications.

**Hook:** "A beautifully engineered knowledge platform — 15-method plugin protocol, SQLite FTS5, git-native storage, three-tier MCP. Worth studying even if you never use it."

**Key capabilities to demo:**
- Plugin protocol architecture (runtime checkable, 15 extension points)
- Dual storage model (markdown source of truth, SQLite derived index)
- Test suite (1780+ tests, TDD culture)
- Extension system (pip-installable domain plugins)
- Clean CLI with Click

**Objections to address:**
- "What would I use this for?"
- "Seems over-engineered for notes"

---

### 5. Automation Builders (n8n, Make, Zapier users)

**Profile:** People who build automated workflows connecting services. Pain points: no good "knowledge" node in their pipelines, can't easily store and query structured data from workflows.

**Hook:** "A knowledge base your automations can read and write — structured data in, smart search out."

**Key capabilities to demo:**
- REST API for workflow integration
- MCP tools for AI nodes
- CLI for shell-based automations
- Typed entries mean consistent data structure
- n8n workflow: RSS → Pyrite → search → alert

**Objections to address:**
- "Can't I just use Airtable/Notion API?"
- "Is there an official n8n node?"

---

## Channels & Content Types

### A. Hacker News

**Audience mix:** Agentic teams (40%), Python devs (30%), PKM power users (20%), curious (10%)

**Content needed:**
- [ ] HN submission title (< 80 chars, technical, intriguing)
- [ ] Blog post to link (the primary content piece)
- [ ] First comment / "Show HN" description (technical depth, architecture highlights)

**Messaging angle:** Lead with the technical insight and contrarian bet. "Knowledge-as-Code for a world of agent swarms. Git, not CRDTs. Schema, not free text. Designed for AI agents as primary consumers."

**Timing:** Tuesday or Wednesday, ~10am ET. Avoid major tech news days.

**Draft titles (pick/refine one):**
- "Show HN: Pyrite – Knowledge-as-Code platform where AI agents are first-class citizens"
- "Show HN: Pyrite – A knowledge base system designed for agent swarms, built on git and markdown"
- "Show HN: Pyrite – Structured knowledge infrastructure for humans and AI agents"

---

### B. Reddit

**Subreddits and angles:**

| Subreddit | Angle | Content |
|-----------|-------|---------|
| r/programming | Architecture deep-dive | Blog post + architecture diagrams |
| r/Python | "Show r/Python" — clean codebase, plugin protocol | Blog post + code walkthrough |
| r/LocalLLaMA | MCP integration, local-first, agent memory | Claude Desktop demo video |
| r/ClaudeAI | MCP tools, Claude Desktop integration | Claude Desktop demo + tutorial |
| r/ObsidianMD | Obsidian vault upgrade path, knowledge graph | PKM demo video + migration guide |
| r/selfhosted | Local-first, no cloud, git-native | Install tutorial + self-hosting guide |
| r/artificial | Agent-first knowledge infrastructure | BHAG blog post |
| r/n8n | Workflow integration | n8n demo video + workflow template |

**Content needed (per subreddit):**
- [ ] Custom post title and intro paragraph for each subreddit
- [ ] Subreddit-specific demo video or link to relevant section of blog

---

### C. Blog Post (Central Content Piece)

**Audience:** All user types; this is what HN, Reddit, and email link to.

**Structure:**

1. **The thesis** (2 paragraphs) — Knowledge management is shifting from human to agent consumers. What does knowledge infrastructure look like in a world of agent swarms?
2. **The problem** (2 paragraphs) — Agents today lose context between sessions. Corporate KBs rot in Confluence. PKM tools don't validate or connect. No tool is designed for programmatic knowledge production.
3. **Introducing Pyrite** (2 paragraphs + Knowledge-as-Code table) — Knowledge-as-Code: markdown files with YAML frontmatter in git. Schema validation. Full-text + semantic search. Three-tier MCP server. Plugin system with 15 extension points.
4. **Demo: The self-configuration loop** (with CLI output / GIFs) — Agent scaffolds extension → tests it → installs → provisions KB → populates → QA validates
5. **Architecture highlights** (diagram + 3-4 paragraphs) — Dual storage, plugin protocol, MCP tiers
6. **Web UI showcase** (screenshots) — Knowledge graph, entry editor, search, QA dashboard
7. **Getting started** (5 commands) — pip install → init → create → search → connect MCP
8. **What's next** (2 paragraphs) — Roadmap through 0.9+, BHAG vision
9. **Links** — GitHub, docs, MCP directory listing, demo videos

**Content needed:**
- [ ] Full blog post draft
- [ ] Architecture diagram (can be mermaid or SVG)
- [ ] Knowledge-as-Code comparison table (already exists in VISION.md)
- [ ] CLI output screenshots/GIFs for self-configuration loop
- [ ] Web UI screenshots (knowledge graph, editor, search)
- [ ] "Getting started" code block verified against actual install flow

---

### D. Video Demos

#### Audience-Specific Intros (~90 seconds each)

| Video | Target | Hook | Key Scenes |
|-------|--------|------|------------|
| **PKM Intro** | Obsidian/Anytype users | "Your markdown vault, supercharged" | Existing markdown folder → `pyrite init` → instant search → knowledge graph → MCP chat with your KB |
| **Corporate KB Intro** | Confluence/Notion teams | "Version-controlled, validated knowledge" | Typed entries (ADRs, runbooks) → QA validation catching stale docs → web UI browse → git diff of knowledge changes |
| **Agentic Teams Intro** | AI engineers | "Agents that build their own knowledge infrastructure" | Empty directory → agent scaffolds extension → tests pass → KB populated → structured queries work |

#### Integration Demos (~2-3 minutes each)

| Video | Target | What It Shows |
|-------|--------|---------------|
| **Claude Desktop** | Broadest audience | Connect MCP → natural language queries against timeline KB → create entries through conversation → knowledge graph updates live |
| **Claude Code** | Developers | Navigate Pyrite's own KB to understand the codebase → search ADRs → find backlog items → "we use it to build it" |
| **n8n Workflow** | Automation builders | RSS feed → n8n → Pyrite API → create typed entries → scheduled QA validation → alert on issues |
| **Web UI Tour** | All (especially non-CLI) | Create entry → rich editor → link entries → knowledge graph exploration → search → collections → QA dashboard |
| **AI in UI** | All | AI-assisted search → suggested connections → content generation within editor |
| **Manual UI Walkthrough** | Skeptics, evaluators | Pure feature tour without AI: create, edit, search, filter, graph, collections. "This is a real product." |

#### Extended Demo (~5 minutes)

| Video | Target | What It Shows |
|-------|--------|---------------|
| **Full Self-Configuration Loop** | HN, agent builders | Start from nothing → agent discovers domain → builds extension with TDD → installs → provisions KB → populates 100 entries → QA validates → web UI shows the result. The BHAG in action. |

**Content needed:**
- [ ] Script/storyboard for each video
- [ ] Screen recording setup (clean terminal, clean browser, consistent fonts)
- [ ] Demo KBs prepared for each video (timeline, software-team, legal example, etc.)
- [ ] Voiceover or text overlay plan
- [ ] Hosting: YouTube channel? Embedded in blog post?

---

### E. Tutorial / Getting Started Guide

**Audience:** Anyone who clicks through from a channel and wants to try it.

**Structure:**

1. **Install** (30 seconds) — `pip install pyrite`
2. **Initialize a KB** (1 minute) — `pyrite init --template software`
3. **Create entries** (2 minutes) — CLI and/or web UI
4. **Search** (1 minute) — FTS and semantic
5. **Connect MCP** (2 minutes) — Claude Desktop configuration + first query
6. **Explore the web UI** (2 minutes) — Knowledge graph, editor, search
7. **Next steps** — Links to extension building, API docs, example KBs

**Content needed:**
- [ ] Tutorial text (in docs/ or standalone page)
- [ ] Verified install-to-working flow on clean machine
- [ ] MCP configuration snippet for Claude Desktop
- [ ] Example queries that produce impressive results with the template KB

---

### F. Email (Direct Outreach)

**Audience:** Python developers in your network.

**Content needed:**
- [ ] Personal email template (short, not marketing-speak)
- [ ] Subject line that gets opened
- [ ] 3-sentence pitch + link to blog post
- [ ] Ask: "try it and tell me what breaks" (beta-tester framing, not product launch)

**Messaging angle:** "I've been building this for a while, would love your eyes on it. It's a knowledge base platform designed for AI agents — think Obsidian meets MCP. Here's the blog post, here's the repo."

---

### G. Dev.to / Hashnode / Medium

**Audience:** Developers discovering through search (long-tail SEO).

**Content needed:**
- [ ] Adapted version of the blog post (platform-native formatting)
- [ ] Tags: python, ai, knowledge-management, mcp, claude, developer-tools
- [ ] Published 1-2 days after HN launch (catches the search traffic)

---

### H. MCP Directory

**Audience:** Claude Desktop users browsing for MCP integrations.

**Content needed:**
- [ ] Updated MCP_SUBMISSION.md (accurate tool count, test count, config examples)
- [ ] Submission to Anthropic's MCP directory (timing: before launch)
- [ ] Clear install instructions in the listing

---

### I. Social Media (Twitter/X, Bluesky, LinkedIn)

**Content needed:**
- [ ] Thread format: 5-7 tweets telling the story (thesis → problem → solution → demo GIF → link)
- [ ] GIFs extracted from demo videos (knowledge graph, CLI in action, search results)
- [ ] LinkedIn post (more professional framing, "we've been building...")

---

## Demo Datasets & KBs

Pre-built KBs for impressive demos:

| Dataset | Source | Entry Count | Best For |
|---------|--------|-------------|----------|
| **4800-event timeline** | Already built | ~4800 | Claude Desktop demo, search impressiveness, PKM intro |
| **Pyrite's own KB** | This repo's `kb/` | ~80+ | "We use it to build it", Claude Code demo |
| **Awesome Python** | awesome-python GitHub | ~1600 | Python dev outreach, search demo ("find me async HTTP libs") |
| **CVE/vulnerability data** | NIST NVD JSON feeds | 1000+ (curated subset) | Security angle, corporate KB demo |
| **RFC summaries** | IETF | ~500 (curated) | Knowledge graph demo (RFCs reference each other heavily) |
| **Python top packages** | PyPI JSON API | ~500 | Python dev outreach, dependency graph visualization |

**Content needed:**
- [ ] Import scripts for each dataset (in `examples/` directory)
- [ ] Curated subsets that demo well (not raw dumps)
- [ ] Each dataset has a matching `--template` or schema definition
- [ ] Verify knowledge graph looks good with each dataset

---

## Content × Channel × Audience Matrix

Which content serves which channel for which audience:

| Content Piece | HN | Reddit | Blog | Email | MCP Dir | Social |
|--------------|-----|--------|------|-------|---------|--------|
| Blog post | ✓ (link) | ✓ (link) | ✓ (primary) | ✓ (link) | | ✓ (link) |
| PKM intro video | | r/ObsidianMD | embedded | | | ✓ |
| Corporate KB intro video | | r/programming | embedded | | | ✓ (LinkedIn) |
| Agentic teams intro video | ✓ (in comment) | r/LocalLLaMA, r/ClaudeAI | embedded | | | ✓ |
| Claude Desktop demo | ✓ (in comment) | r/ClaudeAI | embedded | | ✓ | ✓ |
| Claude Code demo | | r/programming, r/Python | embedded | ✓ | | |
| n8n demo | | r/n8n | linked | | | |
| Web UI tour | | all | embedded | | | ✓ |
| AI in UI demo | | r/artificial | embedded | | | ✓ |
| Manual UI walkthrough | | | linked | | | |
| Full self-config loop | ✓ (in comment) | r/LocalLLaMA | embedded | ✓ | | ✓ |
| Getting Started tutorial | | all (linked) | linked | ✓ | ✓ | |
| Architecture deep-dive | ✓ (in comment) | r/programming, r/Python | section | | | |
| Import scripts / example KBs | | r/Python | linked | ✓ | | |

---

## Staging & Sequencing (four waves, ~2 pieces/week within each)

### Wave 1: Platform Launch (0.8 release)

**Message:** "Pyrite turns your AI into a domain expert."
**Primary audience:** Agent builders (OpenClaw, Claude Code, Codex, CrewAI), Claude Desktop MCP users

#### Pre-Launch (2-3 weeks before)

- [ ] Set up Discord server (channels: #general, #getting-started, #extensions, #agent-builders, #feedback)
- [ ] Set up demo site (see Demo Site Hosting below)
- [ ] Finalize tutorial, verify install flow on clean machine
- [ ] Record priority demo videos (Claude Desktop demo, agentic teams intro)
- [ ] Write wave 1 blog post, get 2-3 people to review
- [ ] Prepare demo KBs (timeline, Pyrite's own KB)
- [ ] Update MCP_SUBMISSION.md, submit to directory
- [ ] Draft HN title, Reddit posts, email template
- [ ] Set up YouTube channel
- [ ] Seed the extension registry KB and public KB directory (see below)
- [ ] Prepare social media assets (GIFs, screenshots)

#### Launch Day (Tuesday or Wednesday, ~10am ET)

- [ ] Publish wave 1 blog post
- [ ] Submit to HN ("Show HN")
- [ ] Send personal emails to Python developer network
- [ ] Tweet/post thread with GIFs

#### Week 1 (~2 pieces)

- [ ] Post to r/ClaudeAI, r/LocalLLaMA (MCP integration, agent memory angle)
- [ ] Publish Claude Desktop demo video

#### Week 2 (~2 pieces)

- [ ] Post to r/programming, r/Python (architecture deep-dive angle)
- [ ] Publish on dev.to (adapted blog post)

#### Wave 1 Activation Metric

Someone connects Pyrite via MCP or CLI to their agent runtime and creates entries programmatically. Track: `pyrite create --format json` invocations, MCP `kb_create` tool calls.

---

### Wave 2: Software Project Plugin (1-2 weeks after wave 1)

**Message:** "Your software project, managed by agents that actually understand it."
**Primary audience:** Dev teams using Claude Code/Codex, engineering leads frustrated with doc rot

#### Content

- [ ] Wave 2 blog post: "We built a software project management tool on Pyrite in [X days] — here's what agents can do with your architecture docs, backlog, and ADRs"
- [ ] Demo video: agents navigating Pyrite's own project KB — claiming tasks, updating status, linking evidence
- [ ] Getting started guide specific to the software plugin

#### Distribution (~2 pieces/week)

- [ ] HN follow-up post (new content, not a repost)
- [ ] r/programming, r/Python (dev tools angle, dogfooding story)
- [ ] r/ExperiencedDevs, r/softwarearchitecture (ADR management, doc rot)
- [ ] LinkedIn post ("we use Pyrite to build Pyrite")
- [ ] Email wave 2 to Python network ("here's what we built on it")

#### Wave 2 Activation Metric

A dev team installs the software plugin and creates 20+ entries across multiple types (ADRs, components, backlog items) for their actual project.

---

### Wave 3: Investigative Journalism Plugin (1-2 weeks after wave 2)

**Message:** "Follow the money — investigative research powered by structured knowledge and AI."
**Primary audience:** Journalists, OSINT researchers, investigative teams, and the broader public that finds this kind of work fascinating

#### Content

- [ ] Wave 3 blog post: "Building an investigative journalism tool with structured knowledge and AI workflows"
- [ ] Demo video: knowledge graph showing entity relationships, money flows, evidence chains
- [ ] Example KB: curated public investigation dataset demonstrating the plugin

#### Distribution (~2 pieces/week)

- [ ] HN (this is the post that goes viral — "follow the money" is inherently dramatic)
- [ ] r/OSINT, journalism-focused communities
- [ ] Twitter/X journalism circles, GIJN network
- [ ] r/artificial, r/programming (different-domain proof)
- [ ] dev.to follow-up

#### Wave 3 Activation Metric

Someone builds a KB for a real investigation or research project and shares it (publicly or with collaborators).

---

### Wave 4: PKM Capture Plugin (after waves 1-3, when capture pipeline is built)

**Message:** "Capture anything. Pyrite turns it into structured knowledge."
**Primary audience:** PKM power users (Obsidian, Anytype, Logseq), anyone who collects and organizes information

This wave is the widest aperture. By this point, three shipping plugins prove the platform works. The PKM crowd hears: "software teams, journalists, and AI agents all use this — and now it captures your web clippings, voice notes, and photos too."

#### Prerequisites (must ship before wave 4 launch)

- [ ] PKM capture plugin built: ingest → classify → extract → create typed entry pipeline
- [ ] Capture endpoints: image (OCR/vision), URL (extract + summarize), voice (transcribe), text (classify)
- [ ] Mobile-friendly web UI (responsive, quick-capture interface)
- [ ] Claude app integration for capture (if feasible)
- [ ] BYOK AI in UI working for interactive classification and querying

#### Content

- [ ] Wave 4 blog post: "Your AI organizes your knowledge for you — snap, clip, dictate, and Pyrite turns it into structured entries"
- [ ] Demo video: phone capture → auto-classification → knowledge graph shows connections → search finds it later
- [ ] Obsidian migration guide: point Pyrite at your existing vault, get instant search + graph + validation
- [ ] Getting started guide specific to PKM workflow (no CLI required)

#### Distribution (~2 pieces/week)

- [ ] r/ObsidianMD, r/PKMS, r/Zettelkasten (this is their home turf)
- [ ] r/productivity, r/selfhosted
- [ ] HN post (new angle: "we built a PKM tool where AI does the filing")
- [ ] PKM YouTube/blog community outreach (Linking Your Thinking, etc.)
- [ ] Twitter/X PKM circles
- [ ] dev.to / Medium (adapted blog post)

#### Wave 4 Activation Metric

Someone migrates an existing Obsidian/markdown vault into Pyrite and uses the capture pipeline to add 10+ entries via web/mobile in their first week.

---

### Ongoing (across all waves)

- [ ] Monitor MCP directory listing traffic
- [ ] Respond to GitHub issues and Discord from new users
- [ ] Iterate on tutorial based on friction points
- [ ] Collect testimonials / usage stories
- [ ] Record remaining demo videos as time permits (n8n, corporate KB, web UI tour, AI in UI, manual walkthrough)
- [ ] Publish new extensions and public KBs to the registry
- [ ] Post to secondary communities (r/selfhosted, r/n8n) as relevant content exists

---

## Success Metrics

| Metric | Target (Week 1) | Target (Month 1) |
|--------|-----------------|-------------------|
| GitHub stars | 100 | 500 |
| PyPI installs | 200 | 1000 |
| HN points | 50+ | — |
| MCP directory installs | 50 | 200 |
| Blog post views | 2000 | 5000 |
| Active users (any CLI/MCP activity) | 20 | 100 |
| GitHub issues from external users | 10 | 30 |
| Extensions built by external users | 1 | 5 |

---

## Demo Site

### What It Is

A public read-only Pyrite instance loaded with one or more demo KBs. Visitors can browse entries, explore the knowledge graph, and run searches without installing anything. This is the "try before you install" experience — link to it from the blog post, HN comment, and README.

### Hosting Architecture

The entire system is self-contained: static SvelteKit frontend + single FastAPI/Uvicorn process + SQLite database + markdown files. No external databases, no caching layer, no load balancer required.

```
Internet → [Reverse proxy (Caddy/nginx)] → [Uvicorn :8088]
                                                ↓
                                    [SQLite FTS5 index]
                                    [Markdown KB files (read-only)]
                                    [Static SvelteKit frontend]
```

### Hosting Options & Cost Estimates

| Option | Monthly Cost | Pros | Cons |
|--------|-------------|------|------|
| **Railway / Render** | $5-7/mo | Easiest deploy, Docker support, auto-SSL | Cold starts on free tier, limited disk |
| **Fly.io** | $3-5/mo | Persistent volumes for SQLite, global edge | Slightly more config |
| **DigitalOcean droplet** | $6/mo (1GB) | Full control, persistent, no cold starts | Manual setup, maintenance |
| **Hetzner VPS** | $4/mo (2GB) | Best price/performance, EU hosting | Manual setup |
| **Oracle Cloud free tier** | $0 | Free forever ARM instance (24GB RAM!) | Oracle, more setup, reliability concerns |
| **GitHub Pages + separate API** | $5/mo (API only) | Static frontend free, CDN-backed | Split architecture, CORS config |

**Recommendation:** Fly.io or Railway for simplicity. A single container with a persistent volume for the SQLite index. Pre-populate the KB and index at build time. Total cost: ~$5/mo.

### Demo Site Content

Load with the most impressive KBs:
- 4800-event timeline (wow factor for search)
- Pyrite's own KB (dogfooding credibility)
- One community dataset (Awesome Python or RFC summaries)

### Configuration

- Read-only mode (no auth needed, no write endpoints exposed)
- Disable git operations
- Pre-built index included in Docker image
- No semantic search (avoids needing GPU/large model — FTS5 is impressive enough for demo)

### Content needed:
- [ ] Updated Dockerfile (current one references stale `cascade_research` module name)
- [ ] `docker-compose.yml` for local testing
- [ ] `fly.toml` or `railway.json` deploy config
- [ ] Pre-built demo KBs committed to a demo repo
- [ ] CI pipeline to rebuild and deploy on KB updates

---

## Extension Registry & Public KB Directory

### Concept

A Pyrite KB whose entries are Pyrite extensions and public knowledge bases. This eats its own dog food: the registry is itself a knowledge base, searchable through the same tools it catalogs.

### Why This Matters

- **Discovery**: Users find extensions and KBs through the same search they use inside Pyrite
- **Demo value**: The registry itself demonstrates Pyrite's capabilities
- **Network effects**: Every new extension or public KB makes the ecosystem more valuable
- **Dogfooding**: Proves the system works for real catalog/directory use cases

### Extension Registry Schema

```yaml
# Entry type: extension
type: extension
fields:
  name: string (required)
  description: string (required)
  repo_url: string (required) # GitHub/GitLab repo URL
  author: string
  license: string
  pypi_package: string # if published to PyPI
  entry_types: list[string] # types this extension provides
  mcp_tools: list[string] # MCP tools this extension adds
  pyrite_version: string # minimum compatible version
  install_command: string # e.g. "pip install pyrite-legal"
  status: enum[experimental, stable, maintained, archived]
tags: # category tags
  - domain (legal, scientific, security, media, etc.)
  - capability (types, validators, workflows, tools)
```

### Public KB Directory Schema

```yaml
# Entry type: public_kb
type: public_kb
fields:
  name: string (required)
  description: string (required)
  repo_url: string (required)
  author: string
  license: string
  entry_count: integer
  kb_type: string # generic, software, research, encyclopedia, etc.
  extensions_used: list[string] # links to extension entries
  topics: list[string]
  last_updated: date
  status: enum[active, archived, snapshot]
```

### Seed Content

Extensions to list at launch (even if first-party):
- `pyrite-zettelkasten` — Zettelkasten extension (ships with Pyrite)
- `pyrite-social` — Social/engagement extension
- `pyrite-encyclopedia` — Encyclopedia workflows
- `pyrite-software-kb` — Software team KB (ADRs, components, backlog)

Public KBs to list:
- Pyrite's own `kb/` — the meta-KB
- 4800-event timeline
- Any community datasets built for demo (Awesome Python, RFCs, etc.)

### Implementation

This could be:
1. **A GitHub repo** with markdown entries following the schemas above — simplest, works immediately
2. **A section of the demo site** — browse extensions and KBs through the web UI
3. **Both** — the repo IS the KB, the demo site indexes it

The "awesome list" approach (option 1) is the fastest to launch. A simple README with a table, plus individual markdown entries for each extension/KB that Pyrite can index. Over time, this becomes a proper Pyrite KB that demonstrates the tool's own capabilities.

### Content needed:
- [ ] Create `pyrite-registry` repo (or directory within main repo)
- [ ] Define extension and public_kb entry type schemas
- [ ] Seed with first-party extensions and KBs
- [ ] Add to demo site
- [ ] README with contribution guidelines ("list your extension here")
- [ ] Consider: should this be a Pyrite extension itself? (meta!)

---

## Discord Community

### Channel Structure

| Channel | Purpose |
|---------|---------|
| #announcements | Release notes, blog posts, new videos |
| #general | Discussion |
| #getting-started | Install help, first-time questions |
| #extensions | Building and sharing extensions |
| #agent-builders | Agentic use cases, MCP integration, OpenClaw etc. |
| #pkm | Personal knowledge management, Obsidian migration |
| #showcase | Share your KBs, extensions, workflows |
| #feedback | Bug reports, feature requests (supplement to GitHub issues) |
| #dev | Contributing to Pyrite core |

### Setup timing

Set up 1-2 weeks before launch. Link in README, blog post, and all channel posts. Include invite link in `pip install` post-install message if possible.

---

## Open Questions

- Where to host the blog post? Personal blog, GitHub Pages, dedicated site?
- YouTube vs embedded video hosting?
- Pricing/licensing messaging — is MIT sufficient or does it need explicit "free forever" language?
- Should we target Product Hunt as well? (probably week 3-4, not launch day)
- Is there a launch week "challenge" angle? ("Build a KB for your domain in 10 minutes")
- Should the extension registry be its own repo or a directory in the main repo?
- Demo site domain name? (demo.pyrite.dev? try.pyrite.dev?)
