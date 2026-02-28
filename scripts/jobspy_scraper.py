#!/usr/bin/env python3
"""
JobSpy Job Scraper - Searches jobs via LinkedIn's public guest API (no auth required).

Uses the python-jobspy library which hits LinkedIn's undocumented but public
REST endpoint: linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search
No API key or LinkedIn account needed.

Also supports Indeed, Glassdoor, and ZipRecruiter in the same call.

Limitations:
- LinkedIn rate-limits at ~100 results per IP (page 10). Use proxies for volume.
- linkedin_fetch_description=True gets full descriptions but hits rate limits faster.
- ToS: LinkedIn prohibits scraping. This hits a public endpoint; use responsibly.

Usage:
    python jobspy_scraper.py --config ~/.config/job-hunter/config.json
    python jobspy_scraper.py --keywords "data scientist" --location "Boston"
"""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from common.config import load_config
from common.dedup import deduplicate_jobs, filter_seen_jobs, generate_job_id

# Map config job_domains to JobSpy site names
DOMAIN_TO_SITE = {
    "linkedin.com": "linkedin",
    "indeed.com": "indeed",
    "glassdoor.com": "glassdoor",
    "zip_recruiter.com": "zip_recruiter",
    "ziprecruiter.com": "zip_recruiter",
}

DEFAULT_SITES = ["linkedin", "indeed", "glassdoor"]

TIME_RANGE_TO_HOURS = {
    "day": 24,
    "week": 168,
    "month": 720,
    "year": 8760,
}


def _jobspy_import():
    try:
        from jobspy import scrape_jobs
        return scrape_jobs
    except ImportError:
        print("Error: python-jobspy is not installed. Run: pip install python-jobspy",
              file=sys.stderr)
        sys.exit(1)


def _domains_to_sites(domains: list[str]) -> list[str]:
    """Convert config job_domains list to JobSpy site name list.

    Handles both exact keys ('linkedin.com') and path-prefixed variants
    ('linkedin.com/jobs') that users may have in their config.
    """
    sites = []
    for d in domains:
        # Try exact match first, then prefix match
        site = DOMAIN_TO_SITE.get(d)
        if not site:
            for key, val in DOMAIN_TO_SITE.items():
                if d.startswith(key):
                    site = val
                    break
        if site and site not in sites:
            sites.append(site)
    return sites or DEFAULT_SITES


def _format_salary(row) -> str:
    """Build a salary string from JobSpy DataFrame row fields."""
    try:
        min_amt = row.get("min_amount")
        max_amt = row.get("max_amount")
        interval = row.get("interval") or ""
        currency = row.get("currency") or "USD"

        if min_amt and max_amt:
            return f"${int(min_amt):,}–${int(max_amt):,} {interval}".strip()
        elif min_amt:
            return f"${int(min_amt):,}+ {interval}".strip()
        elif max_amt:
            return f"up to ${int(max_amt):,} {interval}".strip()
    except Exception:
        pass
    return ""


def _str(val) -> str:
    """Convert a value to string, treating NaN/None/float-NaN as empty string."""
    import math
    if val is None:
        return ""
    if isinstance(val, float) and math.isnan(val):
        return ""
    return str(val)


def normalize_jobspy_row(row: dict) -> dict:
    """Normalize a JobSpy DataFrame row (as dict) to the common job dict format."""
    url = _str(row.get("job_url") or row.get("job_url_direct"))
    title = _str(row.get("title"))
    company = _str(row.get("company"))
    location = _str(row.get("location"))
    description = _str(row.get("description"))
    site = _str(row.get("site"))
    posted_date = row.get("date_posted")

    # Normalize posted_date to ISO string
    if posted_date and hasattr(posted_date, "isoformat"):
        posted_date = posted_date.isoformat()
    elif posted_date:
        posted_date = str(posted_date)
    else:
        posted_date = ""

    is_remote_flag = row.get("is_remote")
    remote = bool(is_remote_flag) or "remote" in (title + " " + location).lower()

    job = {
        "title": title,
        "company": company,
        "location": location,
        "description": description,
        "url": url,
        "posted_date": posted_date,
        "salary": _format_salary(row),
        "employment_type": _str(row.get("job_type")),
        "experience_level": "",
        "remote": remote,
        "source": site,
        "scraped_at": datetime.now().isoformat(),
    }
    job["id"] = generate_job_id(job)
    return job


def scrape_jobs(
    config: dict,
    keywords: list[str] | None = None,
    location: str | None = None,
    skip_seen: bool = True,
) -> list[dict]:
    """Search jobs using JobSpy for each keyword, aggregate and deduplicate."""
    scrape_jobs_fn = _jobspy_import()

    search_config = config.get("search", {})
    keywords_list = keywords or search_config.get("keywords", [])
    loc = location or search_config.get("location", "")
    time_range = search_config.get("time_range", "week")
    hours_old = TIME_RANGE_TO_HOURS.get(time_range, 168)
    results_wanted = search_config.get("max_results_per_query", 20)
    domains = search_config.get("job_domains", [])
    sites = _domains_to_sites(domains)

    if search_config.get("remote") and loc:
        loc = f"{loc}"  # JobSpy handles remote via is_remote filter; keep loc clean

    print(f"Sites: {sites} | Time range: {time_range} ({hours_old}h) | Results/keyword: {results_wanted}")

    all_jobs = []
    for kw in keywords_list:
        print(f"Searching: {kw} | {loc}")
        try:
            df = scrape_jobs_fn(
                site_name=sites,
                search_term=kw,
                location=loc,
                results_wanted=results_wanted,
                hours_old=hours_old,
                linkedin_fetch_description=True,
                country_indeed="USA",
                verbose=0,
            )
            rows = df.to_dict(orient="records") if df is not None and len(df) > 0 else []
        except Exception as e:
            print(f"  JobSpy error: {e}", file=sys.stderr)
            rows = []

        # Filter to remote if configured
        if search_config.get("remote"):
            rows = [r for r in rows if r.get("is_remote") or
                    "remote" in str(r.get("location", "")).lower()]

        normalized = [normalize_jobspy_row(r) for r in rows]
        all_jobs.extend(normalized)
        print(f"  Found {len(normalized)} postings")

    # Deduplicate across keywords
    all_jobs = deduplicate_jobs(all_jobs)

    # Filter previously seen jobs
    if skip_seen and config.get("obsidian_vault"):
        all_jobs = filter_seen_jobs(all_jobs, config["obsidian_vault"])

    # Sort by posted date (newest first)
    all_jobs.sort(key=lambda j: j.get("posted_date", ""), reverse=True)

    print(f"Total: {len(all_jobs)} new jobs after dedup")
    return all_jobs


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Search jobs via JobSpy (no API key required)")
    parser.add_argument("--config", default="~/.config/job-hunter/config.json")
    parser.add_argument("--keywords", nargs="+")
    parser.add_argument("--location")
    parser.add_argument("--output", "-o")
    parser.add_argument("--include-seen", action="store_true")

    args = parser.parse_args()
    config = load_config(args.config)

    jobs = scrape_jobs(
        config,
        keywords=args.keywords,
        location=args.location,
        skip_seen=not args.include_seen,
    )

    output = json.dumps(jobs, indent=2, default=str)
    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"Saved {len(jobs)} jobs to {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
