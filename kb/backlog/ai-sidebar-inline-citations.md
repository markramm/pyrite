---
id: ai-sidebar-inline-citations
type: backlog_item
title: "AI sidebar: require inline [[entry-id]] citations in responses"
kind: improvement
status: proposed
priority: medium
effort: S
tags: [ai, web-ui, grounding, ux]
---

## Problem

`pyrite/server/endpoints/ai_ep.py` retrieves top-N source entries via
search and concatenates body previews into the prompt. The frontend
(`web/src/lib/components/ai/ChatSidebar.svelte`) renders a "Sources:"
footer beneath each assistant message and converts `[[entry-id]]` in the
response into clickable links — but the system prompt doesn't actually
instruct the model to emit those citations inline. So the body of the
response is rarely (or never) grounded, even though the rendering
machinery exists.

Net: users see "the AI says X" with a list of unattached sources below.
Hallucinations don't get caught because individual sentences aren't tied
to specific entries.

## Solution

1. Update the AI-sidebar system prompt to require `[[entry-id]]` citations
   on every load-bearing claim. Include 1-2 examples of correct usage.
2. The retrieved-context block now lists each entry's `id` prominently so
   the model can cite it correctly.
3. Add a lightweight post-processing pass: if the response cites IDs not
   in the retrieved set, log a warning (hallucination signal).
4. UI: when an `[[id]]` citation is hovered, show a quick preview popover
   pulling from the already-fetched source data (no extra request).

## Acceptance criteria

- AI sidebar responses include inline `[[entry-id]]` citations for
  fact-bearing sentences.
- Citations link to the entry as they already do.
- Hover preview works without an additional fetch.
- Out-of-scope citations (IDs not in retrieved sources) are logged.
- Manual test: ask a question that requires citing 3+ sources, verify all
  three appear inline.

## Related

- `llm-prompt-caching` — same code path, sequence the work
- `ai-hallucination-detection-for-research-kbs` (done) — same concept,
  applied here in real time
