- **Unreleased changes are now recorded as one file per change under
  `changelog.d/`, not as a bullet in `CHANGELOG.md` (#243).** Every
  `[Unreleased]` bullet was appended at the same spot, so any two pull requests
  in flight conflicted there by construction — five times in one session, three
  of them on first-time contributors' branches, every one resolved by "keep
  both, either order". A fragment is named `<slug>.<section>.md`, so no two
  branches write the same path and neither a rebase nor a merge has anything to
  resolve; `scripts/release.py` assembles the fragments under the version
  heading at release time and deletes them, and refuses an unknown section
  rather than dropping the entry. See `changelog.d/README.md`.
