---
id: named-rubric-checkers
title: "Named Rubric Checkers: Explicit Binding Between Rubric Items and Validation Functions"
type: backlog_item
tags:
- feature
- qa
- intent-engineering
- plugins
- schema
kind: feature
priority: high
effort: L
status: proposed
links:
- target: intent-layer
  relation: builds_on
  note: "Addresses the rubric-to-checker binding gap identified in intent layer Phase 2"
- target: qa-service
  relation: modifies
- target: rubric-checkers
  relation: modifies
- target: intent-layer-guidelines-and-goals
  relation: builds_on
  note: "Implements the 'deterministic rubric items become validation rules' design"
---

## Problem

The intent layer (Phase 1: done, Phase 2: in progress) defines evaluation rubrics in kb.yaml that describe quality standards for entries. The QA service is supposed to enforce these rubrics, but the bridge between rubric items and checker functions is broken in practice.

**The current design:** Rubric items are natural-language strings in kb.yaml. The QA service matches them to checker functions via regex pattern matching against the text. Items that don't match any pattern fall through to "judgment-only" (LLM evaluation), which is silently skipped when no LLM is configured.

**What actually happens in production:** Across the demo KBs (blank, boyd, wardley, kb-ideas), 84% of rubric items silently do nothing. They don't match any regex pattern, no LLM is configured, so they're skipped without feedback. The KB author has no way to know which items are enforced and which are decorative.

Specific failure modes observed:

1. **Pattern mismatch:** The rubric item `"Person has a role described"` doesn't match the checker regex `r"role or position"`. A checker exists but doesn't fire. Silent failure.

2. **Schema/rubric overlap:** `"Writing has a date"` and `"Writing has a writing_type classification"` are already enforced as required fields by schema validation. But the rubric system doesn't know this — it would try to send them to the LLM as judgment items, duplicating a structural check that already runs.

3. **No feedback on coverage:** `pyrite qa validate` reports structural violations but never tells you which rubric items have checkers, which are judgment-only, and which fell through a gap. The operator can't distinguish "rubric item is waiting for LLM" from "rubric item is broken."

4. **Plugin-provided checkers don't exist:** Domain plugins (intellectual-biography, journalism, software) can't ship their own checkers. The only extension point is the core regex registry, which requires modifying pyrite core code.

This is the gap between Phase 1 (schema + storage, done) and Phase 2 (rubric evaluation becomes real). The rubric items are stored and surfaced to agents, but enforcement is held together by fragile regex matching that breaks whenever a KB author writes rubric text that doesn't happen to match a hardcoded pattern.

## Root Cause

The regex-matching bridge assumes a closed vocabulary of rubric item phrasings. This worked when rubric items were all system-defined (4 items in SYSTEM_INTENT with matching patterns). It breaks when KB authors write domain-specific rubric items in natural language — which is exactly what the intent layer was designed for.

The fix isn't better regex. It's explicit binding: rubric items name their checker, checkers are registered by name, unknown checkers produce visible warnings.

## Solution

### 1. Named Checker Registry

Checkers get explicit string names. Core ships a set of named checkers. Plugins register additional checkers via a new protocol method.

**Core checkers** (in `rubric_checkers.py`):

```python
NAMED_CHECKERS: dict[str, RubricChecker] = {
    # Structural
    "descriptive_title": check_descriptive_title,
    "has_tags": check_has_tags,
    "has_outlinks": check_has_outlinks,
    "status_present": check_status_present,
    "priority_present": check_priority_present,

    # Parameterized field presence
    "has_field": check_has_field,           # params: {field: "role"}
    "has_any_field": check_has_any_field,   # params: {fields: ["url", "author"]}

    # Body structure
    "body_has_section": check_body_has_section,     # params: {heading: "Problem"}
    "body_has_heading": check_body_has_heading,     # params: {heading: "Sources"} — checks for ## heading
    "body_has_pattern": check_body_has_pattern,     # params: {pattern: "Sources?:"} — raw regex, power users
    "body_has_code_block": check_body_has_code_block,
}
```

