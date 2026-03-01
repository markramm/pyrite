---
id: investigative-journalism-plugin
title: "Investigative Journalism Plugin (Wave 3)"
type: backlog_item
tags:
- feature
- plugin
- journalism
- osint
- wave-3
kind: feature
priority: medium
effort: XL
status: planned
links:
- launch-plan
- bhag-self-configuring-knowledge-infrastructure
- roadmap
---

## Problem

Investigative journalists and OSINT researchers track complex webs of people, organizations, financial flows, and events. Current tools are either too generic (spreadsheets, Notion) or too specialized (Maltego, i2 Analyst's Notebook — expensive, proprietary). The knowledge graph they build manually could be built and validated by AI agents, with humans directing the investigation and verifying findings.

## Solution

A Pyrite plugin that provides entity types, workflows, and tools for investigative research. "Follow the money" as structured, validated, AI-augmented knowledge.

### Entry Types

- `person` — name, aliases, roles, affiliations, date of birth, known associates
- `organization` — name, type (company/ngo/government/etc), jurisdiction, registration data, key personnel
- `financial_flow` — source, destination, amount, date, type (donation/payment/investment/grant), evidence links
- `event` — date, location, participants, significance, source chain
- `document` — source document with provenance (court filing, tax record, leaked document, public filing)
- `finding` — investigative conclusion with confidence level, supporting evidence chain, counter-evidence
- `lead` — unverified tip or thread to follow, priority, assigned agent/person
- `timeline_entry` — chronological record linking events, documents, and financial flows

### Workflows

- **Source chain validation**: Every claim must link to a source document. Agents can't create findings without evidence.
- **Confidence scoring**: Findings rated by evidence strength (single source, corroborated, confirmed, contested)
- **Lead triage**: New leads enter as unverified, get prioritized, assigned to agents or humans for follow-up
- **Cross-reference detection**: AI identifies connections between entities that haven't been explicitly linked
- **Timeline construction**: Automated chronological ordering of events and financial flows

### Investigation-Specific Tools

- `inv_follow_money` — trace financial flows between entities, flag gaps in the chain
- `inv_cross_reference` — find connections between entities via shared associates, organizations, events
- `inv_source_verify` — validate source chain completeness for a finding
- `inv_timeline` — generate chronological view of an investigation thread
- `inv_entity_profile` — comprehensive dossier for a person or organization from all linked entries

### QA Integration

- Source chain completeness check: findings without adequate sourcing flagged by QA
- Confidence level validation: findings claiming "confirmed" must have corroborating sources
- Entity deduplication: QA detects duplicate person/org entries (aliases, misspellings)
- Temporal consistency: event dates and financial flow dates cross-checked

## Prerequisites

- Wave 1 platform shipped (0.8 alpha)
- QA Phase 1 (structural validation) for source chain checking
- Task plugin for lead assignment and investigation coordination

## Success Criteria

- Full investigation workflow: create entities → track financial flows → generate findings with source chains
- Source chain validation enforced: no "orphan findings" without evidence
- Cross-reference detection surfaces non-obvious connections
- Demo: "Follow the money" investigation of a public dataset (campaign finance, corporate filings)
- Investigation skill can drive agent-led research across the KB

## Launch Context

This is the **wave 3** plugin. Launches 1-2 weeks after wave 2 (software plugin). Audience: researchers, OSINT practitioners, journalists. Message: "Follow the money — structured investigations with AI." Demonstrates that Pyrite is genuinely general-purpose: the same platform that manages software projects also drives investigative journalism. Different domain, same infrastructure.
