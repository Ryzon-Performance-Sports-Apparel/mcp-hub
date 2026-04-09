"""query_knowledge_base tool — search documents in the Firestore knowledge base."""

import json
from datetime import datetime, timezone
from typing import Optional

from .access import PolicyEngine
from .config import config
from .firestore import document_to_json, query_documents
from .server import mcp_server
from .utils import logger


@mcp_server.tool()
async def query_knowledge_base(
    type: Optional[str] = None,
    tags: Optional[list[str]] = None,
    meeting_series: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    status: Optional[str] = "processed",
    limit: int = 20,
) -> str:
    """Search documents in the knowledge base by type, tags, meeting series, or date range.

    Returns metadata and a content preview (first 500 chars) for each match.
    Use get_document to fetch the full content of a specific document.
    Results are filtered based on your access level.

    Args:
        type: Document type filter (e.g. "meeting_note")
        tags: Filter by tags (matches any of the provided tags)
        meeting_series: Filter by meeting series name (e.g. "weekly-standup")
        date_from: ISO date string, filter meeting_date >= this date
        date_to: ISO date string, filter meeting_date <= this date
        status: Filter by processing_status (default: "processed")
        limit: Maximum results to return (default: 20)
    """
    error = config.validate()
    if error:
        return json.dumps({"error": error}, indent=2)

    if not config.user_email:
        return json.dumps({"error": "Authentication required. No user identity available."}, indent=2)

    parsed_from = None
    parsed_to = None
    if date_from:
        try:
            parsed_from = datetime.fromisoformat(date_from).replace(tzinfo=timezone.utc)
        except ValueError:
            return json.dumps({"error": f"Invalid date_from format: {date_from}"}, indent=2)
    if date_to:
        try:
            parsed_to = datetime.fromisoformat(date_to).replace(tzinfo=timezone.utc)
        except ValueError:
            return json.dumps({"error": f"Invalid date_to format: {date_to}"}, indent=2)

    # Resolve user and load policies
    policies = PolicyEngine.load_policies_from_firestore()
    engine = PolicyEngine(policies=policies)
    user = engine.resolve_user(config.user_email)
    allowed_sensitivity = engine.get_allowed_sensitivity(user)

    # Phase 1: Pre-filter by sensitivity at Firestore level
    # Over-fetch 2x to account for post-filter reductions
    docs = query_documents(
        doc_type=type,
        tags=tags,
        meeting_series=meeting_series,
        date_from=parsed_from,
        date_to=parsed_to,
        status=status,
        limit=limit * 2,
        sensitivity_in=allowed_sensitivity if allowed_sensitivity else None,
    )

    # Phase 2: Post-filter by full policy (categories, participant, feedback subject)
    filtered = engine.filter_results(user, docs)[:limit]

    results = [document_to_json(doc, include_content=False) for doc in filtered]
    return json.dumps({"documents": results, "count": len(results)}, indent=2)
