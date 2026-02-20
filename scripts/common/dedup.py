"""Job deduplication logic."""

import hashlib
import re
from pathlib import Path


def generate_job_id(job: dict) -> str:
    """Generate a unique ID for a job based on URL (primary) or title+company+location."""
    url = job.get("url", "").strip()
    if url:
        return hashlib.md5(url.encode()).hexdigest()[:12]
    key = f"{job.get('title', '')}-{job.get('company', '')}-{job.get('location', '')}"
    return hashlib.md5(key.encode()).hexdigest()[:12]


def _normalize_title(title: str) -> str:
    """Lowercase, strip punctuation for fuzzy title matching."""
    return re.sub(r"[^a-z0-9 ]", "", title.lower()).strip()


def deduplicate_jobs(jobs: list[dict]) -> list[dict]:
    """Remove duplicate jobs.

    Pass 1: deduplicate by URL (exact).
    Pass 2: deduplicate by normalized title, keeping the best source
            (linkedin > indeed > glassdoor > other).
    """
    SOURCE_RANK = {"linkedin": 0, "indeed": 1, "glassdoor": 2, "builtin": 3, "wellfound": 4}

    # Pass 1: URL dedup
    seen_urls: set[str] = set()
    url_unique: list[dict] = []
    for job in jobs:
        url = job.get("url", "").strip()
        if url not in seen_urls:
            seen_urls.add(url)
            url_unique.append(job)

    # Pass 2: title dedup — keep best-source version per unique title
    title_map: dict[str, dict] = {}
    for job in url_unique:
        key = _normalize_title(job.get("title", ""))
        if not key:
            continue
        if key not in title_map:
            title_map[key] = job
        else:
            existing_rank = SOURCE_RANK.get(title_map[key].get("source", ""), 99)
            new_rank = SOURCE_RANK.get(job.get("source", ""), 99)
            if new_rank < existing_rank:
                title_map[key] = job

    return list(title_map.values())


def load_seen_jobs(obsidian_path: str) -> set[str]:
    """Load previously seen job IDs from all Obsidian tracker files."""
    vault = Path(obsidian_path).expanduser()
    if not vault.exists():
        return set()

    tracker_files = list(vault.glob("Job Tracker*.md"))
    if not tracker_files:
        return set()

    seen = set()
    for tracker_path in tracker_files:
        with open(tracker_path) as f:
            content = f.read()
            for line in content.split("\n"):
                if "|" not in line or line.startswith("|--"):
                    continue
                parts = [p.strip() for p in line.split("|")]
                for part in parts:
                    # New format: extract URL from [Apply](url) and hash it
                    for url in re.findall(r'\[(?:Apply|Link)\]\(([^)]+)\)', part):
                        seen.add(hashlib.md5(url.encode()).hexdigest()[:12])
    return seen


def filter_seen_jobs(jobs: list[dict], obsidian_path: str) -> list[dict]:
    """Filter out jobs that have already been seen."""
    seen_ids = load_seen_jobs(obsidian_path)
    original_count = len(jobs)
    filtered = [j for j in jobs if j.get("id") not in seen_ids]
    print(f"Filtered {original_count - len(filtered)} previously seen jobs")
    return filtered
