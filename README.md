---
name: job-hunter
description: |
  Automated job hunting skill that searches jobs via JobSpy (LinkedIn guest API, free)
  and JSearch (RapidAPI/Google Jobs, 200 req/month free), matches them to your resume
  using scoring, generates personalized cover letters, and saves results to Obsidian.

  Triggers: /job-hunt, "find jobs", "job search", "hunt for jobs"
---

# Job Hunter Skill

Automates your job search: scrapes LinkedIn, Indeed, and 100+ job boards daily, scores every posting against your resume, and saves a ranked tracker to Obsidian. No LinkedIn account needed.

## Preview

<table>
  <tr>
    <td><img src="assets/xhs/01-cover.png" width="320"/></td>
    <td><img src="assets/xhs/02-features.png" width="320"/></td>
    <td><img src="assets/xhs/03-workflow.png" width="320"/></td>
  </tr>
  <tr>
    <td><img src="assets/xhs/04-setup.png" width="320"/></td>
    <td><img src="assets/xhs/05-output.png" width="320"/></td>
    <td><img src="assets/xhs/06-ending.png" width="320"/></td>
  </tr>
</table>

## How It Works

Two complementary providers run on a smart schedule:

| Provider | Source | Cost | Schedule |
|----------|--------|------|----------|
| **JobSpy** | LinkedIn guest API + Indeed | Free, no key | Every day |
| **JSearch** | Google Jobs aggregator (100+ boards) | 200 req/month free | Every 2 days |

On days both run, results are merged and deduplicated before scoring. On off-days, JobSpy runs alone. A single daily cron job handles everything automatically.

## Quick Start

### 1. Set up virtual environment

```bash
bash ~/.claude/skills/job-hunter/scripts/setup_venv.sh
```

### 2. Configure

```bash
~/.venv/job-hunter/bin/python3 ~/.claude/skills/job-hunter/scripts/setup_config.py
```

You'll be prompted for:
- **JSearch API key** — free at [rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch](https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch) (JobSpy needs no key)
- Resume path (PDF, DOCX, or TXT)
- Obsidian vault path
- Search keywords and location

### 3. Run

```
/job-hunt
```

Or manually:
```bash
bash ~/.claude/skills/job-hunter/scripts/daily_job_hunt.sh
```

## Full Workflow

### 1. Search — JobSpy (daily) + JSearch (every 2 days)

**JobSpy** hits LinkedIn's undocumented public guest API — no login, no API key, returns full job descriptions (~60 results/run).

**JSearch** queries Google Jobs via RapidAPI, aggregating postings from LinkedIn, Indeed, Dice, Remotive, and 100+ company career pages (~100 results/run).

The scheduler uses a state file (`~/.job-hunter-jsearch-last-run`) to decide whether JSearch runs. If both run, their outputs are merged and deduplicated:

```
JobSpy  ~60 jobs ─┐
                  ├─ deduplicate → ~130–160 unique jobs
JSearch ~100 jobs─┘
```

### 2. Score against resume

Each job is scored 0–100 based on skill keyword matching:
- +5 per skill match (Python, SQL, machine learning, etc.)
- Bonus: role alignment (+15), healthcare domain (+10), EHR tools (+8), remote (+5)
- Skills are extracted automatically from your resume (PDF/DOCX/TXT)

### 3. Save Job Tracker to Obsidian

Writes `Job Tracker - YYYY-MM-DD.md` with all jobs scoring **> 70**, sorted by score descending. Idempotent — skips if today's file already exists.

```markdown
| # | Score | Title | Company | Salary | Remote | Source | Link |
|---|-------|-------|---------|--------|--------|--------|------|
| 1 | 100   | Data Engineer II | Dana-Farber Cancer Institute | - | Yes | Indeed | [Apply](url) |
| 2 | 100   | Senior Health Data Informaticist | Veeva Systems | - | Yes | Linkedin | [Apply](url) |
```

### 4. Wait for User Selection — STOP HERE

After saving the tracker:

> "Saved X jobs to **Job Tracker - YYYY-MM-DD.md** in Obsidian. Review the file and tell me which numbers you'd like cover letters for (e.g. '1, 3')."

