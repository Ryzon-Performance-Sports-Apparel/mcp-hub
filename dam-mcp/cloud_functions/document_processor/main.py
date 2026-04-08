"""Cloud Function entry point for Firestore-triggered document processing.

Triggered on document creation in the knowledge_base collection.
Performs rule-based extraction of participants, meeting dates, and topic tags.
"""

import os
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


EXTRACT_TOOL = {
    "name": "extract_meeting_metadata",
    "description": "Extract structured metadata from meeting notes.",
    "input_schema": {
        "type": "object",
        "properties": {
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Topic tags — be specific (project names, team names, topic-specific terms), not generic. Include 3-8 tags.",
            },
            "summary": {
                "type": "string",
                "description": "2-3 sentence summary of what was discussed and decided",
            },
            "sensitivity": {
                "type": "string",
                "enum": ["safe", "contains_pii"],
                "description": "Flag 'contains_pii' only for genuinely personal data (health info, salary, personal phone/address). Business emails and professional names are NOT PII.",
            },
            "action_items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "task": {"type": "string"},
                        "assignee": {"type": "string"},
                        "due": {"type": "string"},
                    },
                    "required": ["task"],
                },
            },
            "key_decisions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Concrete decisions made during the meeting",
            },
            "meeting_type": {
                "type": "string",
                "enum": ["standup", "planning", "review", "retro", "1on1", "kickoff", "demo", "brainstorm", "sync", "other"],
            },
            "language": {
                "type": "string",
                "description": "ISO 639-1 code of the primary language (e.g. 'en', 'de')",
            },
        },
        "required": ["tags", "summary", "sensitivity", "action_items", "key_decisions", "meeting_type", "language"],
    },
}

SYSTEM_PROMPT = (
    "You are a meeting notes analyst. Extract structured metadata from the provided meeting title and content.\n\n"
    "Guidelines:\n"
    "- tags: Be specific — use project names, team names, and topic-specific terms rather than generic words. Include 3-8 tags.\n"
    "- summary: Write 2-3 sentences covering what was discussed and what was decided.\n"
    "- sensitivity: Flag 'contains_pii' ONLY for genuinely personal data such as health information, salary figures, "
    "or personal phone numbers and home addresses. Business emails and professional names are NOT PII — mark those as 'safe'.\n"
    "- action_items: List every concrete task with its assignee and due date when mentioned.\n"
    "- key_decisions: List only firm, concrete decisions — not discussion points or open questions.\n"
    "- meeting_type: Choose the single best-fitting type from the allowed values.\n"
    "- language: Detect the primary language and return its ISO 639-1 code (e.g. 'en', 'de', 'fr')."
)


def _extract_with_llm(client, title: str, content: str) -> dict | None:
    """Call Claude Haiku to extract structured metadata from meeting notes.

    Returns the tool input dict on success, or None if extraction fails.
    """
    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=[EXTRACT_TOOL],
            tool_choice={"type": "tool", "name": "extract_meeting_metadata"},
            messages=[
                {
                    "role": "user",
                    "content": f"Title: {title}\n\n{content}",
                }
            ],
        )
        for block in response.content:
            if block.type == "tool_use":
                return block.input
        return None
    except Exception:
        return None


MAX_CONTENT_CHARS = 8000

def _generate_embedding(client, title: str, summary: str, content: str) -> list[float] | None:
    """Generate a vector embedding via Voyage AI. Returns None on failure."""
    try:
        truncated_content = content[:MAX_CONTENT_CHARS]
        input_text = f"{title}\n\n{summary}\n\n{truncated_content}"
        result = client.embed(
            texts=[input_text],
            model="voyage-3-lite",
            input_type="document",
        )
        return result.embeddings[0]
    except Exception:
        return None


def _get_anthropic_client():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    import anthropic
    return anthropic.Anthropic(api_key=api_key)


def _get_voyage_client():
    api_key = os.environ.get("VOYAGE_API_KEY")
    if not api_key:
        return None
    import voyageai
    return voyageai.Client(api_key=api_key)


def _get_firestore_client():
    import os
    project_id = os.environ.get("GCP_PROJECT_ID")
    database = os.environ.get("FIRESTORE_DATABASE", "(default)")
    return firestore.Client(project=project_id, database=database)


@functions_framework.cloud_event
def process_document(cloud_event: CloudEvent):
    """Process a newly created document in the knowledge_base collection.

    Step 1: Rule-based extraction (dates, emails, keyword tags)
    Step 2: LLM enrichment via Claude Haiku (tags, summary, PII, action items, etc.)
    Step 3: Vector embedding via Voyage AI
    Step 4: PII handling (move to restricted collection if flagged)
    """
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

    doc_ref.update({"processing_status": "processing"})

    try:
        # Step 1: Rule-based extraction
        participants = _extract_emails(content)
        meeting_date = _parse_date_from_title(title)
        rule_tags = _extract_topic_tags(title, content)

        existing_tags = data.get("tags", []) or []
        merged_tags = list(dict.fromkeys(existing_tags + rule_tags))

        updates = {
            "participants": data.get("participants") or (participants if participants else None),
            "meeting_date": data.get("meeting_date") or meeting_date,
            "tags": merged_tags,
            "sensitivity": "safe",
            "processing_status": "processed",
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": firestore.SERVER_TIMESTAMP,
            "llm_enriched": False,
        }

        # Step 2: LLM enrichment
        anthropic_client = _get_anthropic_client()
        if anthropic_client:
            llm_result = _extract_with_llm(anthropic_client, title, content)
            if llm_result:
                updates["llm_enriched"] = True
                updates["summary"] = llm_result.get("summary")
                updates["sensitivity"] = llm_result.get("sensitivity", "safe")
                updates["action_items"] = llm_result.get("action_items", [])
                updates["key_decisions"] = llm_result.get("key_decisions", [])
                updates["meeting_type"] = llm_result.get("meeting_type")
                updates["language"] = llm_result.get("language")
                llm_tags = llm_result.get("tags", [])
                updates["tags"] = list(dict.fromkeys(merged_tags + llm_tags))

        # Step 3: Vector embedding
        summary_for_embedding = updates.get("summary", "")
        voyage_client = _get_voyage_client()
        if voyage_client:
            embedding = _generate_embedding(voyage_client, title, summary_for_embedding, content)
            if embedding:
                from google.cloud.firestore_v1.vector import Vector
                updates["embedding"] = Vector(embedding)

        # Step 4: PII handling
        if updates.get("sensitivity") == "contains_pii":
            full_doc = {**data, **updates}
            full_doc.pop("id", None)
            full_doc["created_at"] = firestore.SERVER_TIMESTAMP
            full_doc["updated_at"] = firestore.SERVER_TIMESTAMP
            fs_client.collection("knowledge_base_restricted").document(doc_id).set(full_doc)
            doc_ref.delete()
        else:
            doc_ref.update(updates)

    except Exception as e:
        doc_ref.update({
            "processing_status": "failed",
            "updated_at": firestore.SERVER_TIMESTAMP,
        })
        raise e
