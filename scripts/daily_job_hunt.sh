#!/bin/bash
# Daily Job Hunt - runs at 10 AM via cron
# Workflow: search → score → save tracker to Obsidian
# Cover letters are generated manually after user reviews the tracker in Obsidian.
set -e

LOG_FILE="$HOME/.job-hunter.log"
SCRIPTS_DIR="$HOME/.claude/skills/job-hunter/scripts"
PYTHON="$HOME/.venv/job-hunter/bin/python3"
CONFIG="$HOME/.config/job-hunter/config.json"
VAULT=$(python3 -c "import json; print(json.load(open('$CONFIG'))['obsidian_vault'])" 2>/dev/null)
TODAY=$(date '+%Y-%m-%d')
TRACKER="$VAULT/Job Tracker - $TODAY.md"

SCRAPED=$(mktemp /tmp/scraped_jobs.XXXXXX.json)
SCORED=$(mktemp /tmp/scored_jobs.XXXXXX.json)
trap 'rm -f "$SCRAPED" "$SCORED"' EXIT

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"; }

log "========================================"
log "Starting daily job hunt for $TODAY..."

# Step 1: JobSpy (runs every day — no API key, no rate limit)
log "Searching jobs (JobSpy)..."
$PYTHON "$SCRIPTS_DIR/run_search.py" --provider jobspy --config "$CONFIG" -o "$SCRAPED" 2>&1 | tee -a "$LOG_FILE"

# Step 1b: JSearch (runs every 2 days — conserves 200 free req/month)
JSEARCH_STATE="$HOME/.job-hunter-jsearch-last-run"
JSEARCH_KEY=$($PYTHON -c "import json; print(json.load(open('$CONFIG')).get('jsearch_api_key',''))" 2>/dev/null || echo "")

if [ -n "$JSEARCH_KEY" ]; then
    DAYS_SINCE=999
    if [ -f "$JSEARCH_STATE" ]; then
        DAYS_SINCE=$($PYTHON -c "from datetime import date; print((date.today()-date.fromisoformat(open('$JSEARCH_STATE').read().strip())).days)" 2>/dev/null || echo 999)
    fi

    if [ "$DAYS_SINCE" -ge 2 ]; then
        log "Running JSearch (every-2-day supplement)..."
        JSEARCH_TMP=$(mktemp /tmp/jsearch_jobs.XXXXXX.json)
        if $PYTHON "$SCRIPTS_DIR/run_search.py" --provider jsearch --config "$CONFIG" -o "$JSEARCH_TMP" 2>&1 | tee -a "$LOG_FILE"; then
            MERGED_TMP=$(mktemp /tmp/merged_jobs.XXXXXX.json)
            $PYTHON - <<PYEOF 2>&1 | tee -a "$LOG_FILE"
import json, sys
sys.path.insert(0, '$SCRIPTS_DIR')
from common.dedup import deduplicate_jobs
a = json.load(open('$SCRAPED'))
b = json.load(open('$JSEARCH_TMP'))
merged = deduplicate_jobs(a + b)
json.dump(merged, open('$MERGED_TMP', 'w'), indent=2, default=str)
print(f"Merged: {len(a)} JobSpy + {len(b)} JSearch → {len(merged)} after dedup")
PYEOF
            cp "$MERGED_TMP" "$SCRAPED"
            rm -f "$MERGED_TMP"
            echo "$TODAY" > "$JSEARCH_STATE"
        fi
        rm -f "$JSEARCH_TMP"
    else
        log "JSearch skip (last ran ${DAYS_SINCE}d ago, next in $((2-DAYS_SINCE))d)"
    fi
fi

# Step 2: Score against resume
log "Scoring jobs..."
$PYTHON "$SCRIPTS_DIR/score_jobs.py" -i "$SCRAPED" -o "$SCORED" --config "$CONFIG" 2>&1 | tee -a "$LOG_FILE"

# Step 3: Save job tracker (score > 40 only, with Source column)
log "Saving job tracker to Obsidian..."
$PYTHON - <<EOF 2>&1 | tee -a "$LOG_FILE"
import json
from pathlib import Path

with open("$SCORED") as f:
    jobs = json.load(f)

filtered = [j for j in jobs if j.get("match_score", 0) > 70]
tracker_path = Path("$TRACKER")

if tracker_path.exists():
    print(f"Tracker already exists for today, skipping: {tracker_path}")
else:
    lines = [
        "# Job Tracker - $TODAY",
        "",
        f"**Jobs with score > 70:** {len(filtered)} of {len(jobs)} found today",
        "",
        "| # | Score | Title | Company | Salary | Remote | Source | Link |",
        "|---|-------|-------|---------|--------|--------|--------|------|",
    ]
    for i, job in enumerate(filtered, 1):
        title   = job.get("title", "N/A").replace("|", "-")[:50]
        company = (job.get("company") or "-").replace("|", "-")[:30]
        score   = job.get("match_score", 0)
        salary  = job.get("salary") or "-"
        remote  = "Yes" if job.get("remote") else "No"
        source  = job.get("source", "-").capitalize()
        url     = job.get("url", "#")
        lines.append(f"| {i} | {score} | {title} | {company} | {salary} | {remote} | {source} | [Apply]({url}) |")
    tracker_path.write_text("\n".join(lines) + "\n")
    print(f"Saved {len(filtered)} jobs to {tracker_path}")
EOF

log "Done. Review 'Job Tracker - $TODAY.md' in Obsidian and ask Claude which numbers to generate cover letters for."
log "========================================"
