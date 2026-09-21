- **Release notes credit contributors whose work landed inside someone else's
  pull request (#248).** The notes were built from the authors of *merged* PRs
  only, so a contributor whose PR was closed because another branch carried
  the same fix first was thanked nowhere — #237 fixed a documented-but-missing
  command fourteen minutes before #239 merged the identical line, and shipped
  in 0.24.2 uncredited. `scripts/release.py` now also reads `Co-authored-by:`
  trailers over the release's own commits, which is the form `CONTRIBUTING.md`
  already asks for and the only one that survives the merge queue's squash.
