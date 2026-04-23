# Transparency Cascade — example branding folder

Example branding configuration for deploying a Pyrite instance under
the Transparency Cascade Press identity (e.g.,
`investigate.transparencycascade.org`).

## Usage

Point a Pyrite deployment at this folder:

```bash
export PYRITE_BRANDING_DIR=/path/to/deploy/branding-examples/transparency-cascade
```

See the top-level `pyrite-white-labeling` backlog item and
`docs/deployment/white-labeling.md` (once the feature ships) for the
full branding-folder contract.

## Contents

| File | Source | Purpose |
|---|---|---|
| `branding.yaml` | hand-written | Brand config |
| `logo.png` | `https://transparencycascade.org/img/logo-black.png` | Square icon, 512×512, black-on-transparent |
| `wordmark.png` | `https://transparencycascade.org/img/wordmark-black.png` | Horizontal wordmark, 1344×256, black-on-transparent |

Assets are black-on-transparent. `branding.yaml` sets
`invert_on_dark: true`, so the frontend applies CSS `filter: invert(1)`
for dark-theme rendering. One asset per surface, no light/dark
duplication.

## TODOs (derive once, then commit)

The source site does not publish a favicon or apple-touch-icon. Derive
both from `logo.png`:

```bash
# Requires imagemagick or sips. Example with sips (macOS):
sips -s format png -z 180 180 logo.png --out apple-touch-icon.png
sips -s format png -z 32  32  logo.png --out favicon-32.png
# And a multi-resolution .ico via imagemagick:
magick convert logo.png -define icon:auto-resize=16,32,48 favicon.ico
```

After deriving, add `favicon`, `apple_touch_icon`, and `favicon_32`
keys to `branding.yaml` pointing at the new files.

An Open Graph social-share card (1200×630) is also not yet present. A
simple version can be generated from `wordmark.png` over the accent
color `#c93b3b`.

## Provenance

Assets downloaded from `https://transparencycascade.org/` on
2026-04-23. The site is Hugo-generated and serves these files from
`/img/logo-black.png` and `/img/wordmark-black.png`. Licensing:
first-party assets belonging to Transparency Cascade Press, LLC;
reused here under operator authority (the same owner runs both sites).
