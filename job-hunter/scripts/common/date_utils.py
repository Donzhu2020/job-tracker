"""Date parsing utilities for job postings."""

import re
from datetime import datetime, timedelta


def parse_job_date(date_str: str) -> datetime | None:
    """Parse a job posting date string into a datetime.

    Supports:
    - ISO 8601: "2025-01-27T10:00:00Z"
    - Date only: "2025-01-27"
    - Relative: "2 hours ago", "1 day ago", "3 days ago"
    """
    if not date_str:
        return None

    date_str = date_str.strip()

    # ISO 8601
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d", "%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(date_str, fmt).replace(tzinfo=None)
        except ValueError:
            continue

    # Relative time: "X hours/days/minutes ago"
    match = re.match(r"(\d+)\s+(minute|hour|day|week|month)s?\s+ago", date_str, re.IGNORECASE)
    if match:
        amount = int(match.group(1))
        unit = match.group(2).lower()
        deltas = {
            "minute": timedelta(minutes=amount),
            "hour": timedelta(hours=amount),
            "day": timedelta(days=amount),
            "week": timedelta(weeks=amount),
            "month": timedelta(days=amount * 30),
        }
        return datetime.now() - deltas.get(unit, timedelta())

    return None


def is_within_hours(date_str: str, hours: int = 24) -> bool:
    """Check if a date string is within the last N hours."""
    parsed = parse_job_date(date_str)
    if parsed is None:
        return True  # Include if we can't parse (benefit of the doubt)
    return (datetime.now() - parsed) <= timedelta(hours=hours)
