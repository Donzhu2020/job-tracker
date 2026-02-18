# Tavily Setup Guide

This guide explains how to set up Tavily Search API for job scraping.

## Getting Your API Key

1. Go to [Tavily](https://app.tavily.com/home)
2. Sign up or log in
3. Navigate to **API Keys** in your dashboard
4. Copy your API key (format: `tvly-xxxxxxxxxxxx`)

## Pricing

- **Free tier:** 1,000 API calls/month — sufficient for daily job hunting
- **Paid plans:** available at [tavily.com/pricing](https://tavily.com/pricing) for heavier usage

## How the Scraper Works

`tavily_scraper.py` sends one search query per keyword to the Tavily API, targeting these job boards by default:

| Site | Domain |
|------|--------|
| LinkedIn Jobs | `linkedin.com/jobs` |
| Indeed | `indeed.com` |
| Glassdoor | `glassdoor.com` |
| Built In | `builtin.com` |
| Wellfound | `wellfound.com` |

Each query returns up to `max_results_per_query` results. The scraper filters out search-results pages and keeps only individual job postings.

## Configuration

Add your Tavily API key and search preferences to `~/.config/job-hunter/config.json`:

```json
{
  "tavily_api_key": "tvly-xxxxxxxxxxxx",
  "search": {
    "keywords": ["machine learning engineer", "data scientist"],
    "location": "Boston, MA",
    "remote": true,
    "time_range": "week",
    "max_results_per_query": 20,
    "job_domains": [
      "linkedin.com/jobs",
      "indeed.com",
      "glassdoor.com",
      "builtin.com",
      "wellfound.com"
    ]
  }
}
```

### Key Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `tavily_api_key` | Your Tavily API key | required |
| `search.keywords` | Job title keywords to search | required |
| `search.location` | Target location | `""` |
| `search.remote` | Append "remote" to location query | `false` |
| `search.time_range` | `"day"` or `"week"` — used on first run only; subsequent runs always use `"day"` | `"week"` |
| `search.max_results_per_query` | Max results per keyword search | `20` |
| `search.job_domains` | Job boards to search | see above |

## Running the Scraper

```bash
# Use config file (recommended)
python scripts/tavily_scraper.py --config ~/.config/job-hunter/config.json

# Override keywords and location on the fly
python scripts/tavily_scraper.py --keywords "data engineer" --location "Remote"

# Save results to a JSON file
python scripts/tavily_scraper.py --output jobs.json

# Include previously seen jobs (skips deduplication)
python scripts/tavily_scraper.py --include-seen
```

## Time Range Behaviour

- **First run:** uses the `time_range` value in config (default `"week"`) to cast a wide net
- **Subsequent runs:** always uses `"day"` to fetch only new postings since the previous run

This is detected automatically by checking whether any `Job Tracker - *.md` files exist in your Obsidian vault.

## Troubleshooting

### "Error: tavily_api_key not configured"
- Run `python scripts/setup_config.py` to set up your config file
- Or manually add `"tavily_api_key"` to `~/.config/job-hunter/config.json`

### "Tavily API error: 401"
- Your API key is invalid or expired — get a new one from [app.tavily.com](https://app.tavily.com/home)

### "Tavily API error: 429"
- You've hit the rate limit — wait a few minutes or upgrade your Tavily plan

### "Total: 0 new jobs after dedup"
- All results may have been seen before — run with `--include-seen` to verify results are returned
- Try broadening your keywords or switching `time_range` to `"week"` temporarily

## Data Format

Each job is returned in a normalized format:

```json
{
  "id": "abc123def456",
  "source": "linkedin",
  "title": "Senior Data Scientist",
  "company": "TechCorp",
  "location": "Boston, MA",
  "description": "Full job description...",
  "url": "https://linkedin.com/jobs/view/...",
  "posted_date": "2025-01-20T00:00:00",
  "salary": "$150,000 - $200,000",
  "employment_type": "",
  "experience_level": "",
  "remote": true,
  "scraped_at": "2025-01-27T10:30:00"
}
```
