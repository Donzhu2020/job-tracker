#!/usr/bin/env python3
"""
Interactive setup script for Job Hunter skill configuration.

Creates the config file at ~/.config/job-hunter/config.json

Usage:
    python setup_config.py
    python setup_config.py --validate  # Just validate existing config
"""

import argparse
import json
import os
import sys
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "job-hunter"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_CONFIG = {
    "jsearch_api_key": "",
    "search_provider": "jobspy",
    "resume_path": "",
    "obsidian_vault": "",
    "user_name": "",
    "search": {
        "keywords": [],
        "location": "",
        "remote": True,
        "time_range": "week",
        "max_results_per_query": 20,
        "job_domains": ["linkedin.com", "indeed.com", "glassdoor.com", "builtin.com", "wellfound.com"]
    }
}


def prompt(message: str, default: str = "", required: bool = False, secret: bool = False) -> str:
    """Prompt user for input."""
    if default:
        message = f"{message} [{default}]: "
    else:
        message = f"{message}: "

    while True:
        if secret:
            import getpass
            value = getpass.getpass(message)
        else:
            value = input(message).strip()

        if not value:
            value = default

        if required and not value:
            print("This field is required.")
            continue

        return value


def prompt_list(message: str, default: list | None = None) -> list:
    """Prompt user for comma-separated list."""
    default = default or []
    default_str = ", ".join(default) if default else ""

    print(f"{message}")
    value = prompt("Enter comma-separated values", default=default_str)

    if not value:
        return default

    return [item.strip() for item in value.split(",") if item.strip()]


def validate_config(config: dict) -> list[str]:
    """Validate configuration and return list of errors."""
    errors = []

    provider = config.get("search_provider", "jobspy")
    if provider == "jsearch" and not config.get("jsearch_api_key"):
        errors.append("Missing JSearch API key (search_provider is 'jsearch')")
    # jobspy requires no API key

    if not config.get("resume_path"):
        errors.append("Missing resume path")
    elif not Path(config["resume_path"]).expanduser().exists():
        errors.append(f"Resume file not found: {config['resume_path']}")

    if not config.get("obsidian_vault"):
        errors.append("Missing Obsidian vault path")
    elif not Path(config["obsidian_vault"]).expanduser().exists():
        errors.append(f"Obsidian vault not found: {config['obsidian_vault']}")

    search = config.get("search", {})
    if not search.get("keywords"):
        errors.append("Need at least one search keyword configured")

    return errors


def load_existing_config() -> dict:
    """Load existing config or return default."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                return json.load(f)
        except json.JSONDecodeError:
            print("Warning: Existing config is invalid, starting fresh.")

    return DEFAULT_CONFIG.copy()


def save_config(config: dict) -> None:
    """Save config to file."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)

    # Set restrictive permissions (contains API keys)
    os.chmod(CONFIG_FILE, 0o600)

    print(f"\nConfiguration saved to: {CONFIG_FILE}")


