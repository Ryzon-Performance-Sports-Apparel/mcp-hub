"""Cloud Function entry point for scheduled meeting notes sync from Google Drive to Firestore."""

import json
import os
import time
from datetime import datetime, timezone

import functions_framework
import gspread
from google.cloud import firestore
from google.oauth2 import service_account
from googleapiclient.discovery import build

DRIVE_SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
]
GOOGLE_DOC_MIME = "application/vnd.google-apps.document"
FOLDER_MIME = "application/vnd.google-apps.folder"

COLLECTION = "knowledge_base"
SYNC_METADATA_COLLECTION = "_sync_metadata"
SYNC_METADATA_DOC = "meeting_notes_sync"


def _get_config():
    return {
        "project_id": os.environ["GCP_PROJECT_ID"],
        "sheet_id": os.environ["CONFIG_SHEET_ID"],
        "sheet_name": os.environ.get("CONFIG_SHEET_NAME", "Sheet1"),
        "firestore_database": os.environ.get("FIRESTORE_DATABASE", "(default)"),
    }


def _get_credentials():
    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if creds_path:
        return service_account.Credentials.from_service_account_file(
            creds_path, scopes=DRIVE_SCOPES
        )
    import google.auth
    credentials, _ = google.auth.default(scopes=DRIVE_SCOPES)
    return credentials


def _get_drive_service(credentials):
    return build("drive", "v3", credentials=credentials)


def _get_firestore_client(cfg):
    return firestore.Client(project=cfg["project_id"], database=cfg["firestore_database"])


def _get_sheets_client(credentials):
    return gspread.authorize(credentials)


def _read_config_sheet(sheets_client, sheet_id, sheet_name):
    """Read the config sheet and return rows as dicts.

    Expected columns: folder_id, owner_email, meeting_series,
    sync_frequency, tags, sharing_confirmed
    """
    spreadsheet = sheets_client.open_by_key(sheet_id)
    worksheet = spreadsheet.worksheet(sheet_name)
    records = worksheet.get_all_records()
    return records, worksheet


def _list_google_docs_in_folder(drive_service, folder_id):
    """List all Google Docs in a folder (non-recursive for meeting notes)."""
    results = []
    page_token = None
    while True:
        resp = drive_service.files().list(
            q=f"'{folder_id}' in parents and trashed = false and mimeType = '{GOOGLE_DOC_MIME}'",
            fields="nextPageToken, files(id, name, createdTime, modifiedTime, webViewLink)",
            pageSize=1000,
            pageToken=page_token,
        ).execute()
        results.extend(resp.get("files", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return results


def _export_google_doc_as_text(drive_service, file_id):
    """Export a Google Doc as plain text."""
    return drive_service.files().export(
        fileId=file_id, mimeType="text/plain"
    ).execute().decode("utf-8")


def _document_exists_in_firestore(fs_client, source_id):
    """Check if a document with this source_id already exists."""
    docs = (
        fs_client.collection(COLLECTION)
        .where("source", "==", "google_drive")
        .where("source_id", "==", source_id)
        .limit(1)
        .get()
    )
    return len(docs) > 0


def _verify_folder_access(drive_service, folder_id):
    """Check if the service account can access a Drive folder."""
    try:
        drive_service.files().get(fileId=folder_id, fields="id,name").execute()
        return True
    except Exception:
        return False


def _update_sharing_confirmed(worksheet, row_index, value):
    """Update the sharing_confirmed column for a row.

    row_index is 1-based (row 1 = header, row 2 = first data row).
    """
    try:
        header = worksheet.row_values(1)
        col_index = header.index("sharing_confirmed") + 1
        worksheet.update_cell(row_index, col_index, str(value).upper())
    except (ValueError, Exception):
        pass


def _parse_tags(tags_str):
    """Parse comma-separated tags string into a list."""
    if not tags_str:
        return []
    return [t.strip() for t in str(tags_str).split(",") if t.strip()]


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


@functions_framework.http
def sync_handler(request):
    """HTTP Cloud Function entry point for meeting notes sync."""
    start = time.time()
    cfg = _get_config()
    credentials = _get_credentials()
    drive_service = _get_drive_service(credentials)
    fs_client = _get_firestore_client(cfg)
    sheets_client = _get_sheets_client(credentials)

    total_new = 0
    total_skipped = 0
    total_errors = []
    folders_checked = 0

    try:
        rows, worksheet = _read_config_sheet(
            sheets_client, cfg["sheet_id"], cfg["sheet_name"]
        )
    except Exception as e:
        return json.dumps({"status": "error", "error": f"Failed to read config sheet: {e}"}), 500

    for i, row in enumerate(rows):
        folder_id = str(row.get("folder_id", "")).strip()
        if not folder_id:
            continue

        owner_email = str(row.get("owner_email", "")).strip()
        meeting_series = str(row.get("meeting_series", "")).strip() or None
        default_tags = _parse_tags(row.get("tags", ""))
        sharing_confirmed = str(row.get("sharing_confirmed", "")).strip().upper()
        row_number = i + 2  # 1-based, row 1 is header

        # Skip folders explicitly marked as not shared
        if sharing_confirmed == "FALSE":
            continue

        # Verify access if not yet confirmed
        if sharing_confirmed != "TRUE":
            has_access = _verify_folder_access(drive_service, folder_id)
            _update_sharing_confirmed(worksheet, row_number, has_access)
            if not has_access:
                total_errors.append(f"folder {folder_id}: service account has no access")
                continue

        folders_checked += 1

        try:
            docs = _list_google_docs_in_folder(drive_service, folder_id)
        except Exception as e:
            total_errors.append(f"folder {folder_id}: failed to list docs: {e}")
            continue

        for doc in docs:
            if _document_exists_in_firestore(fs_client, doc["id"]):
                total_skipped += 1
                continue

            try:
                content = _export_google_doc_as_text(drive_service, doc["id"])
                firestore_doc = {
                    "type": "meeting_note",
                    "source": "google_drive",
                    "source_id": doc["id"],
                    "source_url": doc.get("webViewLink", ""),
                    "title": doc["name"],
                    "content": content,
                    "content_format": "plain_text",
                    "meeting_series": meeting_series,
                    "meeting_date": None,
                    "participants": None,
                    "tags": default_tags,
                    "sensitivity": "unreviewed",
                    "processing_status": "raw",
                    "owner_email": owner_email,
                    "synced_at": _now_iso(),
                    "processed_at": None,
                    "created_at": firestore.SERVER_TIMESTAMP,
                    "updated_at": firestore.SERVER_TIMESTAMP,
                }
                fs_client.collection(COLLECTION).add(firestore_doc)
                total_new += 1
            except Exception as e:
                total_errors.append(f"{doc['name']} ({doc['id']}): {e}")

    duration = round(time.time() - start, 1)

    # Write sync metadata
    sync_state = {
        "last_sync_at": _now_iso(),
        "folders_checked": folders_checked,
        "new_docs_synced": total_new,
        "skipped_existing": total_skipped,
        "errors": total_errors,
        "duration_seconds": duration,
    }
    try:
        fs_client.collection(SYNC_METADATA_COLLECTION).document(SYNC_METADATA_DOC).set(sync_state)
    except Exception:
        pass

    return json.dumps({
        "status": "completed",
        "folders_checked": folders_checked,
        "new_docs_synced": total_new,
        "skipped_existing": total_skipped,
        "errors": total_errors,
        "duration_seconds": duration,
    }), 200
