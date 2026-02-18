#!/usr/bin/env python3
"""
Job Search CLI - Search for jobs via Tavily and output JSON.

Usage:
    python run_search.py -o /tmp/jobs.json
    python run_search.py --keywords "ML engineer" --location "Boston"
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from common.config import load_config
from tavily_scraper import scrape_jobs


async def main():
    parser = argparse.ArgumentParser(description="Search for jobs via Tavily")
    parser.add_argument("--config", default="~/.config/job-hunter/config.json",
                        help="Path to config file")
    parser.add_argument("--keywords", nargs="+", help="Override search keywords")
    parser.add_argument("--location", help="Override job location")
    parser.add_argument("--output", "-o", help="Output JSON file (default: stdout)")
    parser.add_argument("--include-seen", action="store_true",
                        help="Include previously seen jobs")

    args = parser.parse_args()
    config = load_config(args.config)

    jobs = await scrape_jobs(
        config,
        keywords=args.keywords,
        location=args.location,
        skip_seen=not args.include_seen,
    )

    output = json.dumps(jobs, indent=2, default=str)

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w") as f:
            f.write(output)
        print(f"Saved {len(jobs)} jobs to {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    asyncio.run(main())