def setup_interactive() -> dict:
    """Run interactive setup."""
    print("=" * 50)
    print("Job Hunter Configuration Setup")
    print("=" * 50)
    print()

    config = load_existing_config()

    # Search provider
    print("1. SEARCH PROVIDER")
    print("-" * 30)
    print("  jobspy  - No API key needed. Uses LinkedIn's public guest API. (Recommended)")
    print("  jsearch - RapidAPI. 200 free requests/month. Google Jobs aggregator.")
    config["search_provider"] = prompt(
        "Search provider (jobspy/jsearch)",
        default=config.get("search_provider", "jobspy")
    ).lower()
    print()

    if config["search_provider"] == "jsearch":
        print("1a. JSEARCH CONFIGURATION")
        print("-" * 30)
        print("Get your API key from: https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch")
        config["jsearch_api_key"] = prompt(
            "JSearch (RapidAPI) API key",
            default="***" if config.get("jsearch_api_key") else "",
            required=True,
            secret=True
        )
    else:
        print("1a. JOBSPY — no API key required.")
    print()

    # User Name
    print("2. USER INFO")
    print("-" * 30)
    config["user_name"] = prompt(
        "Your full name (for cover letters)",
        default=config.get("user_name", ""),
        required=True
    )
    print()

    # Resume Path
    print("3. RESUME CONFIGURATION")
    print("-" * 30)
    config["resume_path"] = prompt(
        "Path to your resume (PDF or text)",
        default=config.get("resume_path", ""),
        required=True
    )
    print()

    # Obsidian Vault
    print("4. OBSIDIAN CONFIGURATION")
    print("-" * 30)
    config["obsidian_vault"] = prompt(
        "Obsidian vault path for job tracking",
        default=config.get("obsidian_vault", "~/Documents/Obsidian Vault/job-hunter")
    )
    print()

    # Search Configuration
    print("5. JOB SEARCH CONFIGURATION")
    print("-" * 30)

    search_config = config.get("search", DEFAULT_CONFIG["search"].copy())

    search_config["keywords"] = prompt_list(
        "Job search keywords (e.g., 'machine learning engineer, data scientist')",
        default=search_config.get("keywords", [])
    )

    search_config["location"] = prompt(
        "Location (e.g., 'Boston, MA')",
        default=search_config.get("location", "")
    )

    remote_input = prompt(
        "Include remote jobs? (yes/no)",
        default="yes" if search_config.get("remote", True) else "no"
    )
    search_config["remote"] = remote_input.lower() in ("yes", "y", "true", "1")

    _provider = config.get("search_provider", "jobspy")
    if _provider == "jsearch":
        max_cap, cap_note = 10, "  ← 10/request; each keyword uses 1 request"
    else:
        max_cap, cap_note = 20, "  ← LinkedIn rate-limits at ~100 results/IP"
    max_results = prompt(
        f"Max results per query (1-{max_cap}){cap_note}",
        default=str(search_config.get("max_results_per_query", max_cap))
    )
    search_config["max_results_per_query"] = min(max_cap, int(max_results)) if max_results.isdigit() else max_cap

    search_config["time_range"] = prompt(
        "Time range for job postings (day/week/month)",
        default=search_config.get("time_range", "week")
    )

    config["search"] = search_config
    print()

    # Remove legacy fields if present
    for key in ["apify_api_key", "linkedin_search_url", "indeed_search_url", "email",
                "tavily_api_key", "exa_api_key"]:
        config.pop(key, None)

    return config


def main():
    parser = argparse.ArgumentParser(description="Setup Job Hunter configuration")
    parser.add_argument("--validate", action="store_true",
                        help="Only validate existing configuration")
    parser.add_argument("--show", action="store_true",
                        help="Show current configuration (masks secrets)")

    args = parser.parse_args()

    if args.validate:
        if not CONFIG_FILE.exists():
            print(f"No config file found at {CONFIG_FILE}")
            sys.exit(1)

        config = load_existing_config()
        errors = validate_config(config)

        if errors:
            print("Configuration errors:")
            for error in errors:
                print(f"  - {error}")
            sys.exit(1)
        else:
            print("Configuration is valid!")
            sys.exit(0)

    if args.show:
        if not CONFIG_FILE.exists():
            print(f"No config file found at {CONFIG_FILE}")
            sys.exit(1)

        config = load_existing_config()

        display_config = json.loads(json.dumps(config))
        if display_config.get("jsearch_api_key"):
            display_config["jsearch_api_key"] = display_config["jsearch_api_key"][:10] + "..."

        print(json.dumps(display_config, indent=2))
        sys.exit(0)

    try:
        config = setup_interactive()

        errors = validate_config(config)
        if errors:
            print("\nConfiguration warnings:")
            for error in errors:
                print(f"  - {error}")
            print("\nYou can fix these later by running setup again.")

        save = prompt("Save configuration? (yes/no)", default="yes")
        if save.lower() in ("yes", "y"):
            save_config(config)
            print("\nSetup complete! Run /job-hunt to start hunting.")
        else:
            print("\nConfiguration not saved.")

    except KeyboardInterrupt:
        print("\n\nSetup cancelled.")
        sys.exit(1)


if __name__ == "__main__":
    main()
