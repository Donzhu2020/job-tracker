#!/usr/bin/env python3
"""
Job Search CLI - Search for jobs and output JSON.

Supports two providers:
  - jobspy  (default): LinkedIn guest API — no API key required, free
  - jsearch:           JSearch RapidAPI  — 200 free requests/month, Google Jobs aggregator

Usage:
    python run_search.py -o /tmp/jobs.json
    python run_search.py --provider jsearch -o /tmp/jobs.json
    python run_search.py --keywords "ML engineer" --location "Boston"

Provider can also be set in config.json:
    { "search_provider": "jobspy", ... }
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from common.config import load_config


def main():
    parser = argparse.ArgumentParser(description="Search for jobs")
    parser.add_argument("--config", default="~/.config/job-hunter/config.json",
                        help="Path to config file")
    parser.add_argument("--provider", choices=["jobspy", "jsearch"],
                        help="Search provider (overrides config search_provider)")
    parser.add_argument("--keywords", nargs="+", help="Override search keywords")
    parser.add_argument("--location", help="Override job location")
    parser.add_argument("--output", "-o", help="Output JSON file (default: stdout)")
    parser.add_argument("--include-seen", action="store_true",
                        help="Include previously seen jobs")

    args = parser.parse_args()
    config = load_config(args.config)

    provider = args.provider or config.get("search_provider", "jobspy")
    print(f"Using search provider: {provider}")

    common_kwargs = dict(
        config=config,
        keywords=args.keywords,
        location=args.location,
        skip_seen=not args.include_seen,
    )

    if provider == "jsearch":
        from jsearch_scraper import scrape_jobs as jsearch_scrape
        jobs = jsearch_scrape(**common_kwargs)
    else:
        from jobspy_scraper import scrape_jobs as jobspy_scrape
        jobs = jobspy_scrape(**common_kwargs)

    output = json.dumps(jobs, indent=2, default=str)

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w") as f:
            f.write(output)
        print(f"Saved {len(jobs)} jobs to {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
