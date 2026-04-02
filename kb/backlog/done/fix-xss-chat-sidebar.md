---
id: fix-xss-chat-sidebar
title: "Fix XSS: Escape AI response content in ChatSidebar"
type: backlog_item
tags: [security, xss, frontend]
kind: bug
status: done
priority: critical
effort: S
---

## Problem

`web/src/lib/components/ai/ChatSidebar.svelte:101` — `{@html renderCitations(msg.content)}` converts `[[entry-id]]` to anchor tags but does NOT escape the surrounding text. If an AI response contains HTML, it renders directly.

## Fix

HTML-escape the entire content string before applying the wikilink regex replacement. Consider using DOMPurify for `{@html}` blocks.
