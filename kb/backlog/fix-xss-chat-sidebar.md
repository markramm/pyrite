---
id: fix-xss-chat-sidebar
type: backlog_item
title: "Fix XSS: Escape AI response content in ChatSidebar"
kind: bug
status: proposed
priority: critical
effort: S
tags: [security, xss, frontend]
epic: epic-release-readiness-review
---

## Problem

`web/src/lib/components/ai/ChatSidebar.svelte:101` — `{@html renderCitations(msg.content)}` converts `[[entry-id]]` to anchor tags but does NOT escape the surrounding text. If an AI response contains HTML, it renders directly.

## Fix

HTML-escape the entire content string before applying the wikilink regex replacement. Consider using DOMPurify for `{@html}` blocks.
