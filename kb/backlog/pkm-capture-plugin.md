---
id: pkm-capture-plugin
title: "PKM Capture Plugin — Frictionless Knowledge Ingestion"
type: backlog_item
tags:
- feature
- plugin
- pkm
- capture
- mobile
kind: feature
priority: medium
effort: L
status: planned
links:
- launch-plan
- bhag-self-configuring-knowledge-infrastructure
---

## Problem

PKM users (Obsidian, Anytype, Logseq) need frictionless capture: snap a photo, paste a URL, record a voice note, clip a web page. Current Pyrite workflows require CLI or web editor — too much friction for mobile/on-the-go capture. Without a low-friction capture path, Pyrite can't credibly serve the PKM audience.

## Solution

A Pyrite plugin that provides capture workflows: ingest raw content (images, URLs, voice, text), classify it using AI, extract structure, and create typed KB entries automatically. The human captures; the AI files.

### Entry Types

- `capture` — raw ingested content before classification (ephemeral, processed into typed entries)
- `clipping` — web clippings with source URL, extracted content, summary
- `note` — quick text captures, voice transcriptions, brain dumps
- `bookmark` — URLs with metadata, tags, summary
- `reading_highlight` — extracted quotes/annotations from articles or documents

### Capture Workflows

Each workflow follows the same pipeline: **Ingest → Classify → Extract → Create typed entry → Link**

| Input | Processing | Output |
|-------|-----------|--------|
| **Image** | OCR or vision model describes content | Typed entry (note, document reference, whiteboard capture) |
| **URL** | Fetch, extract content, summarize | `clipping` or `bookmark` with auto-tags |
| **Voice note** | Transcribe (Whisper or similar), summarize | `note` with transcript, extracted action items |
| **Pasted text** | Classify, extract structure | Typed entry based on content (note, quote, reference) |
| **PDF/document** | Extract text, chunk if needed | One or more entries with relationships |
| **Web clipping** (browser extension or share sheet) | Extract article content, metadata | `clipping` with source chain |

### AI Integration

- **Auto-classification**: BYOK model determines entry type based on content and KB schema
- **Auto-tagging**: Extract topics, entities, themes from captured content
- **Auto-linking**: Suggest connections to existing KB entries based on semantic similarity
- **Summarization**: Generate concise summaries for long-form captures
- **Action extraction**: Pull out todos, decisions, questions from voice notes and text

### Interfaces

- **Web UI quick-capture**: Minimal form — paste/type/upload, one click to ingest. Mobile-responsive.
- **Claude app**: Capture through conversation — "save this to my KB" with auto-classification
- **MCP tools**: `capture_ingest`, `capture_classify`, `capture_process` for programmatic access
- **CLI**: `pyrite capture <file-or-url>` for power users and scripts
- **Browser extension** (future): Right-click → save to Pyrite
- **Share sheet** (future): Mobile share → Pyrite capture

## Prerequisites

- BYOK AI integration in web UI (for classification and summarization)
- Mobile-responsive web UI
- Waves 1-3 shipped (platform credibility before targeting PKM audience)

## Success Criteria

- Capture-to-typed-entry in under 5 seconds for text/URL inputs
- Auto-classification accuracy > 80% for common content types
- Mobile web UI capture works smoothly on phone browsers
- Obsidian vault migration: `pyrite init --from-obsidian <vault-path>` creates a working KB
- 10+ entries captured via web/mobile in first week of use by test users

## Launch Context

This is the **wave 4** plugin in the launch plan. Waves 1-3 establish platform credibility with agent builders, dev teams, and researchers. Wave 4 opens the aperture to everyone who collects and organizes information. By this point, three shipping plugins prove the platform works — the PKM crowd hears "software teams, journalists, and AI agents all use this" before being asked to try it themselves.
