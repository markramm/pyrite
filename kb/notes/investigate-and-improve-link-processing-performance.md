---
id: investigate-and-improve-link-processing-performance
title: Investigate and improve link processing performance
type: backlog_item
tags:
- performance
- links
kind: improvement
effort: M
---

## Problem

Link processing operations (creation, querying, test execution) are noticeably slow. This was observed during development when link-related tests took significantly longer than other test suites, and bulk link operations show latency that compounds at scale.

## Symptoms

- Link command tests are slow compared to other CLI test suites
- Bulk link operations show per-link overhead that compounds
- Agent workflows doing cross-KB linking are bottlenecked by link processing

## Investigation Areas

- Index sync frequency during link operations (per-link vs batch)
- Link storage format (frontmatter YAML rewriting vs DB-only)
- Query performance for backlink lookups
- File I/O during link creation (full file rewrite per link?)

## Acceptance Criteria

- Root cause(s) identified with profiling data
- At least 2x improvement in bulk link creation throughput
- Link-related test suite runs in under 5 seconds
- No regression in link data integrity
