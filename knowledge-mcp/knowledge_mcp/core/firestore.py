"""Firestore client wrapper for the Knowledge MCP server."""

import json as _json
from datetime import datetime, timezone
from typing import Any

from google.cloud import firestore
from google.cloud.firestore_v1.vector import Vector
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure

from .config import config
from .utils import logger

_client: firestore.Client | None = None

COLLECTION_GENERAL = "knowledge_base"
COLLECTION_RESTRICTED = "knowledge_base_restricted"


def get_client() -> firestore.Client:
    global _client
    if _client is None:
        _client = firestore.Client(
            project=config.gcp_project_id,
            database=config.firestore_database,
        )
        logger.info(
            f"Firestore client created for project {config.gcp_project_id}, "
            f"database {config.firestore_database}"
        )
    return _client


def get_document(
    document_id: str,
    collection: str = COLLECTION_GENERAL,
) -> dict[str, Any] | None:
    client = get_client()
    doc = client.collection(collection).document(document_id).get()
    if not doc.exists:
        return None
    data = doc.to_dict()
    data["id"] = doc.id
    return data


def query_documents(
    collection: str = COLLECTION_GENERAL,
    doc_type: str | None = None,
    tags: list[str] | None = None,
    meeting_series: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    status: str | None = "processed",
    sensitivity_in: list[str] | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    client = get_client()
    query = client.collection(collection)
    if doc_type:
        query = query.where("type", "==", doc_type)
    if tags:
        if len(tags) == 1:
            query = query.where("tags", "array_contains", tags[0])
        else:
            query = query.where("tags", "array_contains_any", tags[:30])
    if meeting_series:
        query = query.where("meeting_series", "==", meeting_series)
    if status:
        query = query.where("processing_status", "==", status)
    if sensitivity_in:
        query = query.where("sensitivity", "in", sensitivity_in)
    if date_from:
        query = query.where("meeting_date", ">=", date_from)
    if date_to:
        query = query.where("meeting_date", "<=", date_to)
    query = query.order_by("created_at", direction=firestore.Query.DESCENDING)
    query = query.limit(limit)
    results = []
    for doc in query.stream():
        data = doc.to_dict()
        data["id"] = doc.id
        results.append(data)
    return results


def vector_search(
    query_embedding: list[float],
    collection: str = COLLECTION_GENERAL,
    doc_type: str | None = None,
    sensitivity_in: list[str] | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    client = get_client()
    query = client.collection(collection).find_nearest(
        vector_field="embedding",
        query_vector=Vector(query_embedding),
        distance_measure=DistanceMeasure.COSINE,
        limit=limit,
    )
    if doc_type:
        query = query.where("type", "==", doc_type)
    if sensitivity_in:
        query = query.where("sensitivity", "in", sensitivity_in)
    results = []
    for doc in query.stream():
        data = doc.to_dict()
        data["id"] = doc.id
        data.pop("embedding", None)
        results.append(data)
    return results


def _serialize_for_json(obj: Any) -> Any:
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _serialize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize_for_json(v) for v in obj]
    return obj


def document_to_json(doc: dict[str, Any], include_content: bool = True) -> dict:
    result = _serialize_for_json(doc)
    if not include_content and "content" in result:
        content = result["content"] or ""
        if len(content) > 500:
            result["content_preview"] = content[:500] + "..."
            del result["content"]
        else:
            result["content_preview"] = content
            del result["content"]
    return result
