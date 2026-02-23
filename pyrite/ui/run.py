#!/usr/bin/env python3
"""
Run the pyrite web UI.

Usage:
    python -m pyrite.ui.run
    crk-ui  # if installed via pip
"""

import sys
from pathlib import Path


def main():
    """Launch the Streamlit app."""
    try:
        from streamlit.web import cli as stcli
    except ImportError:
        print("Error: streamlit not installed. Run: pip install streamlit")
        sys.exit(1)

    app_path = Path(__file__).parent / "app.py"

    sys.argv = [
        "streamlit",
        "run",
        str(app_path),
        "--server.headless=true",
        "--browser.gatherUsageStats=false",
    ]

    sys.exit(stcli.main())


if __name__ == "__main__":
    main()
