- Web: the New-entry form and the Web Clipper now offer only a KB's declared
  types when it declares any, requiring an explicit choice (auto-selected
  only when the KB declares exactly one) rather than an arbitrary default,
  with an explicit "use a type this KB does not declare" control as the only
  way to reach the rest; the web client no longer sends
  `allow_undeclared: true` unconditionally on every create, clip or import.
  `GET /api/entries/type-schemas` reports the KB's declared types as an
  additive `declared` field. (#392)
