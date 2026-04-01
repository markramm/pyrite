---
id: fix-systematic-silent-data-loss-in-to-frontmatter-across-all-entry-types
title: Fix systematic silent data loss in to_frontmatter across all entry types
type: backlog_item
tags:
- bug
- data-loss
- systematic
importance: 5
kind: bug
status: completed
priority: critical
effort: L
rank: 0
---

## Problem

Every typed entry's to_frontmatter() method uses guards that suppress fields when they equal their default value. This conflates 'not set' with 'explicitly set to the default.' Three patterns cause silent data loss on save/round-trip:

1. **!= default guard**: `if self.status != "proposed"` drops explicitly-set default enum values (20+ fields)
2. **Falsy guard on int/bool**: `if self.rank:` drops 0 and False (8+ fields)
3. **MCP allowlist**: `_UPDATE_FIELDS` frozenset missing valid update fields

## Scope

~39 confirmed bugs across:
- pyrite/models/core_types.py (PersonEntry, OrgEntry, RelationshipEntry, QAAssessmentEntry)
- pyrite/models/task.py (TaskEntry)
- pyrite/models/collection.py (CollectionEntry)
- extensions/software-kb (ADREntry, BacklogItemEntry, MilestoneEntry)
- extensions/cascade (ActorEntry, ThemeEntry, VictimEntry, StatisticEntry, MechanismEntry)
- extensions/journalism-investigation (ClaimEntry, EvidenceEntry, DocumentSourceEntry, InvestigationEventEntry, TransactionEntry, OwnershipEntry, MembershipEntry, FundingEntry)
- extensions/encyclopedia (ArticleEntry)
- extensions/zettelkasten (ZettelEntry)
- extensions/social (WriteupEntry, UserProfileEntry)
- pyrite/server/mcp_server.py (_UPDATE_FIELDS allowlist)

## Fix

Always write the field. Remove != default guards and falsy guards on meaningful fields. Expand MCP _UPDATE_FIELDS.

## Root Cause

Discovered while fixing 4 specific instances (importance, event status, subdirectory override, source extra fields) in commit 7783335.
