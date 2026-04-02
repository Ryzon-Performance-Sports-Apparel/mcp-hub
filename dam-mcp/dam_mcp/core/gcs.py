"""GCS client wrapper — single point of interaction with Google Cloud Storage."""

import datetime
import json as _json

from google.cloud import storage

from .config import config
from .utils import logger

_client: storage.Client | None = None
_bucket: storage.Bucket | None = None

DAM_META_PREFIX = "dam_"


def get_client() -> storage.Client:
    global _client
    if _client is None:
        _client = storage.Client(project=config.gcp_project_id)
        logger.info(f"GCS client created for project {config.gcp_project_id}")
    return _client


def get_bucket() -> storage.Bucket:
    global _bucket
    if _bucket is None:
        _bucket = get_client().bucket(config.gcs_bucket_name)
        logger.info(f"Using GCS bucket: {config.gcs_bucket_name}")
    return _bucket


def list_blobs(
    prefix: str = "",
    max_results: int = 50,
    page_token: str | None = None,
    delimiter: str | None = None,
) -> tuple[list[storage.Blob], str | None]:
    """List blobs with optional prefix filtering and pagination.

    Returns (blobs, next_page_token).
    """
    bucket = get_bucket()
    iterator = bucket.list_blobs(
        prefix=prefix or None,
        max_results=max_results,
        page_token=page_token,
        delimiter=delimiter,
    )
    pages = iterator.pages
    page = next(pages, None)
    blobs = list(page) if page else []
    next_token = iterator.next_page_token
    return blobs, next_token


def get_blob(blob_name: str) -> storage.Blob | None:
    """Get a blob by name, returning None if it doesn't exist."""
    bucket = get_bucket()
    blob = bucket.blob(blob_name)
    if blob.exists():
        blob.reload()
        return blob
    return None


def get_blob_metadata(blob_name: str) -> dict | None:
    """Get custom metadata for a blob."""
    blob = get_blob(blob_name)
    if blob is None:
        return None
    return blob.metadata or {}


def set_blob_metadata(blob_name: str, metadata: dict) -> bool:
    """Update custom metadata on a blob. Merges with existing metadata."""
    blob = get_blob(blob_name)
    if blob is None:
        return False
    existing = blob.metadata or {}
    existing.update(metadata)
    blob.metadata = existing
    blob.patch()
    return True


def upload_blob(
    blob_name: str,
    data: bytes,
    content_type: str,
    metadata: dict | None = None,
) -> storage.Blob:
    """Upload bytes to GCS with optional custom metadata."""
    bucket = get_bucket()
    blob = bucket.blob(blob_name)
    blob.upload_from_string(data, content_type=content_type)
    if metadata:
        blob.metadata = metadata
        blob.patch()
    logger.info(f"Uploaded {blob_name} ({len(data)} bytes, {content_type})")
    return blob


def generate_signed_url(blob_name: str, expiry_minutes: int | None = None) -> str:
    """Generate a V4 signed URL for downloading a blob.

    When running on Cloud Run (no key file), uses IAM Credentials API
    for signing via the service account's signBlob permission.
    """
    import os

    import google.auth

    if expiry_minutes is None:
        expiry_minutes = config.signed_url_expiry_minutes
    bucket = get_bucket()
    blob = bucket.blob(blob_name)

    if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        # Local dev: use key file directly
        url = blob.generate_signed_url(
            version="v4",
            expiration=datetime.timedelta(minutes=expiry_minutes),
            method="GET",
        )
    else:
        # Cloud Run: use IAM Credentials API for signing
        credentials, _ = google.auth.default()
        url = blob.generate_signed_url(
            version="v4",
            expiration=datetime.timedelta(minutes=expiry_minutes),
            method="GET",
            credentials=credentials,
            service_account_email=credentials.service_account_email,
        )
    return url


def blob_to_metadata_dict(blob: storage.Blob) -> dict:
    """Convert a GCS blob to a standard metadata dictionary."""
    custom = blob.metadata or {}
    return {
        "asset_id": blob.name,
        "name": custom.get(f"{DAM_META_PREFIX}original_filename", blob.name.split("/")[-1]),
        "content_type": blob.content_type,
        "size_bytes": blob.size,
        "created_at": custom.get(f"{DAM_META_PREFIX}created_at", ""),
        "updated_at": blob.updated.isoformat() if blob.updated else "",
        "tags": [t.strip() for t in custom.get(f"{DAM_META_PREFIX}tags", "").split(",") if t.strip()],
        "campaign": custom.get(f"{DAM_META_PREFIX}campaign", ""),
        "width": int(custom.get(f"{DAM_META_PREFIX}width", 0)) or None,
        "height": int(custom.get(f"{DAM_META_PREFIX}height", 0)) or None,
        "upload_source": custom.get(f"{DAM_META_PREFIX}upload_source", ""),
    }


def search_blobs(
    query: str = "",
    tags: list[str] | None = None,
    format: str | None = None,
    campaign: str | None = None,
    min_width: int | None = None,
    min_height: int | None = None,
    limit: int = 50,
) -> list[dict]:
    """Search blobs by filtering on custom metadata. Phase 1 in-memory filtering."""
    bucket = get_bucket()
    results = []
    for blob in bucket.list_blobs():
        if len(results) >= limit:
            break
        blob.reload()
        meta = blob.metadata or {}

        if query:
            name = meta.get(f"{DAM_META_PREFIX}original_filename", blob.name)
            blob_tags = meta.get(f"{DAM_META_PREFIX}tags", "")
            blob_campaign = meta.get(f"{DAM_META_PREFIX}campaign", "")
            searchable = f"{name} {blob_tags} {blob_campaign}".lower()
            if query.lower() not in searchable:
                continue

        if tags:
            blob_tags = [t.strip().lower() for t in meta.get(f"{DAM_META_PREFIX}tags", "").split(",") if t.strip()]
            if not all(t.lower() in blob_tags for t in tags):
                continue

        if format:
            ct = blob.content_type or ""
            if format.lower() not in ct.lower() and not blob.name.lower().endswith(f".{format.lower()}"):
                continue

        if campaign:
            if campaign.lower() != meta.get(f"{DAM_META_PREFIX}campaign", "").lower():
                continue

        if min_width:
            try:
                w = int(meta.get(f"{DAM_META_PREFIX}width", 0))
                if w < min_width:
                    continue
            except (ValueError, TypeError):
                continue

        if min_height:
            try:
                h = int(meta.get(f"{DAM_META_PREFIX}height", 0))
                if h < min_height:
                    continue
            except (ValueError, TypeError):
                continue

        results.append(blob_to_metadata_dict(blob))

    return results


SYNC_STATE_BLOB = ".dam_sync_state.json"


def find_blob_by_drive_id(drive_file_id: str) -> storage.Blob | None:
    """Find a blob by its Drive file ID in custom metadata."""
    bucket = get_bucket()
    for blob in bucket.list_blobs():
        blob.reload()
        meta = blob.metadata or {}
        if meta.get(f"{DAM_META_PREFIX}drive_file_id") == drive_file_id:
            return blob
    return None


def write_sync_state(state: dict) -> None:
    """Write sync state to a JSON object in GCS."""
    bucket = get_bucket()
    blob = bucket.blob(SYNC_STATE_BLOB)
    blob.upload_from_string(
        _json.dumps(state, indent=2),
        content_type="application/json",
    )


def read_sync_state() -> dict | None:
    """Read sync state from GCS. Returns None if no state exists."""
    bucket = get_bucket()
    blob = bucket.blob(SYNC_STATE_BLOB)
    if not blob.exists():
        return None
    return _json.loads(blob.download_as_text())
