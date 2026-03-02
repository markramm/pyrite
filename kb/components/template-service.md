---
id: template-service
title: Template Service
type: component
kind: service
path: pyrite/services/template_service.py
owner: core
dependencies:
- pyrite.config
tags:
- core
- service
---

Manages user-defined markdown templates that scaffold new KB entries. Templates are stored as markdown files with YAML frontmatter in each KB's templates directory. Supports variable substitution (`{{date}}`, `{{author}}`, `{{title}}`) and per-type defaults.

## Consumers

- REST API: `/api/kbs/{kb}/templates`, `/api/kbs/{kb}/templates/{name}/render`
- Web UI: template picker in entry creation flow

## Related

- [[kb-service]] — entry creation uses rendered templates
- [[rest-api]] — template endpoints