**Plugin checkers** (new protocol method on `PyritePlugin`):

```python
def get_rubric_checkers(self) -> dict[str, RubricChecker]:
    """Return named rubric checker functions.

    Returns:
        Dict mapping checker name to callable.
        Names should be namespaced: "plugin_name.checker_name"

        Example: {"cascade.has_source_chain": check_source_chain}
    """
    ...
```

**Aggregation** in `PluginRegistry`:

```python
def get_all_rubric_checkers(self) -> dict[str, RubricChecker]:
    """Collect named checkers from core + all plugins."""
    checkers = dict(NAMED_CHECKERS)
    for plugin in self._plugins.values():
        if hasattr(plugin, "get_rubric_checkers"):
            plugin_checkers = plugin.get_rubric_checkers()
            for name, fn in plugin_checkers.items():
                if name in checkers:
                    logger.warning("Checker '%s' from '%s' shadows existing", name, plugin.name)
                checkers[name] = fn
    return checkers
```

### 2. Rubric Item Format

Rubric items in kb.yaml become a union type: plain strings (judgment-only) or dicts with explicit checker binding.

```yaml
evaluation_rubric:
  # Bound to a named checker — runs deterministically
  - text: "Entry cites at least one source"
    checker: body_has_heading
    params: {heading: "Sources"}

  # Bound to a plugin checker
  - text: "Body describes significance, not just contents"
    checker: intellectual_biography.significance_section

  # Parameterized core checker
  - text: "Person has a role described"
    checker: has_field
    params: {field: role}

  # Explicitly marks overlap with schema required fields
  - text: "Writing has a date"
    covered_by: schema

  # Judgment-only — deferred to LLM, skipped without one
  - "Intellectual influences are specific and attributed, not vague"
  - "Co-authors listed where applicable"
```

Three forms:
- **`{text, checker, params?}`** — bound to a named checker, runs deterministically
- **`{text, covered_by: schema}`** — explicitly marks that another validation system handles this, skip
- **plain string** — judgment-only, evaluated by LLM when available

### 3. Checker Signature

Add an optional `params` argument to the checker signature:

```python
# Current
RubricChecker = Callable[[dict[str, Any], KBSchema | None], dict[str, Any] | None]

# New (named checkers)
NamedRubricChecker = Callable[[dict[str, Any], KBSchema | None, dict[str, Any] | None], dict[str, Any] | None]
```

The `params` dict contains:
- `rubric_text: str` — the human-readable text from the rubric item
- Any checker-specific parameters from the `params` key in kb.yaml

This eliminates the factory function pattern. Instead of `_make_metadata_field_checker("role")` generating a closure, the generic `check_has_field` receives `{field: "role"}` at call time.

**Backward compatibility:** The legacy regex code path continues to call checkers with two arguments `(entry, schema)`. Named checkers are called with three arguments `(entry, schema, params)`. Checkers that appear in both registries (i.e., existing checkers migrated to `NAMED_CHECKERS`) must accept `params=None` as a default. New checkers only used via the named path can require `params`.

### 4. Schema Changes

**`TypeSchema.evaluation_rubric`** changes from `list[str]` to `list[str | dict]`:

```python
@dataclass
class TypeSchema:
    # ...
    evaluation_rubric: list[str | dict[str, Any]] = field(default_factory=list)
```

**`KBSchema.evaluation_rubric`** — same change.

**Parsing in `KBSchema.from_dict()`** — already handles YAML lists; dicts and strings both parse naturally from YAML. The existing `list[str]` type annotation is the only thing that needs to change.

**`to_agent_schema()`** — passes rubric items through unchanged. Agents see both forms.

### 5. QA Evaluation Flow

