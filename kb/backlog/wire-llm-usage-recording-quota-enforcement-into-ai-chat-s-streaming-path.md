---
id: wire-llm-usage-recording-quota-enforcement-into-ai-chat-s-streaming-path
title: Wire LLM usage recording + quota enforcement into ai_chat's streaming path
type: backlog_item
tags:
- auth
- tech-debt
- quotas
importance: 5
kind: task
status: proposed
priority: medium
effort: M
rank: 0
---

## Problem

ai_chat (POST /api/ai/chat) is the only one of the 4 AI endpoints not
covered by check_llm_quota, because it calls LLMService.stream()
rather than .complete(), and .stream() has no usage-recording path at
all -- only _anthropic_complete() calls _record_anthropic_usage().
Discovered while wiring wire-user-usage-tier-resolution-for-
quota-enforcement into the other 3 endpoints (summarize/auto-tag/
suggest-links), all of which use .complete().

Streaming responses don't get a single Anthropic SDK response object
with a usage attribute up front the way non-streaming calls do -- the
usage totals only become available after the stream is fully consumed
(typically via a final message_delta/message_stop event or the stream
object's accumulated usage). This needs its own design, not a
copy-paste of _record_anthropic_usage().

## Fix

1. Determine how to capture token usage from client.messages.stream()
   (check the Anthropic SDK's streaming response object for a final
   usage total after iteration completes).
2. Add usage recording to _anthropic_stream() / wherever chat's
   streaming loop lives, tagged kind="chat".
3. Wire _enforce_llm_quota(kind="chat") into ai_chat, before starting
   the stream (pre-check, same as the other 3 endpoints) -- can't
   retroactively deny a response that's already started streaming.

## Acceptance criteria

- Chat requests are recorded in llm_usage with kind="chat" and real
  token counts (not zeros).
- Over-quota chat requests are denied (429) before any tokens stream
  to the client.
- Existing chat tests (test_ai_endpoints.py::TestAIChat) still pass.
