- **`pyrite create -t <type>` no longer silently files a different type when the
  KB does not declare the one asked for (#197).** Core types were exempt from
  the CLI's write-side refusal, so `-t note` against a KB whose schema declares
  only `adr | backlog_item | component | standard` skipped the guard, and plugin
  type resolution then promoted it to its most-derived `note` subtype — an ADR
  with `adr_number: 0` under `kb/adrs/`, from a command that asked for a note.
  The refusal now covers every type the KB does not declare; `--allow-undeclared`
  still overrides it.
