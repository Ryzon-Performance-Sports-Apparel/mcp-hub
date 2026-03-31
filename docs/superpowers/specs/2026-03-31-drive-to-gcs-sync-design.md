# Google Drive → GCS Sync Design

**Date:** 2026-03-31
**Status:** Approved — ready for implementation

## Problem

Designers upload creative assets to Google Drive in campaign-based folders. The dam-mcp server stores and serves assets from GCS. Currently, assets must be manually uploaded via the `upload_asset` tool. There is no automated bridge between Drive and GCS.

## Solution

Additive, one-way sync from a Google Drive folder tree to the `ryzon-dam` GCS bucket. The sync logic lives in dam-mcp as a reusable module, callable both via an MCP tool (on-demand) and a Cloud Function (hourly schedule).

## Architecture

```
Google Drive (shared folder, nested by campaign)
  e.g., /Creatives/Summer-2026/hero.png
                   /Product-Launch/banner.jpg
      |
      | (Drive API: list + download)
      v
drive_sync.py (sync module in dam-mcp)
      |
      | (GCS API: upload with metadata)
      v
gs://ryzon-dam/Summer-2026/hero.png
               /Product-Launch/banner.jpg
```

**Two entry points to the same sync logic:**

1. **MCP tool `trigger_sync`** — on-demand, called by LLM or user
2. **Cloud Function** — hourly via Cloud Scheduler

## Sync Logic (`dam_mcp/core/drive_sync.py`)

### Algorithm

1. List all files in the configured Drive folder recursively (respecting folder hierarchy)
2. For each file:
   a. Compute the GCS blob name from the Drive folder path (e.g., `Summer-2026/hero.png`)
   b. Check if a blob with matching `dam_drive_file_id` already exists in GCS
   c. If not found: download from Drive, upload to GCS with metadata
   d. If found: skip (additive only, no updates)
3. Return summary: total files in Drive, new files synced, skipped, errors

### Metadata on synced assets

| Key | Value | Example |
|-----|-------|---------|
| `dam_drive_file_id` | Google Drive file ID | `1a2b3c4d5e6f` |
| `dam_original_filename` | Original filename from Drive | `hero.png` |
| `dam_upload_source` | Always `drive_sync` | `drive_sync` |
| `dam_campaign` | Parent folder name in Drive | `Summer-2026` |
| `dam_created_at` | ISO timestamp of sync | `2026-03-31T14:00:00+00:00` |
| `dam_tags` | Empty (user can add via `tag_asset` later) | `` |

### Tracking synced files

Each synced GCS object has `dam_drive_file_id` set to the Drive file's unique ID. Before syncing a file, the module checks if any blob in the bucket already has that Drive ID. This prevents duplicates even if the file is moved or renamed in Drive.

For Phase 1, this check iterates existing blobs. If the bucket grows past ~10K files, a Firestore index would replace this (Phase 3).

### Deletions

Not handled. If a file is removed from Drive, it stays in GCS. GCS is the archive.

## MCP Tools

### `trigger_sync`

```
trigger_sync(folder_id: Optional[str] = None) -> str
```

Runs the sync immediately. Uses `GDRIVE_FOLDER_ID` env var if `folder_id` not provided. Returns JSON:

```json
{
  "status": "completed",
  "drive_files_found": 42,
  "new_files_synced": 5,
  "skipped_existing": 37,
  "errors": [],
  "duration_seconds": 12.3
}
```

### `sync_status`

```
sync_status() -> str
```

Reports the last sync run. Reads from a metadata object at `gs://ryzon-dam/.dam_sync_state.json`:

```json
{
  "last_sync_at": "2026-03-31T14:00:00+00:00",
  "last_sync_result": "completed",
  "files_synced": 5,
  "total_drive_files": 42,
  "errors": []
}
```

## Cloud Function

### Location

```
dam-mcp/cloud_functions/drive_sync/
  main.py          # Cloud Function entry point, imports drive_sync module
  requirements.txt # google-cloud-storage, google-api-python-client, google-auth
```

### Entry point

`main.py` defines an HTTP function that:
1. Imports and calls the sync logic from `dam_mcp.core.drive_sync`
2. Returns the sync summary as JSON
3. Authenticated via IAM (Cloud Scheduler uses OIDC token)

### Deployment

```bash
gcloud functions deploy drive-sync \
  --gen2 \
  --runtime=python312 \
  --region=europe-west3 \
  --source=dam-mcp/cloud_functions/drive_sync/ \
  --entry-point=sync_handler \
  --service-account=dam-mcp@gold-blueprint-357814.iam.gserviceaccount.com \
  --set-env-vars=GCP_PROJECT_ID=gold-blueprint-357814,GCS_BUCKET_NAME=ryzon-dam,GDRIVE_FOLDER_ID=<folder-id> \
  --trigger-http \
  --no-allow-unauthenticated \
  --timeout=300 \
  --memory=256Mi
```

### Cloud Scheduler

```bash
gcloud scheduler jobs create http drive-sync-hourly \
  --location=europe-west3 \
  --schedule="0 * * * *" \
  --uri=<cloud-function-url> \
  --oidc-service-account-email=dam-mcp@gold-blueprint-357814.iam.gserviceaccount.com \
  --http-method=POST
```

## Authentication & Permissions

### Service account: `dam-mcp@gold-blueprint-357814.iam.gserviceaccount.com`

Already has:
- `roles/storage.objectAdmin` on `gs://ryzon-dam`
- `roles/iam.serviceAccountTokenCreator` (for signed URLs)

Needs added:
- **Google Drive API** enabled on the GCP project
- The Drive folder shared with the service account email (Viewer access)
- `roles/cloudfunctions.invoker` (if using Cloud Scheduler → Cloud Function)

### Drive folder sharing

The target Drive folder must be shared with `dam-mcp@gold-blueprint-357814.iam.gserviceaccount.com` as a Viewer. This gives the service account read access to list and download files.

## Dependencies

New Python dependencies for dam-mcp:
- `google-api-python-client>=2.0.0` — Google Drive API client
- `google-auth-httplib2>=0.2.0` — Auth transport for Drive API

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GDRIVE_FOLDER_ID` | Yes (for sync) | Google Drive folder ID to sync from |
| `GCP_PROJECT_ID` | Yes | Already configured |
| `GCS_BUCKET_NAME` | Yes | Already configured |
| `GOOGLE_APPLICATION_CREDENTIALS` | Yes | Already configured |

## Error Handling

- Individual file download failures don't stop the sync — they're logged and included in the errors array
- If Drive API is unreachable, the sync fails fast with a clear error message
- Sync state is written to GCS after every run (success or failure)

## Testing

- Unit tests: mock Drive API responses and GCS operations, verify sync logic (new files copied, existing skipped, metadata set correctly)
- Integration test (e2e): requires a test Drive folder with known files and the `ryzon-dam` bucket

## Files to create/modify

**New:**
- `dam_mcp/core/drive_sync.py` — sync logic module
- `dam_mcp/core/tools_trigger_sync.py` — `trigger_sync` MCP tool
- `dam-mcp/cloud_functions/drive_sync/main.py` — Cloud Function entry point
- `dam-mcp/cloud_functions/drive_sync/requirements.txt`
- `tests/test_drive_sync.py` — unit tests for sync logic
- `tests/test_trigger_sync.py` — unit tests for MCP tool

**Modified:**
- `dam_mcp/core/__init__.py` — import new tool modules
- `dam_mcp/core/tools_sync.py` — replace stub with real implementation reading sync state
- `pyproject.toml` — add Drive API dependencies
