---
type: backlog_item
title: "Web Clipper"
kind: feature
status: proposed
priority: low
effort: M
tags: [web, import, phase-5]
---

Capture web content into Pyrite:

**Backend:**
- `POST /api/clip` — accepts URL, fetches page, converts HTML to Markdown, creates entry
- Extracts title, meta description, main content
- Stores source URL in metadata

**Frontend:**
- Clip page in web app (paste URL → preview → save)
- Bookmarklet for one-click clipping from any page
- Tag and KB selection before saving

Enables research capture workflow without leaving the browser.
