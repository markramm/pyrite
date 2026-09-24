"""Generate Pyrite's logo SVGs from exact isometric geometry.

    python docs/assets/logo/build_logo.py

The mark is a pyrite crystal read as a knowledge graph: an isometric cube
(the crystal habit of pyrite) inside a hexagonal frame, with nodes on
alternating frame corners and on both side faces, joined by edges that run
along the crystal. Every variant is drawn from the same geometry, so a change
here changes them all. Colours are the web app's gold tokens (web/src/app.css).

Outputs (next to this file, plus the web app's copies):
  pyrite-mark.svg          full mark, gold on transparent -- for dark backgrounds
  pyrite-mark-light.svg    full mark, dark gold on transparent -- for light backgrounds
  pyrite-icon.svg          app icon / avatar: full mark on a dark rounded square
  pyrite-favicon.svg       16-32 px: the cube alone, heavy strokes, on a dark square
  web/static/favicon.svg   = pyrite-favicon.svg
  web/static/pyrite-mark.svg, pyrite-mark-light.svg = the sidebar mark (dark / light theme)
"""

from __future__ import annotations

import math
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]

GOLD = "#D4A843"  # --color-gold-400
GOLD_LIGHT_BG = "#8F6B14"  # darker gold that keeps contrast on white
DARK = "#18181b"  # zinc-900, the app's dark surface


def hexagon(cx: float, cy: float, r: float) -> list[tuple[float, float]]:
    """Pointy-top hexagon: V0 top, then clockwise (V1 upper-right ... V5 upper-left)."""
    return [
        (cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a)))
        for a in (-90, -30, 30, 90, 150, 210)
    ]


def fmt(p: tuple[float, float]) -> str:
    return f"{p[0]:.2f},{p[1]:.2f}"


def line(a, b) -> str:
    return f'<line x1="{a[0]:.2f}" y1="{a[1]:.2f}" x2="{b[0]:.2f}" y2="{b[1]:.2f}"/>'


def poly(points) -> str:
    return "M" + " L".join(fmt(p) for p in points) + " Z"


def mid(*pts):
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))


def cube(cx, cy, r):
    """The six outline vertices and the centre of an isometric cube seen from above.

    Top face V0-V1-C-V5; left face V5-C-V3-V4; right face C-V1-V2-V3.
    """
    return hexagon(cx, cy, r), (cx, cy)


def full_mark(color: str, size: float = 256, stroke: float = 8.0, pad: float = 0.1) -> str:
    """Cube in a hexagonal frame, struts at every corner, five nodes."""
    c = size / 2
    outer_r = size * (0.5 - pad)
    inner_r = outer_r * 0.74
    outer = hexagon(c, c, outer_r)
    v, centre = cube(c, c, inner_r)
    node_r = stroke * 1.25

    left_face = [v[5], centre, v[3], v[4]]
    right_face = [centre, v[1], v[2], v[3]]
    left_node = mid(*left_face)
    right_node = mid(*right_face)

    edges = [
        # the cube: outline and the internal Y
        *(line(v[i], v[(i + 1) % 6]) for i in range(6)),
        line(centre, v[1]),
        line(centre, v[5]),
        line(centre, v[3]),
        # frame struts, outer corner to cube corner
        *(line(outer[i], v[i]) for i in range(6)),
        # graph edges on the side faces, mirrored: each face node to its far
        # upper corner and to the front-bottom vertex, the shared hub
        line(left_node, v[5]),
        line(left_node, v[3]),
        line(right_node, v[1]),
        line(right_node, v[3]),
    ]
    nodes = [outer[0], outer[2], outer[4], left_node, right_node]

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size:g} {size:g}" role="img" aria-label="Pyrite">
  <path d="{poly(left_face)}" fill="{color}" fill-opacity="0.45"/>
  <g fill="none" stroke="{color}" stroke-width="{stroke:g}" stroke-linecap="round" stroke-linejoin="round">
    <path d="{poly(outer)}"/>
    {"".join(edges)}
  </g>
  <g fill="{color}">
    {"".join(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{node_r:.2f}"/>' for x, y in nodes)}
  </g>
</svg>
"""


def on_tile(inner_svg: str, size: float, radius: float, bg: str) -> str:
    """Wrap a mark on a rounded square tile of the given background."""
    body = inner_svg.split(">", 1)[1].rsplit("</svg>", 1)[0]
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size:g} {size:g}" role="img" aria-label="Pyrite">
  <rect width="{size:g}" height="{size:g}" rx="{radius:g}" fill="{bg}"/>{body}</svg>
"""


def favicon(color: str, bg: str, size: float = 32) -> str:
    """The cube alone, heavy strokes, three nodes -- legible at 16 px."""
    c = size / 2
    stroke = size * 0.085
    v, centre = cube(c, c + size * 0.01, size * 0.37)
    left_face = [v[5], centre, v[3], v[4]]
    edges = [
        *(line(v[i], v[(i + 1) % 6]) for i in range(6)),
        line(centre, v[1]),
        line(centre, v[5]),
        line(centre, v[3]),
    ]
    nodes = [v[0], v[2], v[4]]
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size:g} {size:g}" role="img" aria-label="Pyrite">
  <rect width="{size:g}" height="{size:g}" rx="{size * 0.19:g}" fill="{bg}"/>
  <path d="{poly(left_face)}" fill="{color}" fill-opacity="0.55"/>
  <g fill="none" stroke="{color}" stroke-width="{stroke:.2f}" stroke-linecap="round" stroke-linejoin="round">
    {"".join(edges)}
  </g>
  <g fill="{color}">
    {"".join(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{stroke * 1.15:.2f}"/>' for x, y in nodes)}
  </g>
</svg>
"""


def main() -> None:
    outputs = {
        "pyrite-mark.svg": full_mark(GOLD),
        "pyrite-mark-light.svg": full_mark(GOLD_LIGHT_BG),
        "pyrite-icon.svg": on_tile(full_mark(GOLD, stroke=11, pad=0.11), 256, 48, DARK),
        "pyrite-favicon.svg": favicon(GOLD, DARK),
    }
    for name, svg in outputs.items():
        (HERE / name).write_text(svg, encoding="utf-8")
    static = REPO / "web" / "static"
    shutil.copyfile(HERE / "pyrite-favicon.svg", static / "favicon.svg")
    shutil.copyfile(HERE / "pyrite-mark.svg", static / "pyrite-mark.svg")
    shutil.copyfile(HERE / "pyrite-mark-light.svg", static / "pyrite-mark-light.svg")
    print("wrote", ", ".join(outputs), "+ web/static/{favicon,pyrite-mark,pyrite-mark-light}.svg")


if __name__ == "__main__":
    main()
