"""One-time upgrade step for demos seeded before /site became public-KB-only.

/site now renders only KBs with `default_role: read`. seed.sh sets that on
new demos, but it runs once, so an already-seeded demo's config.yaml has KBs
with no `default_role`, and its public site goes empty after the upgrade.

    python public-kbs.py /data/config.yaml           # list them, change nothing
    python public-kbs.py /data/config.yaml --apply   # mark them default_role: read

--apply touches only KBs with no `default_role`; an explicit `none` or
`write` is left alone. Restart the server and re-render the site afterwards
(POST /api/site/render).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    from pyrite.utils.yaml import dump_yaml_file, load_yaml_file
except ImportError:  # run from the container, where the package lives in /app
    sys.path.insert(0, "/app")
    from pyrite.utils.yaml import dump_yaml_file, load_yaml_file


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("config", type=Path)
    parser.add_argument("--apply", action="store_true", help="set default_role: read")
    args = parser.parse_args()

    data = load_yaml_file(args.config) or {}
    unset = [kb for kb in data.get("knowledge_bases") or [] if kb.get("default_role") is None]
    if not unset:
        print("All KBs have a default_role; nothing to do for /site.")
        return 0

    names = ", ".join(kb.get("name", "?") for kb in unset)
    if not args.apply:
        print(
            f"These KBs have no default_role and will not appear on /site: {names}\n"
            f"To publish them (one-time step), run:\n"
            f"  python {Path(__file__).name} {args.config} --apply\n"
            f"then restart the server and re-render the site (POST /api/site/render)."
        )
        return 0

    for kb in unset:
        kb["default_role"] = "read"
    dump_yaml_file(data, args.config)
    print(f"Set default_role: read on: {names}. Restart and re-render the site.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
