"""Cloud Function entry point for scheduled Granola meeting notes sync from Google Drive to Firestore."""

import json
import os
import re
import time
from datetime import datetime, timezone

import functions_framework
import yaml
from google.cloud import firestore
from google.oauth2 import service_account
from googleapiclient.discovery import build

DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
COLLECTION = "knowledge_base"
SYNC_METADATA_COLLECTION = "_sync_metadata"
SYNC_METADATA_DOC = "granola_sync"
FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _get_config():
    return {
        "project_id": os.environ["GCP_PROJECT_ID"],
        "folder_id": os.environ["GRANOLA_DRIVE_FOLDER_ID"],
        "owner_email": os.environ.get("GRANOLA_OWNER_EMAIL", ""),
        "firestore_database": os.environ.get("FIRESTORE_DATABASE", "(default)"),
    }


def _get_credentials():
    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if creds_path:
        return service_account.Credentials.from_service_account_file(creds_path, scopes=DRIVE_SCOPES)
    import google.auth
    credentials, _ = google.auth.default(scopes=DRIVE_SCOPES)
    return credentials


def _get_drive_service(credentials):
    return build("drive", "v3", credentials=credentials)


def _get_firestore_client(cfg):
    return firestore.Client(project=cfg["project_id"], database=cfg["firestore_database"])


def _list_markdown_files(drive_service, folder_id):
    results = []
    page_token = None
    while True:
        resp = drive_service.files().list(
            q=f"'{folder_id}' in parents and trashed = false and name contains '.md'",
            fields="nextPageToken, files(id, name)",
            pageSize=1000,
            pageToken=page_token,
        ).execute()
        results.extend(resp.get("files", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return results


def _download_file(drive_service, file_id):
    return drive_service.files().get_media(fileId=file_id).execute().decode("utf-8")


def _parse_frontmatter(content):
    match = FRONTMATTER_PATTERN.match(content)
    if not match:
        return {}, content
    try:
        metadata = yaml.safe_load(match.group(1))
        body = content[match.end():]
        return metadata or {}, body
    except yaml.YAMLError:
        return {}, content


def _document_exists(fs_client, granola_id):
    docs = (
        fs_client.collection(COLLECTION)
        .where("source", "==", "granola")
        .where("source_id", "==", str(granola_id))
        .limit(1)
        .get()
    )
    return len(docs) > 0


def _parse_date(date_value):
    if isinstance(date_value, datetime):
        return date_value.replace(tzinfo=timezone.utc) if date_value.tzinfo is None else date_value
    if isinstance(date_value, str):
        try:
            return datetime.fromisoformat(date_value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


@functions_framework.http
def sync_handler(request):
    start = time.time()
    cfg = _get_config()
    credentials = _get_credentials()
    drive_service = _get_drive_service(credentials)
    fs_client = _get_firestore_client(cfg)

    total_new = 0
    total_skipped = 0
    errors = []

    try:
        files = _list_markdown_files(drive_service, cfg["folder_id"])
    except Exception as e:
        return json.dumps({"status": "error", "error": f"Failed to list Drive files: {e}"}), 500

    for f in files:
        try:
            content = _download_file(drive_service, f["id"])
            metadata, body = _parse_frontmatter(content)

            granola_id = metadata.get("granola_id")
            if not granola_id:
                errors.append(f"{f['name']}: no granola_id in frontmatter")
                continue

            if _document_exists(fs_client, granola_id):
                total_skipped += 1
                continue

            tags = metadata.get("tags", [])
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(",") if t.strip()]

            participants = metadata.get("participants", [])
            if isinstance(participants, str):
                participants = [p.strip() for p in participants.split(",") if p.strip()]

            firestore_doc = {
                "type": "meeting_note",
                "source": "granola",
                "source_id": str(granola_id),
                "source_url": None,
                "title": metadata.get("title", f["name"].replace(".md", "").replace("_", " ")),
                "content": body.strip(),
                "content_format": "markdown",
                "meeting_series": metadata.get("meeting-series"),
                "meeting_date": _parse_date(metadata.get("created_at")),
                "participants": participants if participants else None,
                "tags": tags,
                "area": metadata.get("area"),
                "sensitivity": "unreviewed",
                "processing_status": "raw",
                "owner_email": cfg["owner_email"],
                "synced_at": _now_iso(),
                "created_at": firestore.SERVER_TIMESTAMP,
                "updated_at": firestore.SERVER_TIMESTAMP,
            }

            fs_client.collection(COLLECTION).add(firestore_doc)
            total_new += 1
        except Exception as e:
            errors.append(f"{f['name']}: {e}")

    duration = round(time.time() - start, 1)
    sync_state = {
        "last_sync_at": _now_iso(),
        "files_found": len(files),
        "new_docs_synced": total_new,
        "skipped_existing": total_skipped,
        "errors": errors,
        "duration_seconds": duration,
    }
    try:
        fs_client.collection(SYNC_METADATA_COLLECTION).document(SYNC_METADATA_DOC).set(sync_state)
    except Exception:
        pass

    return json.dumps({
        "status": "completed",
        "files_found": len(files),
        "new_docs_synced": total_new,
        "skipped_existing": total_skipped,
        "errors": errors,
        "duration_seconds": duration,
    }), 200
