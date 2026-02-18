#!/usr/bin/env python3
"""
Tavily Job Scraper - Searches jobs via Tavily Search API.

Usage:
    python tavily_scraper.py --config ~/.config/job-hunter/config.json
    python tavily_scraper.py --keywords "software engineer" --location "Boston"
"""

import argparse
import asyncio
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx

# Add parent directory to path for common imports
sys.path.insert(0, str(Path(__file__).parent))

from common.config import load_config
from common.dedup import deduplicate_jobs, filter_seen_jobs, generate_job_id

TAVILY_SEARCH_URL = "https://api.tavily.com/search"

DEFAULT_JOB_DOMAINS = [
    "linkedin.com/jobs",
    "indeed.com",
    "glassdoor.com",
    "builtin.com",
    "wellfound.com",
]


async def search_jobs(
    api_key: str,
    query: str,
    max_results: int = 20,
    time_range: str = "week",
    domains: list[str] | None = None,
) -> list[dict]:
    """Search for jobs using Tavily API."""
    payload = {
        "api_key": api_key,
        "query": query,
        "topic": "general",
        "search_depth": "basic",
        "time_range": time_range,
        "max_results": max_results,
        "include_domains": domains or DEFAULT_JOB_DOMAINS,
        "include_raw_content": "markdown",
    }

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(TAVILY_SEARCH_URL, json=payload)
        if resp.status_code != 200:
            print(f"Tavily API error: {resp.status_code} - {resp.text}", file=sys.stderr)
            return []
        return resp.json().get("results", [])


def extract_job_title(result: dict) -> str:
    """Extract job title from Tavily result title.

    Common formats:
    - "Job Title - Company | LinkedIn"
    - "Job Title - Company - Indeed"
    - "Job Title at Company - Glassdoor"
    """
    title = result.get("title", "")

    # Remove trailing site names
    for suffix in [" | LinkedIn", " - Indeed", " | Indeed.com", " - Glassdoor",
                   " | Glassdoor", " | Built In", " | Wellfound"]:
        if title.endswith(suffix):
            title = title[: -len(suffix)]

    # Split on " - " or " at " to get job title (first part)
    for sep in [" - ", " at "]:
        if sep in title:
            return title.split(sep)[0].strip()

    return title.strip()


def extract_company(result: dict) -> str:
    """Extract company name from Tavily result."""
    title = result.get("title", "")
    content = result.get("content", "")
    url = result.get("url", "")

    # --- LinkedIn URL: /jobs/view/job-title-at-company-name-JOBID ---
    if "linkedin.com/jobs/view/" in url:
        slug = url.rstrip("/").split("/")[-1]
        slug = re.sub(r"-\d+$", "", slug)          # remove trailing job ID
        if "-at-" in slug:
            company_slug = slug.split("-at-", 1)[1]
            return company_slug.replace("-", " ").title()

    # --- Strip site suffixes from title ---
    clean_title = title
    for suffix in [" | LinkedIn", " - Indeed", " | Indeed.com", " - Glassdoor",
                   " | Glassdoor", " | Built In", " | Wellfound"]:
        if clean_title.endswith(suffix):
            clean_title = clean_title[: -len(suffix)]

    # "Job Title - Company" or "Job Title at Company"
    for sep in [" - ", " at "]:
        if sep in clean_title:
            parts = clean_title.split(sep)
            if len(parts) >= 2:
                candidate = parts[-1].strip()
                # Reject if it looks like a location or junk
                if candidate and len(candidate) < 60 and not re.match(
                    r"^\d|^(remote|boston|new york|san francisco|chicago)", candidate.lower()
                ):
                    return candidate

    # --- Search raw_content (full page markdown) for "at CompanyName" pattern ---
    raw = result.get("raw_content") or ""
    full_text = content + "\n" + raw

    at_match = re.search(
        r"\bat\s+([A-Z][A-Za-z0-9&'\-,\. ]{2,50})(?:\s*[\|\n\(]|$)", full_text
    )
    if at_match:
        candidate = at_match.group(1).strip().rstrip(".,")
        if not re.search(
            r"least|years?|experience|remote|boston|least|all|our|the\b|a\b",
            candidate.lower()
        ):
            return candidate

    # --- Fallback: first capitalised proper-noun line in raw_content ---
    for line in (raw or content).split("\n")[:15]:
        line = line.strip()
        if (5 < len(line) < 60
                and re.match(r"^[A-Z]", line)
                and not re.search(
                    r"\$|http|jobs?|remote|apply|indeed|glassdoor|linkedin"
                    r"|\d{5}|boston|\bthe\b|\ba\b|additional|full job",
                    line.lower()
                )):
            return line

    return ""


