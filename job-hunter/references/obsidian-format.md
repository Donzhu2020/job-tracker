# Obsidian Output Format Specification

This document defines the format for job tracking notes in Obsidian.

## Directory Structure

```
job-hunter/
├── Job Tracker - 2025-01-27.md  # Today's tracker (dated per run day)
├── Job Tracker - 2025-01-26.md  # Previous day's tracker
├── Job Tracker.md               # Legacy tracker (still read for dedup)
├── Cover Letters/
│   ├── TechCorp - Senior SWE.md
│   └── StartupXYZ - Backend Lead.md
├── Archive/
│   └── 2025-01/                 # Monthly archives
│       └── Job Tracker - 2025-01-15.md
└── Templates/
    └── Cover Letter Template.md
```

## Job Tracker Format

### Job Tracker - YYYY-MM-DD.md

```markdown
---
updated: 2025-01-27T10:30:00
total_jobs: 45
jobs_applied: 12
jobs_interviewing: 3
---

# Job Tracker

## Summary
- **Total Jobs Tracked:** 45
- **Applied:** 12
- **Interviewing:** 3
- **Rejected:** 5
- **Offers:** 0

## Active Jobs

| ID | Date | Company | Title | Match | Status | Source | Link |
|----|------|---------|-------|-------|--------|--------|------|
| abc123 | 2025-01-27 | TechCorp | Senior SWE | 92% | 🔍 New | LinkedIn | [Apply](url) |
| def456 | 2025-01-26 | StartupXYZ | Backend Lead | 88% | ✅ Applied | Indeed | [Apply](url) |
| ghi789 | 2025-01-25 | BigCo | Staff Engineer | 85% | 📞 Interview | LinkedIn | [Apply](url) |

## Legend
- 🔍 New - Just scraped, not yet reviewed
- 👀 Reviewing - Currently reviewing
- ✅ Applied - Application submitted
- 📞 Interview - Interview scheduled/completed
- ❌ Rejected - Application rejected
- 🎉 Offer - Received offer
- ⏸️ Paused - On hold
- 🚫 Not Interested - Decided not to apply
```

### Table Fields

| Field | Description |
|-------|-------------|
| ID | Unique 12-character hash |
| Date | Date job was scraped |
| Company | Company name |
| Title | Job title |
| Match | AI match score (0-100%). Rows sorted by Match descending (highest first) |
| Status | Current status emoji + text |
| Source | linkedin or indeed |
| Link | Apply link |

## Cover Letter Format

### Individual Cover Letter Notes

Filename: `{Company} - {Title}.md`

```markdown
---
job_id: abc123def456
company: TechCorp
title: Senior Software Engineer
location: San Francisco, CA
match_score: 92
status: new
source: linkedin
url: https://linkedin.com/jobs/view/...
scraped_at: 2025-01-27T10:30:00
applied_at: null
---

# TechCorp - Senior Software Engineer

## Job Details

**Company:** TechCorp
**Location:** San Francisco, CA (Remote OK)
**Salary:** $150,000 - $200,000

### Description
[Full job description here]

### Requirements
- 5+ years of experience with Python
- Experience with distributed systems
- Strong communication skills

## Match Analysis

**Score:** 92%

### Why This Matches
- Your 7 years of Python experience exceeds requirement
- Your work on microservices at PrevCo aligns with distributed systems
- Open source contributions show communication ability

### Potential Gaps
- Job mentions Kubernetes experience (you have Docker but limited K8s)

## Cover Letter

Dear Hiring Manager,

[AI-generated personalized cover letter]

Best regards,
[Your Name]

---

## Notes

- [ ] Research company culture
- [ ] Prepare portfolio examples
- [ ] Draft follow-up email

## Timeline

- **2025-01-27:** Job discovered
```

## Frontmatter Schema

### Job Tracker Frontmatter

```yaml
updated: ISO 8601 datetime
total_jobs: integer
jobs_applied: integer
jobs_interviewing: integer
```

### Cover Letter Frontmatter

```yaml
job_id: string (12 char hash)
company: string
title: string
location: string
match_score: integer (0-100)
status: string (new|reviewing|applied|interview|rejected|offer|paused|not_interested)
source: string (linkedin|indeed)
url: string (apply URL)
scraped_at: ISO 8601 datetime
applied_at: ISO 8601 datetime or null
```

## Status Workflow

```
New → Reviewing → Applied → Interview → Offer
                    ↓           ↓
                Rejected    Rejected
```

Valid transitions:
- `new` → `reviewing`, `not_interested`
- `reviewing` → `applied`, `paused`, `not_interested`
- `applied` → `interview`, `rejected`
- `interview` → `offer`, `rejected`
- `paused` → `reviewing`, `not_interested`

## Archiving

At the start of each month, the previous month's completed jobs are moved to:
```
Archive/YYYY-MM/Job Tracker - YYYY-MM-DD.md
```

Archived jobs include:
- All jobs with status: `rejected`, `offer`, `not_interested`
- Jobs older than 60 days with status: `new`, `paused`

## Tags

Use these tags for Obsidian organization:

- `#job-hunt` - All job hunting notes
- `#job-hunt/new` - New jobs to review
- `#job-hunt/applied` - Applied jobs
- `#job-hunt/interview` - Interview stage
- `#job-hunt/offer` - Received offers
- `#job-hunt/rejected` - Rejections (for learning)

## Linking

- Link cover letters to Job Tracker: `[[Job Tracker - YYYY-MM-DD#abc123]]`
- Link Job Tracker to cover letters: `[[Cover Letters/TechCorp - Senior SWE]]`
- Use company as alias: `[[Cover Letters/TechCorp - Senior SWE|TechCorp]]`
