#!/usr/bin/env python3
"""
AI re-rank helper — lets Claude judge resume-vs-job fit beyond keyword matching.

Keyword scoring (score_jobs.py) is fast and free but literal: it can't tell
"we use Python to build Excel macros" from "ML platform team". This module
prepares a compact packet of the top-N keyword-scored jobs plus the resume,
which the Claude session running the skill reads and scores holistically.
No API key needed — the reasoning happens in the skill session itself.

Two subcommands:

  prep   Build a markdown packet for Claude to read.
         python rerank.py prep -i /tmp/scored.json --config CONFIG \
             -o /tmp/rerank_packet.md --top 30

  apply  Merge Claude's scores back and re-sort the jobs file.
         python rerank.py apply -i /tmp/scored.json -r /tmp/rerank_scores.json \
             -o /tmp/scored.json

The scores file (written by Claude) maps job id → score/reason:
    {
      "a1b2c3d4e5f6": {"ai_score": 88, "ai_reason": "Strong healthcare + Python overlap"},
      ...
    }

After apply, each job gains `final_score` (= ai_score when present, else
match_score) and the list is re-sorted by final_score descending, so tracker
row numbers still align with cover-letter --indices.
"""

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from common.config import load_config
from common.job_scoring import load_resume_text

DEFAULT_TOP = 30
RESUME_CHARS = 4000
DESCRIPTION_CHARS = 1200


def cmd_prep(args) -> None:
    with open(Path(args.input).expanduser()) as f:
        jobs = json.load(f)

    resume_text = ""
    if args.resume:
        resume_text = load_resume_text(args.resume)
    elif args.config:
        config = load_config(args.config)
        if config.get("resume_path"):
            resume_text = load_resume_text(config["resume_path"])

    top = jobs[: args.top]
    lines = [
        "# Re-rank Packet",
        "",
        "Score each job 0-100 for fit against the resume below. Judge holistically:",
        "seniority match, domain overlap, day-to-day work vs. candidate strengths —",
        "not keyword presence. A job can keyword-match heavily and still be a bad fit.",
        "",
        "## Resume",
        "",
        resume_text[:RESUME_CHARS] if resume_text else "(resume unavailable — score on job quality and internal consistency only)",
        "",
        "## Jobs",
        "",
    ]
    for i, job in enumerate(top, 1):
        desc = (job.get("description") or "").strip()
        if len(desc) > DESCRIPTION_CHARS:
            desc = desc[:DESCRIPTION_CHARS] + " …[truncated]"
        lines += [
            f"### Job {i} — id: `{job.get('id', '')}`",
            f"- **Title:** {job.get('title', '')}",
            f"- **Company:** {job.get('company', '')}",
            f"- **Location:** {job.get('location', '')} | Remote: {'Yes' if job.get('remote') else 'No'}",
            f"- **Salary:** {job.get('salary') or 'n/a'} | Keyword score: {job.get('match_score', 'n/a')}",
            "",
            desc if desc else "(no description available — score conservatively from title/company)",
            "",
        ]

    lines += [
        "## Required output",
        "",
        "Write a JSON file mapping every job id above to its score:",
        "",
        "```json",
        '{"<id>": {"ai_score": 0-100, "ai_reason": "<one line, max 80 chars>"}}',
        "```",
    ]

    out = "\n".join(lines)
    if args.output:
        out_path = Path(args.output).expanduser()
        out_path.write_text(out)
        os.chmod(out_path, 0o600)  # resume excerpt; restrict to owner
        print(f"Wrote re-rank packet with {len(top)} jobs to {args.output}")
    else:
        print(out)


def cmd_apply(args) -> None:
    with open(Path(args.input).expanduser()) as f:
        jobs = json.load(f)
    with open(Path(args.scores).expanduser()) as f:
        scores = json.load(f)

    applied = 0
    for job in jobs:
        entry = scores.get(job.get("id", ""))
        if entry and isinstance(entry.get("ai_score"), (int, float)):
            ai = max(0, min(100, int(entry["ai_score"])))
            job["ai_score"] = ai
            job["ai_reason"] = str(entry.get("ai_reason", ""))[:120]
            job["final_score"] = ai
            applied += 1
        else:
            job["final_score"] = job.get("match_score", 0)

    jobs.sort(key=lambda j: j.get("final_score", 0), reverse=True)

    output_path = Path(args.output or args.input).expanduser()
    output_path.write_text(json.dumps(jobs, indent=2, default=str))
    print(f"Applied AI scores to {applied}/{len(jobs)} jobs; re-sorted by final_score → {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Prepare/apply AI re-ranking of scored jobs")
    sub = parser.add_subparsers(dest="command", required=True)

    prep = sub.add_parser("prep", help="Build markdown packet for Claude to read")
    prep.add_argument("--input", "-i", required=True, help="Scored jobs JSON")
    prep.add_argument("--config", default="~/.config/job-hunter/config.json")
    prep.add_argument("--resume", help="Resume path (overrides config)")
    prep.add_argument("--top", type=int, default=DEFAULT_TOP, help=f"Jobs to include (default {DEFAULT_TOP})")
    prep.add_argument("--output", "-o", help="Packet output path (default: stdout)")
    prep.set_defaults(func=cmd_prep)

    apply_p = sub.add_parser("apply", help="Merge Claude's scores back into jobs JSON")
    apply_p.add_argument("--input", "-i", required=True, help="Scored jobs JSON")
    apply_p.add_argument("--scores", "-r", required=True, help="JSON of id → {ai_score, ai_reason}")
    apply_p.add_argument("--output", "-o", help="Output path (default: overwrite input)")
    apply_p.set_defaults(func=cmd_apply)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
