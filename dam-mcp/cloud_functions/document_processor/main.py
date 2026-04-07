"""Cloud Function entry point for Firestore-triggered document processing.

Triggered on document creation in the knowledge_base collection.
Performs rule-based extraction of participants, meeting dates, and topic tags.
"""

import re
from datetime import datetime, timezone

from cloudevents.http import CloudEvent
from google.cloud import firestore

import functions_framework

# Configurable topic keywords — extend as needed
TOPIC_KEYWORDS = {
    "sprint": "sprint",
    "standup": "standup",
    "stand-up": "standup",
    "retro": "retrospective",
    "retrospective": "retrospective",
    "planning": "planning",
    "roadmap": "roadmap",
    "hiring": "hiring",
    "interview": "interview",
    "onboarding": "onboarding",
    "design": "design",
    "review": "review",
    "demo": "demo",
    "sync": "sync",
    "kickoff": "kickoff",
    "kick-off": "kickoff",
    "brainstorm": "brainstorm",
    "budget": "budget",
    "strategy": "strategy",
    "product": "product",
    "engineering": "engineering",
    "marketing": "marketing",
    "sales": "sales",
    "customer": "customer",
    "support": "support",
    "incident": "incident",
    "postmortem": "postmortem",
    "post-mortem": "postmortem",
}

# Regex for extracting email addresses
EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

# Date patterns commonly found in meeting note titles
DATE_PATTERNS = [
    # 2026-04-07
    (re.compile(r"(\d{4})-(\d{2})-(\d{2})"), lambda m: (int(m.group(1)), int(m.group(2)), int(m.group(3)))),
    # 2026/04/07 or 2026/4/7
    (re.compile(r"(\d{4})/(\d{1,2})/(\d{1,2})"), lambda m: (int(m.group(1)), int(m.group(2)), int(m.group(3)))),
    # 04/07/2026 or 4/7/2026
    (re.compile(r"(\d{1,2})/(\d{1,2})/(\d{4})"), lambda m: (int(m.group(3)), int(m.group(1)), int(m.group(2)))),
    # April 7, 2026 or Apr 7, 2026
    (re.compile(
        r"(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
        r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
        r"\s+(\d{1,2}),?\s+(\d{4})",
        re.IGNORECASE,
    ), None),  # handled separately
    # 7 April 2026
    (re.compile(
        r"(\d{1,2})\s+"
        r"(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
        r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
        r",?\s+(\d{4})",
        re.IGNORECASE,
    ), None),  # handled separately
]

MONTH_MAP = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}


def _extract_emails(content: str) -> list[str]:
    """Extract unique email addresses from content."""
    emails = EMAIL_PATTERN.findall(content)
    return list(dict.fromkeys(emails))  # deduplicate preserving order


def _parse_date_from_title(title: str) -> datetime | None:
    """Try to parse a date from the document title."""
    # Patterns with simple lambda extractors (YYYY-MM-DD, YYYY/MM/DD, MM/DD/YYYY)
    for pattern, extractor in DATE_PATTERNS[:3]:
        m = pattern.search(title)
        if m and extractor:
            try:
                y, mo, d = extractor(m)
                return datetime(y, mo, d, tzinfo=timezone.utc)
            except ValueError:
                continue

    # Pattern: Month Day, Year (e.g. "April 7, 2026")
    m = DATE_PATTERNS[3][0].search(title)
    if m:
        try:
            month_name = m.group(1).lower()
            day = int(m.group(2))
            year = int(m.group(3))
            month = MONTH_MAP.get(month_name)
            if month:
                return datetime(year, month, day, tzinfo=timezone.utc)
        except (ValueError, KeyError):
            pass

    # Pattern: Day Month Year (e.g. "7 April 2026")
    m = DATE_PATTERNS[4][0].search(title)
    if m:
        try:
            day = int(m.group(1))
            month_name = m.group(2).lower()
            year = int(m.group(3))
            month = MONTH_MAP.get(month_name)
            if month:
                return datetime(year, month, day, tzinfo=timezone.utc)
        except (ValueError, KeyError):
            pass

    return None


def _extract_topic_tags(title: str, content: str) -> list[str]:
    """Extract topic tags based on keyword matching in title and content."""
    text = f"{title} {content}".lower()
    found_tags = set()
    for keyword, tag in TOPIC_KEYWORDS.items():
        if keyword in text:
            found_tags.add(tag)
    return sorted(found_tags)


def _get_firestore_client():
    import os
    project_id = os.environ.get("GCP_PROJECT_ID")
    database = os.environ.get("FIRESTORE_DATABASE", "(default)")
    return firestore.Client(project=project_id, database=database)


@functions_framework.cloud_event
def process_document(cloud_event: CloudEvent):
    """Process a newly created document in the knowledge_base collection.

    Extracts participants, meeting date, and topic tags using rule-based logic.
    Updates the document with extracted data and sets processing_status to 'processed'.
    """
    # Extract document path from the CloudEvent subject
    # subject format: "documents/knowledge_base/{doc_id}"
    subject = cloud_event["subject"]
    parts = subject.split("/")
    if len(parts) < 3:
        return
    collection = parts[1]
    doc_id = parts[2]

    fs_client = _get_firestore_client()
    doc_ref = fs_client.collection(collection).document(doc_id)
    doc = doc_ref.get()

    if not doc.exists:
        return

    data = doc.to_dict()
    title = data.get("title", "")
    content = data.get("content", "")

    # Set processing status
    doc_ref.update({"processing_status": "processing"})

    try:
        # Extract participants from content
        participants = _extract_emails(content)

        # Parse meeting date from title
        meeting_date = _parse_date_from_title(title)

        # Extract topic tags
        topic_tags = _extract_topic_tags(title, content)

        # Merge with existing tags (no duplicates)
        existing_tags = data.get("tags", []) or []
        merged_tags = list(dict.fromkeys(existing_tags + topic_tags))

        # Build update
        updates = {
            "participants": participants if participants else None,
            "meeting_date": meeting_date,
            "tags": merged_tags,
            "sensitivity": "unreviewed",
            "processing_status": "processed",
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": firestore.SERVER_TIMESTAMP,
        }

        doc_ref.update(updates)
    except Exception as e:
        doc_ref.update({
            "processing_status": "failed",
            "updated_at": firestore.SERVER_TIMESTAMP,
        })
        raise e
