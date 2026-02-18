"""Unified configuration loading for Job Hunter."""

import json
import sys
from pathlib import Path

DEFAULT_CONFIG_PATH = "~/.config/job-hunter/config.json"


def load_config(config_path: str = DEFAULT_CONFIG_PATH) -> dict:
    """Load configuration from JSON file."""
    path = Path(config_path).expanduser()
    if not path.exists():
        print(f"Error: Config file not found at {path}", file=sys.stderr)
        print("Run setup_config.py to create configuration.", file=sys.stderr)
        sys.exit(1)

    with open(path) as f:
        return json.load(f)


def get_user_info(config: dict) -> dict:
    """Extract user info from config."""
    return {
        "name": config.get("user_name", ""),
        "resume_path": config.get("resume_path", ""),
    }
