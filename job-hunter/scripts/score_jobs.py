#!/usr/bin/env python3
"""
Job Scoring CLI - Score jobs against resume skills.

Usage:
    python score_jobs.py -i /tmp/jobs.json -o /tmp/scored.json
    python score_jobs.py -i /tmp/jobs.json  # output to stdout
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from common.job_scoring import score_jobs


def main():
    parser = argparse.ArgumentParser(description="Score jobs against resume skills")
    parser.add_argument("--input", "-i", required=True, help="Input jobs JSON file")
    parser.add_argument("--output", "-o", help="Output scored JSON file (default: stdout)")
    parser.add_argument("--resume", help="Path to resume file (.docx or .pdf)")
    parser.add_argument("--config", help="Path to config JSON (used to find resume if --resume not set)")

    args = parser.parse_args()

    resume_path = args.resume
    if not resume_path and args.config:
        config_path = Path(args.config).expanduser()
        if config_path.exists():
            with open(config_path) as f:
                cfg = json.load(f)
            resume_path = cfg.get("resume_path")

    with open(Path(args.input).expanduser()) as f:
        jobs = json.load(f)

    scored = score_jobs(jobs, resume_path=resume_path)
    print(f"Scored {len(scored)} jobs", file=sys.stderr)

    output = json.dumps(scored, indent=2, default=str)

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w") as f:
            f.write(output)
        print(f"Saved to {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
