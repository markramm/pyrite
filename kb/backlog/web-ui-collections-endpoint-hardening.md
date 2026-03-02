---
id: web-ui-collections-endpoint-hardening
title: "Harden Collections Create Endpoint"
type: backlog_item
tags:
- bug
- api
- validation
kind: bug
priority: medium
effort: XS
status: proposed
---

## Problem

The collections create endpoint has incomplete validation and unused request fields:

- `collection_type` field in `CreateCollectionRequest` schema is accepted but never used by the endpoint handler
- No validation for duplicate collection slugs in the same folder
- Unclear behavior when creating a collection with a slug that already exists (silently overwrites? returns error?)

## Solution

- Either use `collection_type` in the collection metadata (e.g., `metadata.type`) or remove it from the request schema
- Add slug uniqueness validation in the endpoint
- Return 409 Conflict if a collection with the same slug already exists in the folder
- Document the behavior in API docs

## Success Criteria

- `collection_type` is either used in metadata or removed from schema (consistency)
- Duplicate slug detection and validation implemented
- 409 Conflict returned for slug collisions
- Endpoint behavior documented