```python
def _check_rubric_evaluation(self, entry, issues):
    rubric_items = self._get_rubric_items(entry_type, kb_name)
    checkers = get_registry().get_all_rubric_checkers()

    for item in rubric_items:
        if isinstance(item, str):
            # Legacy string — try regex fallback, else judgment-only
            checker = match_rubric_item(item)  # existing regex bridge
            if checker:
                result = checker(enriched, kb_schema, None)
                if result:
                    issues.append(result)
            else:
                judgment_items.append(item)
            continue

        if isinstance(item, dict):
            if item.get("covered_by"):
                continue

            checker_name = item.get("checker")
            if not checker_name:
                judgment_items.append(item.get("text", ""))
                continue

            fn = checkers.get(checker_name)
            if fn is None:
                issues.append({
                    "entry_id": entry["id"],
                    "kb_name": entry["kb_name"],
                    "rule": "config_error",
                    "severity": "warning",
                    "field": "evaluation_rubric",
                    "message": f"Unknown checker '{checker_name}' in rubric for '{entry_type}'",
                })
                continue

            params = dict(item.get("params", {}))
            params["rubric_text"] = item.get("text", "")
            result = fn(enriched, kb_schema, params)
            if result:
                issues.append(result)
```

Key behaviors:
- **Unknown checker name → visible warning.** No silent failure.
- **Plain strings → legacy regex fallback** during transition, then judgment-only.
- **`covered_by: schema` → skip.** Replaces the brittle `is_already_covered()` regex list.
- **Deduplication:** When the same rubric text appears as both a string and a dict (e.g., inherited as a string from SYSTEM_INTENT, overridden as a dict in kb.yaml), the dict wins — it carries more specific binding information. Dedup key is the text content.
- **Bulk path (`_check_rubric_all`):** Iterates entries and calls checkers per-entry (same as today). No SQL-level optimization needed — parameterized checkers require per-entry evaluation.
- **Validate summary:** `pyrite qa validate` output includes a count of judgment-only items deferred: e.g., `"judgment_deferred": 5` in the JSON response, or "5 rubric items deferred (no LLM configured)" in human-readable output. This is the primary feedback loop for operators with unchecked rubric items.

### 6. Discoverability CLI

```
$ pyrite qa checkers
Core:
  descriptive_title    Check for generic/placeholder titles
  has_tags             Entry has at least one tag
  has_outlinks         Entry links to at least one related entry
  has_field            Metadata field is present (parameterized)
  has_any_field        At least one of several fields present
  body_has_section     Markdown heading present in body
  body_has_pattern     Regex pattern found in body
  body_has_code_block  Code block present in body
  status_present       Entry has a status value
  priority_present     Entry has a priority value

Plugin (intellectual_biography):
  intellectual_biography.sources_cited          Sources cited in body
  intellectual_biography.significance_section   Significance/impact section present

$ pyrite qa checkers --kb blank
Rubric coverage for blank:

  KB-level rubric (6 items):
    [checker]   "Entry cites at least one source" → body_has_pattern
    [judgment]  "Methodology claims specify which version/era..."
    [judgment]  "People entries describe the specific relationship..."
    [judgment]  "Metrics include date of measurement"
    [judgment]  "Intellectual influences are specific and attributed"
    [judgment]  "Cross-KB connections are noted where relevant"

  Type: writing (4 items):
    [checker]   "Body describes significance" → intellectual_biography.significance_section
    [schema]    "Writing has a date" (covered by required field)
    [schema]    "Writing has a writing_type" (covered by required field)
    [judgment]  "Co-authors listed where applicable"

  Summary: 2 checker-bound, 2 schema-covered, 5 judgment-only
```

### 7. Backward Compatibility

- Plain string rubric items continue to work (judgment-only with regex fallback)
- Existing kb.yaml files require no changes
- The regex-matching bridge (`match_rubric_item`) remains as legacy fallback
- Factory functions (`_make_metadata_field_checker` etc.) remain for any code that calls them directly
- The `is_already_covered()` function remains but `covered_by: schema` is the preferred mechanism

### 8. Plugin Skill Integration

Each domain plugin ships a Claude Code skill that knows the plugin's available checkers. When an AI assistant creates an entry, the skill guides it to produce content that will pass the checkers.

Example skill knowledge for the intellectual-biography plugin:

