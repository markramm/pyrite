---
type: component
title: "Format System"
kind: module
path: "pyrite/formats/"
owner: "markr"
dependencies: ["ruamel.yaml", "csv", "json"]
tags: [core, formats, import-export]
---

# Format System

The format system provides pluggable serialization (export) and deserialization (import) of entries across multiple file formats. It powers content negotiation in the REST API and bulk import/export in the CLI.

## Key Files

| File | Purpose |
|------|---------|
| `pyrite/formats/__init__.py` | `FormatRegistry`, `FormatSpec`, `negotiate_format()`, `format_response()` |
| `pyrite/formats/json_fmt.py` | JSON serializer (`json_serialize`) |
| `pyrite/formats/markdown_fmt.py` | Markdown serializer |
| `pyrite/formats/csv_fmt.py` | CSV serializer |
| `pyrite/formats/yaml_fmt.py` | YAML serializer |
| `pyrite/formats/importers/__init__.py` | `ImporterRegistry`, importer registration |
| `pyrite/formats/importers/json_importer.py` | JSON importer (`import_json`) |
| `pyrite/formats/importers/markdown_importer.py` | Markdown importer (`import_markdown`) |
| `pyrite/formats/importers/csv_importer.py` | CSV importer (`import_csv`) |

## Export: `FormatRegistry`

### `FormatSpec` Dataclass

Each format is described by a `FormatSpec` with `name`, `media_type`, `file_extension`, and a `serializer` callable `(data, **kwargs) -> str`.

### Registered Formats

| Name | Media Type | Extension | Serializer |
|------|-----------|-----------|------------|
| `json` | `application/json` | `.json` | `json_serialize` (indented, `default=str`) |
| `markdown` | `text/markdown` | `.md` | `markdown_serialize` |
| `csv` | `text/csv` | `.csv` | `csv_serialize` |
| `yaml` | `text/yaml` | `.yaml` | `yaml_serialize` |

### Key Functions

- **`get_format_registry()`** -- Returns the global singleton `FormatRegistry`, lazily initializing and registering the four default formats on first call.
- **`format_response(data, format_name, **kwargs)`** -- Looks up the format by name, calls its serializer, and returns a `(content_string, media_type)` tuple.

## Content Negotiation

**`negotiate_format(accept_header: str) -> str | None`**

Parses the HTTP `Accept` header, sorts by quality factor (`q=`), and returns the name of the best matching format. Defaults to `"json"` for `*/*` or empty headers. Returns `None` when no registered format matches (signaling HTTP 406).

## Import: `ImporterRegistry`

### Registered Importers

| Name | Importer |
|------|----------|
| `json` | `import_json` |
| `markdown` | `import_markdown` |
| `csv` | `import_csv` |

### Key Functions

- **`get_importer_registry()`** -- Returns the global singleton `ImporterRegistry`, lazily registering the three default importers on first call.
- **`registry.get(name)`** -- Returns the importer callable for a given format name.
- **`registry.available_formats()`** -- Lists registered importer names.

## Design Notes

- Both registries are module-level singletons with lazy initialization, so format modules are only imported when first needed.
- Serializers are plain functions, not classes -- they take `(data, **kwargs)` and return a string. This keeps the interface minimal and composable.
- The content negotiation implementation is intentionally simplified: it handles `Accept` headers with quality factors but does not implement full RFC 7231 precedence rules.
- Adding a new format requires writing a serializer function and calling `registry.register(FormatSpec(...))` -- no subclassing needed.

## Consumers

- **REST API** -- uses `negotiate_format()` and `format_response()` to serve entries in the client's preferred format.
- **CLI export commands** -- use the `FormatRegistry` to serialize entries for file output.
- **CLI import commands** -- use the `ImporterRegistry` to parse bulk input files.

## Related

- [[rest-api]] -- content negotiation integration
- [[entry-model]] -- entries are the primary data serialized/deserialized
- [[kb-service]] -- import pipelines feed into `KBService.create_entry()`
