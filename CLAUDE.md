# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A Claude skill (`/job-hunt`) that automates job searching: scrapes job postings via JobSpy (LinkedIn guest API, free) and JSearch (RapidAPI/Google Jobs, 200 req/month free), scores them against a resume, saves a ranked Job Tracker to Obsidian, and generates cover letters for user-selected jobs.

When installed as a skill, scripts run from `~/.claude/skills/job-hunter/scripts/` with the venv at `~/.venv/job-hunter/`.

## Commands

### Setup (first time)
```bash
bash scripts/setup_venv.sh
~/.venv/job-hunter/bin/python3 scripts/setup_config.py
```

### Run individual pipeline steps
```bash
PYTHON=~/.venv/job-hunter/bin/python3
CONFIG=~/.config/job-hunter/config.json

# 1. Search (provider from config, or override with --provider jobspy|jsearch)
$PYTHON scripts/run_search.py --config $CONFIG -o /tmp/jobs.json
$PYTHON scripts/run_search.py --provider jsearch --config $CONFIG -o /tmp/jobs.json

# 2. Score
$PYTHON scripts/score_jobs.py -i /tmp/jobs.json -o /tmp/scored.json --config $CONFIG

# 3. Write tracker to Obsidian (idempotent; --force to overwrite)
$PYTHON scripts/write_tracker.py -i /tmp/scored.json --config $CONFIG

# 4. Cover letters (after user selects from tracker)
$PYTHON scripts/generate_cover_letters.py --jobs /tmp/scored.json --indices "1,3"
```

### Run full automated pipeline
```bash
bash scripts/daily_job_hunt.sh
```

### Dependencies
`requirements.txt` lists `httpx`, `python-dateutil`, and `python-jobspy`. Optional: `python-docx` (`.docx` resume), `PyPDF2` (`.pdf` resume).

## Architecture

### Data Flow
```
LinkedIn guest API  → jobspy_scraper.py ─┐
Google Jobs/RapidAPI→ jsearch_scraper.py─┴→ run_search.py → [raw jobs JSON]
                                                   ↓
                              score_jobs.py (common/job_scoring.py)
                                       ↓
                              [scored jobs JSON, sorted by match_score desc]
                                       ↓
                   write_tracker.py writes → Obsidian: Job Tracker - YYYY-MM-DD.md
                                       ↓  (user reviews and picks numbers)
                              generate_cover_letters.py
                                       ↓
                              Obsidian: Cover Letters/YYYY-MM-DD/Company - Title.md
```

### Module Relationships
- `scripts/common/` — shared library imported by all scripts via `sys.path.insert`
  - `config.py` — loads `~/.config/job-hunter/config.json`
  - `job_scoring.py` — extracts skills from resume, scores/ranks jobs (0–100)
  - `dedup.py` — URL-based dedup (pass 1), normalized (title, company) dedup (pass 2), tracks seen jobs across all Obsidian tracker files
  - `date_utils.py` — date helpers
- `jobspy_scraper.py` — Uses `python-jobspy` to hit LinkedIn's undocumented public guest API (`/jobs-guest/...`); no API key needed; also supports Indeed/Glassdoor/ZipRecruiter; rate-limited at ~100 results/IP by LinkedIn. Each site is scraped **individually** (per-site try/except + one retry after 10s) so one failing board can't discard the others' results; supports `linkedin_fetch_description`, `request_delay`, `proxies`, `user_agent` config knobs
- `jsearch_scraper.py` — Calls JSearch on RapidAPI (`jsearch.p.rapidapi.com`), which aggregates Google Jobs (LinkedIn, Indeed, Dice, and 100s of company career pages); 200 free requests/month; returns full descriptions; auto-paginates for >10 results
- `run_search.py` — provider-switching CLI: reads `search_provider` from config (or `--provider` flag), dispatches to jobspy/jsearch scraper; output schema is identical regardless of provider
- `score_jobs.py` — CLI wrapper around `common.job_scoring.score_jobs()`
- `write_tracker.py` — writes the ranked Job Tracker markdown to the Obsidian vault (idempotent; `min_score` from config, default 70; `--force` to overwrite)
- `generate_cover_letters.py` — produces Markdown cover letter templates with job metadata

### Job Schema
Each job dict has: `title`, `company`, `location`, `description`, `url`, `posted_date`, `salary`, `employment_type`, `experience_level`, `remote` (bool), `source`, `scraped_at`, `id` (MD5 of URL), and after scoring: `match_score` (0–100), `match_reason`.

### Scoring Logic (`common/job_scoring.py`)
- Extracts skills present in resume from a curated master list
- +5 per skill keyword match in job text
- Bonus rules (15/10/8/5 pts) for role alignment, healthcare domain, EHR tools, remote
- Falls back to hardcoded `_FALLBACK_SKILLS` if resume can't be read

### Deduplication Strategy (`common/dedup.py`)
- Pass 1: exact URL dedup (empty URLs are never treated as duplicates of each other)
- Pass 2: normalized (title, company) dedup, keeping best source (linkedin > indeed > glassdoor > zip_recruiter > ...). Title alone is deliberately NOT the key — different companies post identical titles
- `filter_seen_jobs()` reads all `Job Tracker*.md` files in the vault and extracts URL hashes to exclude already-seen postings

### Key Design Decisions
- **`time_range` always stays `"week"`**: switching to `"day"` returns aggregator pages instead of individual postings; dedup handles repeat suppression
- **Tracker is never overwritten**: if `Job Tracker - YYYY-MM-DD.md` already exists, the script skips writing (idempotent runs)
- **Cover letters are never auto-generated**: the skill explicitly stops after writing the tracker and waits for the user to select job numbers

## Configuration
Config file: `~/.config/job-hunter/config.json`

Key fields: `search_provider` (`"jobspy"` default, or `"jsearch"`), `jsearch_api_key` (jobspy needs no key), `resume_path` (PDF/DOCX/TXT), `obsidian_vault` (path), `user_name`, `min_score` (tracker threshold, default 70), `search.keywords[]`, `search.location`, `search.remote` (bool), `search.time_range`, `search.max_results_per_query` (max 10 for JSearch, max 20 for JobSpy), `search.job_domains[]` (JobSpy maps these to `linkedin`, `indeed`, `glassdoor`, `zip_recruiter`; ignored by JSearch; glassdoor excluded from defaults due to upstream 400s), `search.linkedin_fetch_description` (default true; set false to avoid LinkedIn 429s), `search.request_delay` (seconds between JobSpy calls, default 3), `search.proxies[]`, `search.user_agent`, `search.country_indeed` (default "USA").