def extract_location(result: dict) -> str:
    """Extract location from content or raw_content."""
    content = result.get("content", "") + " " + (result.get("raw_content") or "")

    # Common patterns
    patterns = [
        r"(?:location|where)\s*[:\-]\s*(.+?)(?:\n|\.|\|)",
        r"((?:Remote|Hybrid|On-site)\s*(?:in\s+)?[\w\s,]+(?:,\s*[A-Z]{2})?)",
        r"([\w\s]+,\s*[A-Z]{2}\s*\d{5})",  # City, ST 12345
        r"([\w\s]+,\s*[A-Z]{2})(?:\s|\.|\n|\|)",  # City, ST
    ]

    for pattern in patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            loc = match.group(1).strip()
            if len(loc) < 80:  # sanity check
                return loc

    return ""


def extract_salary(result: dict) -> str:
    """Extract salary info from content."""
    content = result.get("content", "") + " " + (result.get("raw_content") or "")

    patterns = [
        r"\$[\d,]+(?:k|\s*K)?\s*[-–]\s*\$[\d,]+(?:k|\s*K)?(?:\s*(?:per\s+)?(?:year|yr|annually|a\s+year))?",
        r"\$[\d,]+(?:k|\s*K)?(?:\s*(?:per\s+)?(?:year|yr|annually|a\s+year|hour|hr))",
    ]

    for pattern in patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            return match.group(0).strip()

    return ""


def detect_source(url: str) -> str:
    """Detect job source from URL."""
    domain_map = {
        "linkedin.com": "linkedin",
        "indeed.com": "indeed",
        "glassdoor.com": "glassdoor",
        "builtin.com": "builtin",
        "wellfound.com": "wellfound",
    }
    for domain, source in domain_map.items():
        if domain in url:
            return source
    return "other"


def is_individual_job_posting(result: dict) -> bool:
    """Return True only if the result is an individual job posting, not a search results page."""
    url = result.get("url", "").lower()
    raw_title = result.get("title", "")
    title_lower = raw_title.lower()

    # --- URL-based rejection (search/aggregator pages) ---
    reject_url_patterns = [
        r"indeed\.com/q-",                    # indeed search: /q-keyword-l-location-jobs.html
        r"indeed\.com/jobs\?",                # indeed search: /jobs?q=...
        r"indeed\.com/m/",                    # indeed mobile search
        r"glassdoor\.com/job/.*srch_",        # glassdoor search results
        r"glassdoor\.com/jobs/",              # glassdoor job listing index
        r"linkedin\.com/jobs/search/",        # linkedin search
        r"linkedin\.com/jobs/[a-z-]+jobs",    # linkedin aggregator
        r"wellfound\.com/jobs$",              # wellfound listing index
        r"builtin\.com/jobs",                 # builtin listing index
    ]
    for pattern in reject_url_patterns:
        if re.search(pattern, url):
            return False

    # --- Title-based rejection (search page titles) ---
    reject_title_patterns = [
        r"^\d+\s+\w",                          # "34 Data science jobs..."
        r"\bjobs? in\b.*(remote|boston|ma)",   # "Data Analyst jobs in Remote"
        r"\bjob openings? from\b",             # "job openings from Boston"
        r"\bjobs?,?\s+employment\b",           # "Remote Jobs, Employment"
        r"^flexible .+ jobs?$",               # "Flexible Biology Data Analyst Remote Jobs"
        r"^remote .+ jobs? in\b",             # "Remote data entry jobs in Boston"
        r"browse \d+",                         # "Browse 66 Remote..."
        r"search .+ jobs? in\b",              # "Search Data science jobs in..."
    ]
    for pattern in reject_title_patterns:
        if re.search(pattern, title_lower):
            return False

    return True


