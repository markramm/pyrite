---
id: journalist-onboarding-flow-and-kb-orientation
title: Journalist Onboarding Flow and KB Orientation
type: backlog_item
tags:
- web
- ux
- journalism
- onboarding
links:
- target: epic-journalists-pyrite-wiki-hosted-research-platform-for-independent-journalists
  relation: subtask_of
  kb: pyrite
importance: 5
---

## Problem

An invited journalist needs to go from invitation to productive research quickly. The current setup assumes a developer audience. Journalists need a guided onboarding that explains what they have access to and how to start investigating.

## Solution

1. **Invitation system** -- Admin generates invite link, journalist signs up with email/GitHub
2. **Onboarding wizard** -- First-login flow that:
   - Explains the available KBs and what they contain
   - Prompts for BYOK API key setup
   - Offers a guided first search across the pre-populated KBs
   - Shows how to create their own KB for their investigation
3. **KB orientation view** -- For each pre-populated KB, a landing page showing scope, entry count, key entities, sample queries, and a "start exploring" button
4. **Quick start templates** -- Pre-built search queries and workflow templates relevant to common investigation angles

## Success Criteria

- Journalist goes from invite to first meaningful search in under 5 minutes
- No technical knowledge required beyond entering an API key
- Clear documentation of what each KB contains and how to use it
