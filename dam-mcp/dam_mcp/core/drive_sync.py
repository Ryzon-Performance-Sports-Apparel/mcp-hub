"""Google Drive to GCS sync logic."""

import time

from google.oauth2 import service_account
from googleapiclient.discovery import build

from .config import config
from .gcs import (
    DAM_META_PREFIX,
    find_blob_by_drive_id,
    upload_blob,
    write_sync_state,
)
from .utils import logger, now_iso

DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
FOLDER_MIME = "application/vnd.google-apps.folder"

_drive_service = None


def _get_drive_service():
    """Get or create a Google Drive API service client."""
    global _drive_service
    if _drive_service is not None:
        return _drive_service

    import os

    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if creds_path:
        credentials = service_account.Credentials.from_service_account_file(
            creds_path, scopes=DRIVE_SCOPES
        )
    else:
        import google.auth
        credentials, _ = google.auth.default(scopes=DRIVE_SCOPES)

    _drive_service = build("drive", "v3", credentials=credentials)
    return _drive_service


def list_drive_files(folder_id: str, _path_prefix: str = "") -> list[dict]:
    """Recursively list all files in a Drive folder.

    Returns a list of dicts with keys: id, name, path, mimeType.
    Folders are not included in the output — only files.
    """
    service = _get_drive_service()
    results = []
    page_token = None

    while True:
        resp = service.files().list(
            q=f"'{folder_id}' in parents and trashed = false",
            fields="nextPageToken, files(id, name, mimeType, parents)",
            pageSize=1000,
            pageToken=page_token,
        ).execute()

        for item in resp.get("files", []):
            item_path = f"{_path_prefix}{item['name']}" if _path_prefix else item["name"]

            if item["mimeType"] == FOLDER_MIME:
                results.extend(
                    list_drive_files(item["id"], _path_prefix=f"{item_path}/")
                )
            else:
                results.append({
                    "id": item["id"],
                    "name": item["name"],
                    "path": item_path,
                    "mimeType": item["mimeType"],
                })

        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    return results


def _download_drive_file(file_id: str) -> bytes:
    """Download a file's content from Google Drive."""
    service = _get_drive_service()
    return service.files().get_media(fileId=file_id).execute()


def _campaign_from_path(path: str) -> str:
    """Extract campaign name from the first folder in the path."""
    parts = path.split("/")
    return parts[0] if len(parts) > 1 else ""


def sync_drive_to_gcs(folder_id: str) -> dict:
    """Sync files from a Google Drive folder to GCS.

    Returns a summary dict with counts and errors.
    """
    start = time.time()
    errors = []

    logger.info(f"Starting Drive sync from folder {folder_id}")

    try:
        drive_files = list_drive_files(folder_id)
    except Exception as e:
        logger.error(f"Failed to list Drive files: {e}")
        state = {
            "last_sync_at": now_iso(),
            "last_sync_result": "error",
            "files_synced": 0,
            "total_drive_files": 0,
            "errors": [str(e)],
            "duration_seconds": round(time.time() - start, 1),
        }
        try:
            write_sync_state(state)
        except Exception:
            pass
        return state

    new_synced = 0
    skipped = 0

    for f in drive_files:
        existing = find_blob_by_drive_id(f["id"])
        if existing is not None:
            skipped += 1
            continue

        try:
            data = _download_drive_file(f["id"])
            metadata = {
                f"{DAM_META_PREFIX}drive_file_id": f["id"],
                f"{DAM_META_PREFIX}original_filename": f["name"],
                f"{DAM_META_PREFIX}upload_source": "drive_sync",
                f"{DAM_META_PREFIX}campaign": _campaign_from_path(f["path"]),
                f"{DAM_META_PREFIX}created_at": now_iso(),
                f"{DAM_META_PREFIX}tags": "",
            }
            upload_blob(f["path"], data, f["mimeType"], metadata)
            new_synced += 1
            logger.info(f"Synced: {f['path']}")
        except Exception as e:
            error_msg = f"{f['path']}: {e}"
            errors.append(error_msg)
            logger.error(f"Failed to sync {f['path']}: {e}")

    duration = round(time.time() - start, 1)
    state = {
        "last_sync_at": now_iso(),
        "last_sync_result": "completed",
        "files_synced": new_synced,
        "total_drive_files": len(drive_files),
        "errors": errors,
        "duration_seconds": duration,
    }
    write_sync_state(state)

    logger.info(f"Sync complete: {new_synced} new, {skipped} skipped, {len(errors)} errors in {duration}s")
    return {
        "status": "completed",
        "drive_files_found": len(drive_files),
        "new_files_synced": new_synced,
        "skipped_existing": skipped,
        "errors": errors,
        "duration_seconds": duration,
    }
