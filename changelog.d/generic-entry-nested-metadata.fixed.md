- **A `GenericEntry` no longer duplicates its undeclared frontmatter keys into
  a `metadata:` block on save.** `Entry._base_frontmatter` serialized the whole
  `self.metadata` mapping as a nested block while `GenericEntry.to_frontmatter`
  also promoted the same keys to top level, so a no-op load→save grew a
  `metadata:` block the source file never had. Only keys that came from an
  explicit `metadata:` block stay nested now; the rest are promoted once
  (#149). A `metadata:` value that is not a mapping (null, a string, a list, a
  number) is kept verbatim and written back on the next save, with a warning,
  instead of failing the load and saving the file back as a different entry
  type. Deliberate behaviour change: an entry *created* with `metadata={…}` now
  writes those keys top-level only, where `dev` also wrote a nested block --
  except a key the base frontmatter already emits (`title`, `id`, …), which
  stays nested under `metadata:` rather than being dropped.
