---
id: collection-query-service
title: Collection Query Service
type: component
kind: service
path: pyrite/services/collection_query.py
owner: core
dependencies: [kb-service, storage-layer]
tags:
- core
- collections
- search
---

Query DSL parser and evaluator for virtual collections. Parses inline query strings (e.g., `type:backlog_item status:proposed tags:core`) into `CollectionQuery` dataclass, validates against known fields, and evaluates against the database with configurable TTL caching (default 60s).

Key functions:
- `parse_query()` — parse inline query string to CollectionQuery
- `query_from_dict()` — build from collection metadata dict
- `validate_query()` — return list of validation errors
- `evaluate_query()` — execute query against database
- `evaluate_query_cached()` — cached evaluation with SHA256 key + TTL
