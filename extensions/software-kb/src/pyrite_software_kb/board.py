"""Board configuration for kanban-style views."""

from pathlib import Path

DEFAULT_BOARD_CONFIG = {
    "lanes": [
        {"name": "Backlog", "statuses": ["proposed", "planned"]},
        {"name": "Ready", "statuses": ["accepted"]},
        {"name": "In Progress", "statuses": ["in_progress"], "wip_limit": 5},
        {"name": "Review", "statuses": ["review"], "wip_limit": 3},
        {"name": "Done", "statuses": ["done", "completed"]},
    ],
    "wip_policy": "warn",
}


def load_board_config(kb_path: Path) -> dict:
    """Load board config from board.yaml in KB root, falling back to defaults."""
    board_file = kb_path / "board.yaml"
    if board_file.exists():
        from pyrite.utils.yaml import load_yaml_file

        return load_yaml_file(board_file)
    return DEFAULT_BOARD_CONFIG.copy()