```
When creating person entries in an intellectual-biography KB:
- Include a "## Relationship" section describing the connection
  to the subject (checker: intellectual_biography.relationship_described)
- End the body with "Sources: ..." listing references
  (checker: intellectual_biography.sources_cited)
- Include a "## Significance" section for writing entries
  (checker: intellectual_biography.significance_section)

The skill knows checker names so it can tell the agent exactly what
will be validated. Entries pass validation on first creation.
```

This closes the loop: intent (kb.yaml rubric) → creation guidance (skill) → validation (named checker) → feedback (QA report). No gap where quality standards exist but aren't enforced or communicated.

## Implementation Plan

### Step 1: Named Checker Registry [S]

- Add `NAMED_CHECKERS` dict to `rubric_checkers.py`, registering existing checkers by name
- Add `get_rubric_checkers()` to `PyritePlugin` protocol
- Add `get_all_rubric_checkers()` to `PluginRegistry`
- Update `RubricChecker` type alias to accept optional `params` argument
- Adapt existing checker functions to accept `params` (backward compatible — `params=None` default)
- Tests: checker registration, plugin aggregation, namespace collision warning

### Step 2: Mixed-Format Rubric Items [S]

- Change `TypeSchema.evaluation_rubric` from `list[str]` to `list[str | dict[str, Any]]`
- Same for `KBSchema.evaluation_rubric`
- Update `from_dict()` parsing (minimal — YAML already handles both)
- Update `to_agent_schema()` to pass through both forms
- Update `_get_rubric_items()` return type and deduplication logic (dedup on text, not full dict)
- Tests: parsing, serialization, agent schema export with mixed rubric items

### Step 3: QA Evaluation with Named Lookup [M — this is the bulk of the work]

- Rewrite `_check_rubric_evaluation()` to handle string and dict rubric items
- Named checker lookup with unknown-checker warning
- `covered_by: schema` support
- Legacy regex fallback for plain strings
- Update `_check_rubric_all()` bulk path to match
- Tests: named lookup, unknown checker warning, covered_by skip, legacy fallback, params passing

### Step 4: Discoverability CLI [S]

- `pyrite qa checkers` — lists all available checkers (core + plugins)
- `pyrite qa checkers --kb <name>` — shows rubric coverage for a KB
- Shows checker-bound, schema-covered, and judgment-only counts

### Step 5: Migrate Demo KBs [S]

- Update blank, boyd, wardley, kb-ideas kb.yaml files to use named checkers where appropriate
- Mark schema-covered items with `covered_by: schema`
- Verify `pyrite qa validate` produces clean results with the new format

## Open Questions

**Should SYSTEM_INTENT rubric items migrate to named format?** The four system-level items ("descriptive title", "body non-empty", "has tags", "has outlinks") currently work via regex matching. They could stay as legacy strings (they work), or migrate to named-checker dicts to serve as the canonical example of the new format. Recommendation: migrate them — they're the first thing a new developer sees and should demonstrate the preferred pattern. This is a small change in `core_types.py`.

## What This Does Not Include

- **New domain-specific checkers.** This proposal adds the infrastructure for named checkers. Building the intellectual-biography plugin with domain-specific checkers (sources_cited, significance_section, relationship_described) is a separate backlog item that depends on this one.
- **LLM rubric evaluation changes.** The judgment-only path is unchanged. LLM evaluation continues to work for items without a named checker. This proposal makes the boundary between deterministic and judgment-only explicit rather than implicit.
- **Deprecation of regex matching.** The legacy regex bridge remains as fallback. A future backlog item can deprecate it once all shipped KBs use named checkers.

## Success Criteria

- KB authors can bind rubric items to named checkers in kb.yaml
- Unknown checker names produce a visible warning in `pyrite qa validate`
- Plugins can register domain-specific checkers via `get_rubric_checkers()`
- `pyrite qa checkers` shows available checkers and per-KB coverage
- Existing KBs with plain-string rubric items continue to work unchanged
- The demo KBs (blank, boyd, wardley) use named checkers for all deterministic items
- Zero silent failures: every rubric item is either checker-bound, schema-covered, judgment-only, or produces a warning
