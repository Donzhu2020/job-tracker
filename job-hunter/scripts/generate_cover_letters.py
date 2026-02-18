#!/usr/bin/env python3
"""
Generate cover letters for job matches with dated organization.

Usage:
    python generate_cover_letters.py --jobs scored_jobs.json --config ~/.config/job-hunter/config.json
    python generate_cover_letters.py --jobs scored_jobs.json --top 10
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from common.config import load_config, get_user_info


def clean_description(text: str) -> str:
    """Strip markdown headers, deduplicate lines, and remove sidebar noise."""
    # Remove markdown headers (# ## ###)
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    # Remove lines that are just dots or dashes
    text = re.sub(r'^\s*[.\-*]+\s*$', '', text, flags=re.MULTILINE)
    # Collapse runs of blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Remove duplicate consecutive sentences/lines (LinkedIn sidebar)
    seen, deduped = set(), []
    for line in text.split('\n'):
        stripped = line.strip()
        if stripped and stripped not in seen:
            seen.add(stripped)
            deduped.append(line)
        elif not stripped:
            deduped.append(line)
    return '\n'.join(deduped).strip()


def extract_key_requirements(description: str) -> list[str]:
    """Pull bullet-point requirements from job description."""
    reqs = []
    for line in description.split('\n'):
        line = line.strip().lstrip('*•-').strip()
        # Lines that look like requirements: start with a verb or "X years"
        if (len(line) > 20 and len(line) < 200
                and re.match(r'^(experience|profici|strong|knowledge|ability|bachelor|master|phd|\d+\+?\s+year)', line.lower())):
            reqs.append(line)
        if len(reqs) >= 5:
            break
    return reqs


def generate_cover_letter(job: dict, config: dict) -> str:
    """Generate a cover letter for a job posting."""
    title = job.get('title', 'Position')
    company = job.get('company', 'Company')
    location = job.get('location', 'N/A')
    match_score = job.get('match_score', 0)
    raw_description = job.get('description', '')
    description = clean_description(raw_description)

    user_info = get_user_info(config)
    user_name = user_info["name"] or "Your Name"

    # Build a short description snippet (first 2 clean sentences, no markdown)
    first_para = description.split('\n\n')[0].replace('\n', ' ').strip()
    # Trim to first 250 chars at a sentence boundary
    if len(first_para) > 250:
        cut = first_para[:250].rfind('. ')
        first_para = first_para[:cut + 1] if cut > 50 else first_para[:250]

    cover_letter = f"""# Cover Letter - {company}

**Position:** {title}
**Company:** {company}
**Location:** {location}
**Match Score:** {match_score}/100
**Date Created:** {datetime.now().strftime('%Y-%m-%d')}

---

## Letter

Dear Hiring Manager,

I am writing to express my strong interest in the {title} position at {company}. With my background in [your field and years of experience], I am excited about the opportunity to contribute to your team.

[Describe your current role and most relevant experience. Highlight specific projects or accomplishments that directly relate to this position.]

My technical background includes:

- [Key skill 1 relevant to the role]
- [Key skill 2 relevant to the role]
- [Key skill 3 relevant to the role]
- [Key skill 4 relevant to the role]

I am particularly drawn to {company} because [specific reason related to the company's mission, products, or values]. I would welcome the opportunity to bring my skills and experience to your team.

Thank you for considering my application. I look forward to the opportunity to discuss how I can contribute.

Sincerely,

{user_name}

---

## Job Details

**Posted:** {job.get('posted_date') or 'Unknown'}
**Remote:** {'Yes' if job.get('remote') else 'No'}
**Employment Type:** {job.get('employment_type') or 'Not specified'}
**Salary:** {job.get('salary') or 'Not specified'}

**Application URL:** {job.get('url', '#')}

### Match Reason:
{job.get('match_reason', 'General fit')}

### Description Excerpt:
{description[:600] if description else 'No description available'}

---

**Tags:** #cover-letter #job-application #{company.replace(' ', '-').replace(',', '').lower()}
**Status:** Draft
**Applied:** [ ] No

"""

    return cover_letter


def main():
    parser = argparse.ArgumentParser(description='Generate cover letters for job matches')
    parser.add_argument('--jobs', required=True, help='Path to scored jobs JSON file')
    parser.add_argument('--config', default='~/.config/job-hunter/config.json',
                       help='Path to config file')
    parser.add_argument('--top', type=int, default=5,
                       help='Number of top jobs to generate cover letters for (ignored if --indices is set)')
    parser.add_argument('--indices', help='Comma-separated 1-based indices to generate, e.g. "1,3,5"')
    parser.add_argument('--output-dir', help='Override output directory')

    args = parser.parse_args()

    config = load_config(args.config)

    if args.output_dir:
        output_base = Path(args.output_dir).expanduser()
    else:
        vault_path = config.get('obsidian_vault', '~/Documents/Obsidian Vault/job-hunter')
        output_base = Path(vault_path).expanduser() / 'Cover Letters'

    # Create dated subfolder for this run
    today = datetime.now().strftime('%Y-%m-%d')
    output_dir = output_base / today
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(Path(args.jobs).expanduser()) as f:
        jobs = json.load(f)

    if args.indices:
        selected_indices = [int(i.strip()) - 1 for i in args.indices.split(',')]
        jobs_to_process = [jobs[i] for i in selected_indices if 0 <= i < len(jobs)]
    else:
        jobs_to_process = jobs[:min(args.top, len(jobs))]

    num_letters = len(jobs_to_process)

    print(f"Generating {num_letters} cover letters in {output_dir}/")

    for i, job in enumerate(jobs_to_process, 1):
        title = job.get('title', 'Position')
        company = job.get('company', 'Company')

        cover_letter = generate_cover_letter(job, config)

        safe_company = company.replace('/', '_').replace(':', '_').replace('|', '_')[:50]
        safe_title = title.replace('/', '_').replace(':', '_').replace('|', '_')[:40]
        filename = f"{safe_company} - {safe_title}.md"

        output_file = output_dir / filename
        with open(output_file, 'w') as f:
            f.write(cover_letter)

        print(f"  {i}. {filename}")

    print(f"\nGenerated {num_letters} cover letter(s) in {output_dir}/")


if __name__ == '__main__':
    main()
