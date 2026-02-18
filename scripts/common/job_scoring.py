"""Job scoring logic - scores jobs against resume content."""

import sys
from pathlib import Path

# Fallback skill list if resume cannot be read
_FALLBACK_SKILLS = [
    'python', 'sql', 'tableau', 'data analyst', 'data science', 'data scientist',
    'machine learning', 'deep learning', 'research', 'healthcare', 'clinical',
    'ehr', 'informatics', 'aws', 'pytorch', 'pandas', 'statistics',
]

# Bonus rules: (keywords_any_match, points)
# Applied on top of per-skill scoring
_BONUS_RULES = [
    # Role alignment bonuses
    (['data analyst', 'data analysis'],                         15),
    (['research analyst', 'research data analyst'],             15),
    (['informatics analyst', 'health informatics'],             15),
    (['clinical data analyst', 'clinical analyst'],             15),
    (['data scientist', 'data science'],                        15),
    (['machine learning engineer', 'ml engineer'],              10),
    # Domain bonuses
    (['healthcare', 'clinical', 'medical', 'health system'],    10),
    (['ehr', 'electronic health record', 'epic', 'cerner',
      'omop', 'i2b2', 'fhir'],                                 10),
    (['research', 'scientist'],                                 10),
    (['phd', 'doctoral', 'graduate'],                           8),
    (['wearable', 'sensor', 'iot', 'fitbit'],                   8),
    # Remote bonus
    (['remote', 'hybrid'],                                       5),
]


def load_resume_text(resume_path: str) -> str:
    """Load plain text from a resume file (.docx or .txt/.pdf)."""
    path = Path(resume_path).expanduser()
    if not path.exists():
        print(f"[scoring] Resume not found: {path}", file=sys.stderr)
        return ""

    suffix = path.suffix.lower()
    try:
        if suffix == '.docx':
            from docx import Document  # python-docx
            doc = Document(str(path))
            return ' '.join(p.text for p in doc.paragraphs)
        elif suffix == '.pdf':
            import PyPDF2
            text = []
            with open(path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    text.append(page.extract_text() or '')
            return ' '.join(text)
        else:
            return path.read_text(errors='ignore')
    except Exception as e:
        print(f"[scoring] Could not read resume: {e}", file=sys.stderr)
        return ""


def extract_skills_from_resume(resume_text: str) -> list[str]:
    """Extract matchable skill keywords from resume text.

    Uses a curated master list and returns only those that appear in
    the resume, so matching reflects the candidate's actual profile.
    """
    # Master list of terms that commonly appear in both resumes and job postings
    candidates = [
        # Programming & databases
        'python', 'java', 'kotlin', 'c++', 'sql', 'postgresql', 'mongodb',
        'pandas', 'numpy', 'scikit-learn', 'scipy',
        # ML / AI
        'machine learning', 'deep learning', 'pytorch', 'tensorflow',
        'neural network', 'cnn', 'rnn', 'lstm', 'transformer',
        'nlp', 'natural language processing', 'large language model', 'llm',
        'computer vision', 'fair ml', 'fairness', 'predictive modeling',
        'feature engineering', 'statistical modeling', 'statistics',
        'regression', 'classification', 'clustering', 'a/b testing',
        # Cloud / infra
        'aws', 'lambda', 'dynamodb', 'ec2', 's3', 'docker',
        'distributed systems', 'etl', 'data pipeline', 'cloud',
        # Data / visualization
        'tableau', 'matplotlib', 'seaborn', 'excel', 'power bi',
        'arcgis', 'geospatial', 'exploratory data analysis',
        'business intelligence', 'data visualization',
        # Healthcare / clinical
        'healthcare', 'clinical', 'ehr', 'electronic health record',
        'omop', 'fhir', 'hipaa', 'informatics', 'health informatics',
        'clinical data', 'medical', 'patient data', 'all of us',
        # Research
        'research', 'data scientist', 'data analyst', 'data science',
        'informatics analyst', 'research analyst',
        # Wearable / IoT
        'wearable', 'sensor', 'iot', 'fitbit', 'mobile',
        # Other
        'flutter', 'git', 'docker', 'web scraping', 'mongodb',
    ]

    text_lower = resume_text.lower()
    found = [skill for skill in candidates if skill in text_lower]
    # Deduplicate while preserving order
    seen = set()
    result = []
    for s in found:
        if s not in seen:
            seen.add(s)
            result.append(s)
    return result


def score_job(job: dict, resume_skills: list[str]) -> tuple[int, str]:
    """Score a single job against resume skills. Returns (score, match_reason)."""
    text = (
        job.get('title', '') + ' ' +
        job.get('description', '') + ' ' +
        job.get('company', '')
    ).lower()

    score = 0
    matches = []

    # Per-skill keyword match: +5 each
    for skill in resume_skills:
        if skill in text:
            score += 5
            matches.append(skill)

    # Bonus rules
    for keywords, points in _BONUS_RULES:
        if any(kw in text for kw in keywords):
            score += points

    score = min(score, 100)
    reason = f"Matches: {', '.join(matches[:6])}" if matches else 'General fit'
    return score, reason


def score_jobs(
    jobs: list[dict],
    resume_skills: list[str] | None = None,
    resume_path: str | None = None,
) -> list[dict]:
    """Score and sort jobs. Returns jobs with match_score and match_reason added.

    Priority: resume_skills (explicit) > resume_path (read file) > fallback list.
    """
    if resume_skills is None:
        if resume_path:
            text = load_resume_text(resume_path)
            if text:
                resume_skills = extract_skills_from_resume(text)
                print(f"[scoring] Loaded {len(resume_skills)} skills from resume", file=sys.stderr)
            else:
                resume_skills = _FALLBACK_SKILLS
        else:
            resume_skills = _FALLBACK_SKILLS

    for job in jobs:
        s, reason = score_job(job, resume_skills)
        job['match_score'] = s
        job['match_reason'] = reason

    jobs.sort(key=lambda x: x['match_score'], reverse=True)
    return jobs
