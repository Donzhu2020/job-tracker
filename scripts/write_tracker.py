#!/usr/bin/env python3
"""
Write the daily Job Tracker markdown file to the Obsidian vault.

Reads scored jobs JSON, filters by minimum score, and writes
"Job Tracker - YYYY-MM-DD.md". Idempotent: if today's tracker already
exists it is left untouched (use --force to overwrite).

Usage:
    python write_tracker.py -i /tmp/scored.json --config ~/.config/job-hunter/config.json
    python write_tracker.py -i /tmp/scored.json --vault ~/Vault/job-hunter --min-score 60
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from common.config import load_config

DEFAULT_MIN_SCORE = 70


def build_tracker(jobs: list[dict], min_score: int, day: str) -> tuple[str, int]:
    """Return (markdown content, number of jobs included)."""
    filtered = [j for j in jobs if j.get("match_score", 0) > min_score]

    lines = [
        f"# Job Tracker - {day}",
        "",
        f"**Jobs with score > {min_score}:** {len(filtered)} of {len(jobs)} found today",
        "",
        "| # | Score | Title | Company | Salary | Remote | Source | Link |",
        "|---|-------|-------|---------|--------|--------|--------|------|",
    ]
    for i, job in enumerate(filtered, 1):
        title = (job.get("title") or "N/A").replace("|", "-")[:50]
        company = (job.get("company") or "-").replace("|", "-")[:30]
        score = job.get("match_score", 0)
        salary = job.get("salary") or "-"
        remote = "Yes" if job.get("remote") else "No"
        source = (job.get("source") or "-").capitalize()
        url = job.get("url") or "#"
        lines.append(
            f"| {i} | {score} | {title} | {company} | {salary} | {remote} | {source} | [Apply]({url}) |"
        )
    return "\n".join(lines) + "\n", len(filtered)


def main():
    parser = argparse.ArgumentParser(description="Write Job Tracker markdown to Obsidian")
    parser.add_argument("--input", "-i", required=True, help="Scored jobs JSON file")
    parser.add_argument("--config", default="~/.config/job-hunter/config.json")
    parser.add_argument("--vault", help="Override Obsidian vault path")
    parser.add_argument("--min-score", type=int, help="Override minimum score (default from config, else 70)")
    parser.add_argument("--force", action="store_true", help="Overwrite existing tracker")

    args = parser.parse_args()

    vault = args.vault
    min_score = args.min_score
    if not vault or min_score is None:
        config = load_config(args.config)
        vault = vault or config.get("obsidian_vault", "")
        if min_score is None:
            min_score = config.get("min_score", DEFAULT_MIN_SCORE)

    if not vault:
        print("Error: no Obsidian vault configured (obsidian_vault in config or --vault)",
              file=sys.stderr)
        sys.exit(1)

    vault_path = Path(vault).expanduser()
    vault_path.mkdir(parents=True, exist_ok=True)

    today = date.today().isoformat()
    tracker_path = vault_path / f"Job Tracker - {today}.md"

    if tracker_path.exists() and not args.force:
        print(f"Tracker already exists for today, skipping: {tracker_path}")
        return

    with open(Path(args.input).expanduser()) as f:
        jobs = json.load(f)

    content, count = build_tracker(jobs, min_score, today)
    tracker_path.write_text(content)
    print(f"Saved {count} jobs (score > {min_score}) to {tracker_path}")


if __name__ == "__main__":
    main()
