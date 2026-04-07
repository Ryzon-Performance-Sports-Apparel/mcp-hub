"""query_knowledge_base tool — search documents in the Firestore knowledge base."""

import json
from datetime import datetime, timezone
from typing import Optional

from .config import config
from .firestore import document_to_json, query_documents
from .server import mcp_server


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

    docs = query_documents(
        doc_type=type,
        tags=tags,
        meeting_series=meeting_series,
        date_from=parsed_from,
        date_to=parsed_to,
        status=status,
        limit=limit,
    )

    results = [document_to_json(doc, include_content=False) for doc in docs]
    return json.dumps({"documents": results, "count": len(results)}, indent=2)
