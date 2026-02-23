---
type: standard
title: "Python Code Style"
category: coding
enforced: true
tags: [python, style]
---

## Formatting
- Ruff for linting and formatting (configured in pyproject.toml)
- Line length: 100 characters
- Target: Python 3.11+

## Naming
- snake_case for functions, variables, modules
- PascalCase for classes
- UPPER_SNAKE for constants and enum tuples

## Type Hints
- Use modern syntax: `list[str]` not `List[str]`, `str | None` not `Optional[str]`
- Type annotations on public API functions

## Imports
- Standard library, third-party, local — separated by blank lines
- Ruff handles import sorting (isort rules)