def normalize_tavily_result(result: dict) -> dict:
    """Normalize a Tavily search result to the common job format."""
    url = result.get("url", "")
    title = extract_job_title(result)
    company = extract_company(result)
    location = extract_location(result)

    job = {
        "title": title,
        "company": company,
        "location": location,
        "description": result.get("content", ""),
        "url": url,
        "posted_date": result.get("published_date", ""),
        "salary": extract_salary(result),
        "employment_type": "",
        "experience_level": "",
        "remote": "remote" in (title + " " + location + " " + result.get("content", "")).lower(),
        "source": detect_source(url),
        "scraped_at": datetime.now().isoformat(),
    }
    job["id"] = generate_job_id(job)
    return job


def _determine_time_range(config: dict) -> str:
    """Use configured time_range on first run; fall back to 'day' on all subsequent runs.

    'First run' = no dated Job Tracker files exist in the Obsidian vault yet.
    This lets the initial run cast a wide net (week) while daily runs only
    fetch genuinely new postings (day), avoiding duplicate results.
    """
    vault = config.get("obsidian_vault", "")
    if vault:
        vault_path = Path(vault).expanduser()
        if list(vault_path.glob("Job Tracker - *.md")):
            return "day"
    # First run: respect whatever time_range is set in config (default "week")
    return config.get("search", {}).get("time_range", "week")


async def scrape_jobs(
    config: dict,
    keywords: list[str] | None = None,
    location: str | None = None,
    skip_seen: bool = True,
) -> list[dict]:
    """Search jobs using Tavily for each keyword, aggregate and deduplicate."""
    api_key = config.get("tavily_api_key", "")
    if not api_key:
        print("Error: tavily_api_key not configured", file=sys.stderr)
        return []

    search_config = config.get("search", {})
    keywords_list = keywords or search_config.get("keywords", [])
    loc = location or search_config.get("location", "")
    time_range = _determine_time_range(config)
    print(f"Search time range: {time_range}")
    max_results = search_config.get("max_results_per_query", 20)
    domains = search_config.get("job_domains", DEFAULT_JOB_DOMAINS)

    if search_config.get("remote"):
        loc = f"{loc} remote".strip() if loc else "remote"

    all_jobs = []
    for kw in keywords_list:
        query = f"{kw} jobs {loc}".strip()
        print(f"Searching: {query}")
        results = await search_jobs(api_key, query, max_results, time_range, domains)
        postings = [r for r in results if is_individual_job_posting(r)]
        normalized = [normalize_tavily_result(r) for r in postings]
        all_jobs.extend(normalized)
        print(f"  Found {len(results)} results ({len(postings)} individual postings)")

    # Deduplicate
    all_jobs = deduplicate_jobs(all_jobs)

    # Filter previously seen jobs
    if skip_seen and config.get("obsidian_vault"):
        all_jobs = filter_seen_jobs(all_jobs, config["obsidian_vault"])

    # Sort by posted date (newest first)
    all_jobs.sort(key=lambda j: j.get("posted_date", ""), reverse=True)

    print(f"Total: {len(all_jobs)} new jobs after dedup")
    return all_jobs


async def main():
    parser = argparse.ArgumentParser(description="Search jobs via Tavily")
    parser.add_argument("--config", default="~/.config/job-hunter/config.json",
                        help="Path to config file")
    parser.add_argument("--keywords", nargs="+", help="Search keywords")
    parser.add_argument("--location", help="Job location")
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
        with open(args.output, "w") as f:
            f.write(output)
        print(f"Saved {len(jobs)} jobs to {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    asyncio.run(main())
