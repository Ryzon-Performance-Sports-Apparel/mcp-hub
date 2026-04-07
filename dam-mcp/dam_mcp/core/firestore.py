"""Firestore client wrapper — single point of interaction with Google Cloud Firestore."""

import json as _json
from datetime import datetime, timezone
from typing import Any

from google.cloud import firestore

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


def write_document(
    data: dict[str, Any],
    collection: str = COLLECTION_GENERAL,
    document_id: str | None = None,
) -> str:
    """Write a document to Firestore. Returns the document ID.

    If document_id is None, Firestore auto-generates one.
    Server timestamps are added for created_at and updated_at.
    """
    client = get_client()
    col_ref = client.collection(collection)

    data["updated_at"] = firestore.SERVER_TIMESTAMP
    if "created_at" not in data:
        data["created_at"] = firestore.SERVER_TIMESTAMP

    if document_id:
        col_ref.document(document_id).set(data)
        logger.info(f"Wrote document {document_id} to {collection}")
        return document_id
    else:
        _, doc_ref = col_ref.add(data)
        logger.info(f"Wrote document {doc_ref.id} to {collection}")
        return doc_ref.id


def get_document(
    document_id: str,
    collection: str = COLLECTION_GENERAL,
) -> dict[str, Any] | None:
    """Get a single document by ID. Returns None if not found."""
    client = get_client()
    doc = client.collection(collection).document(document_id).get()
    if not doc.exists:
        return None
    data = doc.to_dict()
    data["id"] = doc.id
    return data


def update_document(
    document_id: str,
    updates: dict[str, Any],
    collection: str = COLLECTION_GENERAL,
) -> bool:
    """Update specific fields on an existing document."""
    client = get_client()
    doc_ref = client.collection(collection).document(document_id)
    doc = doc_ref.get()
    if not doc.exists:
        return False
    updates["updated_at"] = firestore.SERVER_TIMESTAMP
    doc_ref.update(updates)
    logger.info(f"Updated document {document_id} in {collection}")
    return True


def document_exists(
    source: str,
    source_id: str,
    collection: str = COLLECTION_GENERAL,
) -> bool:
    """Check if a document with the given source and source_id already exists."""
    client = get_client()
    docs = (
        client.collection(collection)
        .where("source", "==", source)
        .where("source_id", "==", source_id)
        .limit(1)
        .get()
    )
    return len(docs) > 0


def query_documents(
    collection: str = COLLECTION_GENERAL,
    doc_type: str | None = None,
    tags: list[str] | None = None,
    meeting_series: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    status: str | None = "processed",
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Query documents with optional filters.

    Note: Firestore array-contains-any supports up to 30 values.
    For tags, we use array-contains for a single tag or
    array-contains-any for multiple tags.
    """
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


def _serialize_for_json(obj: Any) -> Any:
    """Convert Firestore types to JSON-serializable types."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _serialize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize_for_json(v) for v in obj]
    return obj


def document_to_json(doc: dict[str, Any], include_content: bool = True) -> dict:
    """Convert a Firestore document dict to a JSON-safe dict.

    If include_content is False, truncates content to a preview.
    """
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
