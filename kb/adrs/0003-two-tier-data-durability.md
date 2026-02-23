---
type: adr
title: "Two-Tier Data Durability Model"
adr_number: 3
status: accepted
deciders: ["markr"]
date: "2025-10-15"
tags: [architecture, storage, data-model]
---

## Context

Some data (articles, notes, ADRs) is core knowledge that must survive clone/fork. Other data (votes, reviews, reputation scores) is engagement metadata that is high-volume, needs fast aggregation, and is inherently local.

## Decision

Two tiers:
- **Content tier** (markdown files): git-tracked, portable. Entries, profiles, articles, ADRs.
- **Engagement tier** (SQLite tables): local-only, not git-tracked. Votes, reputation, reviews, edit history.

## Consequences

- `git clone` gives full content but zero engagement data
- Backup requires both repo + database
- Federation of engagement data is a future backlog item (CRDTs, ActivityPub, or lightweight file format)
- Plugin DB tables (social_vote, encyclopedia_review) live in the engagement tier