**Never auto-generate cover letters. Always wait for user to select.**

### 5. Generate Cover Letters

```bash
~/.venv/job-hunter/bin/python3 ~/.claude/skills/job-hunter/scripts/generate_cover_letters.py \
  --jobs /path/to/scored_jobs.json \
  --indices "1,3"
```

Saves to `Cover Letters/YYYY-MM-DD/Company - Title.md` in your Obsidian vault.

## Configuration Reference

Config file: `~/.config/job-hunter/config.json`

```json
{
  "jsearch_api_key": "your-rapidapi-key",
  "search_provider": "jobspy",
  "resume_path": "/path/to/resume.pdf",
  "obsidian_vault": "~/Documents/Obsidian Vault/job-hunter",
  "user_name": "Your Name",
  "search": {
    "keywords": ["data analyst", "healthcare data analyst", "research analyst"],
    "location": "Boston, MA",
    "remote": true,
    "time_range": "week",
    "max_results_per_query": 20,
    "job_domains": ["linkedin.com", "indeed.com", "glassdoor.com"]
  }
}
```

### Key Fields

| Field | Description |
|-------|-------------|
| `jsearch_api_key` | RapidAPI key for JSearch (free tier: 200 req/month) |
| `search_provider` | `"jobspy"` (default) or `"jsearch"` for manual override |
| `search.max_results_per_query` | Max 20 for JobSpy, max 10 for JSearch |
| `search.job_domains` | Used by JobSpy; maps to `linkedin`, `indeed`, `glassdoor`, `zip_recruiter` |

## Scheduling

Set up a daily cron to run the full pipeline automatically:

```bash
# Run job hunt daily at 10am
0 10 * * * bash ~/.claude/skills/job-hunter/scripts/daily_job_hunt.sh
```

The script decides internally whether to also run JSearch (every 2 days). To force a JSearch run:

```bash
rm ~/.job-hunter-jsearch-last-run
```

## API Usage & Cost

| Provider | Free Tier | Usage per run | Monthly (daily cron) |
|----------|-----------|---------------|----------------------|
| JobSpy | Unlimited | 0 requests | $0 |
| JSearch | 200 req/month | 7–14 requests | ~98 req/month ✓ |

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/jobspy_scraper.py` | LinkedIn/Indeed via guest API (no key) |
| `scripts/jsearch_scraper.py` | Google Jobs via RapidAPI |
| `scripts/run_search.py` | Provider-switching search CLI |
| `scripts/score_jobs.py` | Score jobs against resume |
| `scripts/generate_cover_letters.py` | Generate cover letter templates |
| `scripts/daily_job_hunt.sh` | Full pipeline orchestration (cron) |
| `scripts/setup_config.py` | Interactive config setup |
| `scripts/setup_venv.sh` | Virtual environment setup |
| `scripts/common/` | Shared modules (config, scoring, dedup) |

## Obsidian Structure

```
job-hunter/
├── Job Tracker - 2026-02-28.md   # Today's tracker
├── Job Tracker - 2026-02-27.md   # Yesterday's tracker
├── Cover Letters/
│   ├── 2026-02-28/
│   │   ├── Dana-Farber - Data Engineer II.md
│   │   └── Veeva Systems - Senior Health Data Informaticist.md
│   └── 2026-02-27/
```

## Troubleshooting

**No jobs found**
- Broaden search keywords in config
- Check `~/.job-hunter.log` for errors

**JSearch API errors**
- Verify key at [rapidapi.com](https://rapidapi.com)
- Check monthly usage (200 free requests)
- Delete `~/.job-hunter-jsearch-last-run` to retry

**Glassdoor 400 errors in logs**
- Known upstream issue in JobSpy — non-fatal, LinkedIn/Indeed results still collected

**Virtual environment issues**
- Re-run `bash ~/.claude/skills/job-hunter/scripts/setup_venv.sh`
- Requires Python 3.10+

## Acknowledgments

- **[JobSpy](https://github.com/speedyapply/JobSpy)** — Job scraping library that powers the LinkedIn and Indeed integration. Thanks to the JobSpy team for making job data accessible without API keys.
