"""search_knowledge_base_semantic tool — vector-based semantic search."""

import json
import os
from typing import Optional

from .config import config
from .firestore import document_to_json, vector_search
from .server import mcp_server


def _get_voyage_client():
    api_key = os.environ.get("VOYAGE_API_KEY")
    if not api_key:
        return None
    import voyageai
    return voyageai.Client(api_key=api_key)


@mcp_server.tool()
async def search_knowledge_base_semantic(
    query: str,
    type: Optional[str] = None,
    limit: int = 10,
) -> str:
    """Search the knowledge base using natural language semantic similarity.

    Generates a vector embedding for your query and finds the most similar
    documents using Firestore vector search. More powerful than tag-based
    search for finding conceptually related content.

    Args:
        query: Natural language search query
        type: Optional document type filter (e.g. "meeting_note")
        limit: Maximum results to return (default: 10)
    """
    error = config.validate()
    if error:
        return json.dumps({"error": error}, indent=2)

    voyage_client = _get_voyage_client()
    if voyage_client is None:
        return json.dumps({"error": "VOYAGE_API_KEY not configured — semantic search unavailable"}, indent=2)

    try:
        result = voyage_client.embed(
            texts=[query],
            model="voyage-3-lite",
            input_type="query",
        )
        query_embedding = result.embeddings[0]
    except Exception as e:
        return json.dumps({"error": f"Embedding generation failed: {e}"}, indent=2)

    docs = vector_search(
        query_embedding=query_embedding,
        doc_type=type,
        limit=limit,
    )

    results = [document_to_json(doc, include_content=False) for doc in docs]
    return json.dumps({"documents": results, "count": len(results)}, indent=2)
