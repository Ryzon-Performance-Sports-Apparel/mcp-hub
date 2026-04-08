# Drive-to-GCS Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automatically sync creative assets from Google Drive to GCS, callable on-demand via MCP tool and scheduled hourly via Cloud Function.

**Architecture:** A `drive_sync.py` module handles all sync logic (list Drive, diff against GCS, copy new files). Two entry points share this module: an MCP tool (`trigger_sync`) for on-demand use, and a Cloud Function for hourly scheduled runs. Sync state is persisted as a JSON object in GCS.

**Tech Stack:** google-api-python-client (Drive API), google-cloud-storage (GCS), google-auth, Cloud Functions gen2, Cloud Scheduler

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `dam_mcp/core/drive_sync.py` | Create | Core sync logic: list Drive files, diff against GCS, copy new files, save sync state |
| `dam_mcp/core/tools_trigger_sync.py` | Create | `trigger_sync` MCP tool — on-demand entry point |
| `dam_mcp/core/tools_sync.py` | Rewrite | `sync_status` MCP tool — reads sync state from GCS |
| `dam_mcp/core/__init__.py` | Modify | Add import for `tools_trigger_sync` |
| `dam_mcp/core/gcs.py` | Modify | Add `find_blob_by_drive_id()` and `upload_sync_state()` / `read_sync_state()` |
| `pyproject.toml` | Modify | Add `google-api-python-client` and `google-auth-httplib2` deps |
| `cloud_functions/drive_sync/main.py` | Create | Cloud Function HTTP entry point |
| `cloud_functions/drive_sync/requirements.txt` | Create | Cloud Function dependencies |
| `tests/test_drive_sync.py` | Create | Unit tests for sync logic |
| `tests/test_trigger_sync.py` | Create | Unit tests for trigger_sync MCP tool |
| `tests/test_sync_status.py` | Create | Unit tests for updated sync_status tool |

---

### Task 1: Add Drive API dependencies

**Files:**
- Modify: `dam-mcp/pyproject.toml:17-25`

- [ ] **Step 1: Add dependencies to pyproject.toml**

In `pyproject.toml`, replace the dependencies list:

```toml
dependencies = [
    "mcp[cli]>=1.12.0",
    "google-cloud-storage>=2.0.0",
    "google-auth>=2.0.0",
    "google-api-python-client>=2.0.0",
    "google-auth-httplib2>=0.2.0",
    "httpx>=0.26.0",
    "python-dotenv>=1.1.0",
    "pytest>=8.4.1",
    "pytest-asyncio>=1.0.0",
]
```

- [ ] **Step 2: Install updated deps**

Run: `cd /Users/simonheinken/Documents/projects/meta/mcp/dam-mcp && source .venv/bin/activate && pip install -e .`
Expected: installs `google-api-python-client` and `google-auth-httplib2` successfully

- [ ] **Step 3: Verify import works**

Run: `source .venv/bin/activate && python -c "from googleapiclient.discovery import build; print('Drive API client available')"`
Expected: `Drive API client available`

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "Add Google Drive API dependencies for sync feature"
```

---

### Task 2: Add GCS helper functions for sync state

**Files:**
- Modify: `dam-mcp/dam_mcp/core/gcs.py`
- Create: `dam-mcp/tests/test_sync_state_gcs.py`

- [ ] **Step 1: Write failing tests for sync state helpers**

Create `tests/test_sync_state_gcs.py`:

```python
"""Tests for GCS sync state helpers."""

import json
import pytest
from unittest.mock import MagicMock, patch

from dam_mcp.core.gcs import (
    find_blob_by_drive_id,
    read_sync_state,
    write_sync_state,
    SYNC_STATE_BLOB,
)


def test_find_blob_by_drive_id_found():
    mock_bucket = MagicMock()
    blob = MagicMock()
    blob.metadata = {"dam_drive_file_id": "drive123"}
    blob.reload = MagicMock()
    mock_bucket.list_blobs.return_value = [blob]

    with patch("dam_mcp.core.gcs.get_bucket", return_value=mock_bucket):
        result = find_blob_by_drive_id("drive123")
        assert result is blob


def test_find_blob_by_drive_id_not_found():
    mock_bucket = MagicMock()
    blob = MagicMock()
    blob.metadata = {"dam_drive_file_id": "other_id"}
    blob.reload = MagicMock()
    mock_bucket.list_blobs.return_value = [blob]

    with patch("dam_mcp.core.gcs.get_bucket", return_value=mock_bucket):
        result = find_blob_by_drive_id("drive123")
        assert result is None


def test_write_sync_state():
    mock_bucket = MagicMock()
    mock_blob = MagicMock()
    mock_bucket.blob.return_value = mock_blob

    state = {"last_sync_at": "2026-03-31T14:00:00+00:00", "files_synced": 5}

    with patch("dam_mcp.core.gcs.get_bucket", return_value=mock_bucket):
        write_sync_state(state)
        mock_bucket.blob.assert_called_once_with(SYNC_STATE_BLOB)
        mock_blob.upload_from_string.assert_called_once()
        uploaded_data = mock_blob.upload_from_string.call_args[0][0]
        assert json.loads(uploaded_data)["files_synced"] == 5


def test_read_sync_state_exists():
    mock_bucket = MagicMock()
    mock_blob = MagicMock()
    mock_blob.exists.return_value = True
    mock_blob.download_as_text.return_value = '{"last_sync_at": "2026-03-31T14:00:00+00:00"}'
    mock_bucket.blob.return_value = mock_blob

    with patch("dam_mcp.core.gcs.get_bucket", return_value=mock_bucket):
        result = read_sync_state()
        assert result["last_sync_at"] == "2026-03-31T14:00:00+00:00"


def test_read_sync_state_not_exists():
    mock_bucket = MagicMock()
    mock_blob = MagicMock()
    mock_blob.exists.return_value = False
    mock_bucket.blob.return_value = mock_blob

    with patch("dam_mcp.core.gcs.get_bucket", return_value=mock_bucket):
        result = read_sync_state()
        assert result is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `source .venv/bin/activate && python -m pytest tests/test_sync_state_gcs.py -v`
Expected: FAIL — `ImportError: cannot import name 'find_blob_by_drive_id'`

- [ ] **Step 3: Implement the helper functions**

Add to the end of `dam_mcp/core/gcs.py`:

```python
import json as _json

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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `source .venv/bin/activate && python -m pytest tests/test_sync_state_gcs.py -v`
Expected: 5 passed

- [ ] **Step 5: Run full test suite to check for regressions**

Run: `source .venv/bin/activate && python -m pytest tests/ -v`
Expected: all tests pass (22 existing + 5 new = 27)

- [ ] **Step 6: Commit**

```bash
git add dam_mcp/core/gcs.py tests/test_sync_state_gcs.py
git commit -m "Add GCS helpers for sync state and Drive file ID lookup"
```

---

### Task 3: Implement drive_sync module

**Files:**
- Create: `dam-mcp/dam_mcp/core/drive_sync.py`
- Create: `dam-mcp/tests/test_drive_sync.py`

- [ ] **Step 1: Write failing tests for sync logic**

Create `tests/test_drive_sync.py`:

```python
"""Tests for Drive-to-GCS sync logic."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from dam_mcp.core.drive_sync import list_drive_files, sync_drive_to_gcs


def _mock_drive_service(files):
    """Create a mock Drive API service that returns the given files."""
    service = MagicMock()
    list_req = MagicMock()
    list_req.execute.return_value = {"files": files, "nextPageToken": None}
    service.files.return_value.list.return_value = list_req
    return service


def test_list_drive_files_flat():
    files = [
        {"id": "f1", "name": "hero.png", "mimeType": "image/png", "parents": ["root"]},
        {"id": "f2", "name": "banner.jpg", "mimeType": "image/jpeg", "parents": ["root"]},
    ]
    service = _mock_drive_service(files)

    with patch("dam_mcp.core.drive_sync._get_drive_service", return_value=service):
        result = list_drive_files("root_folder_id")
        assert len(result) == 2
        assert result[0]["id"] == "f1"
        assert result[0]["path"] == "hero.png"


def test_list_drive_files_nested():
    # First call returns a subfolder + a file
    folder_and_file = [
        {"id": "folder1", "name": "Summer-2026", "mimeType": "application/vnd.google-apps.folder", "parents": ["root"]},
        {"id": "f1", "name": "logo.png", "mimeType": "image/png", "parents": ["root"]},
    ]
    # Second call (for subfolder) returns a file
    subfolder_files = [
        {"id": "f2", "name": "hero.png", "mimeType": "image/png", "parents": ["folder1"]},
    ]

    service = MagicMock()
    list_mock = service.files.return_value.list

    call_count = {"n": 0}
    def side_effect(**kwargs):
        req = MagicMock()
        if call_count["n"] == 0:
            req.execute.return_value = {"files": folder_and_file}
        else:
            req.execute.return_value = {"files": subfolder_files}
        call_count["n"] += 1
        return req
    list_mock.side_effect = side_effect

    with patch("dam_mcp.core.drive_sync._get_drive_service", return_value=service):
        result = list_drive_files("root_folder_id")
        paths = [f["path"] for f in result]
        assert "logo.png" in paths
        assert "Summer-2026/hero.png" in paths


def test_sync_drive_to_gcs_new_file():
    drive_files = [
        {"id": "f1", "name": "hero.png", "path": "Summer-2026/hero.png", "mimeType": "image/png"},
    ]

    service = MagicMock()
    get_media = MagicMock()
    get_media.execute.return_value = b"fake-image-data"
    service.files.return_value.get_media.return_value = get_media

    with patch("dam_mcp.core.drive_sync._get_drive_service", return_value=service), \
         patch("dam_mcp.core.drive_sync.list_drive_files", return_value=drive_files), \
         patch("dam_mcp.core.drive_sync.find_blob_by_drive_id", return_value=None), \
         patch("dam_mcp.core.drive_sync.upload_blob") as mock_upload, \
         patch("dam_mcp.core.drive_sync.write_sync_state"):

        mock_blob = MagicMock()
        mock_blob.reload = MagicMock()
        mock_upload.return_value = mock_blob

        result = sync_drive_to_gcs("root_folder_id")
        assert result["new_files_synced"] == 1
        assert result["skipped_existing"] == 0
        mock_upload.assert_called_once()
        blob_name = mock_upload.call_args[0][0]
        assert blob_name == "Summer-2026/hero.png"


def test_sync_drive_to_gcs_skips_existing():
    drive_files = [
        {"id": "f1", "name": "hero.png", "path": "Summer-2026/hero.png", "mimeType": "image/png"},
    ]

    existing_blob = MagicMock()

    with patch("dam_mcp.core.drive_sync._get_drive_service", return_value=MagicMock()), \
         patch("dam_mcp.core.drive_sync.list_drive_files", return_value=drive_files), \
         patch("dam_mcp.core.drive_sync.find_blob_by_drive_id", return_value=existing_blob), \
         patch("dam_mcp.core.drive_sync.upload_blob") as mock_upload, \
         patch("dam_mcp.core.drive_sync.write_sync_state"):

        result = sync_drive_to_gcs("root_folder_id")
        assert result["new_files_synced"] == 0
        assert result["skipped_existing"] == 1
        mock_upload.assert_not_called()


def test_sync_drive_to_gcs_handles_download_error():
    drive_files = [
        {"id": "f1", "name": "hero.png", "path": "Summer-2026/hero.png", "mimeType": "image/png"},
    ]

    service = MagicMock()
    service.files.return_value.get_media.return_value.execute.side_effect = Exception("Download failed")

    with patch("dam_mcp.core.drive_sync._get_drive_service", return_value=service), \
         patch("dam_mcp.core.drive_sync.list_drive_files", return_value=drive_files), \
         patch("dam_mcp.core.drive_sync.find_blob_by_drive_id", return_value=None), \
         patch("dam_mcp.core.drive_sync.write_sync_state"):

        result = sync_drive_to_gcs("root_folder_id")
        assert result["new_files_synced"] == 0
        assert len(result["errors"]) == 1
        assert "hero.png" in result["errors"][0]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `source .venv/bin/activate && python -m pytest tests/test_drive_sync.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'dam_mcp.core.drive_sync'`

- [ ] **Step 3: Implement drive_sync.py**

Create `dam_mcp/core/drive_sync.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `source .venv/bin/activate && python -m pytest tests/test_drive_sync.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add dam_mcp/core/drive_sync.py tests/test_drive_sync.py
git commit -m "Add Drive-to-GCS sync logic module"
```

---

### Task 4: Implement trigger_sync MCP tool

**Files:**
- Create: `dam-mcp/dam_mcp/core/tools_trigger_sync.py`
- Create: `dam-mcp/tests/test_trigger_sync.py`
- Modify: `dam-mcp/dam_mcp/core/__init__.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_trigger_sync.py`:

```python
"""Tests for trigger_sync MCP tool."""

import json
import pytest
from unittest.mock import patch

from dam_mcp.core.tools_trigger_sync import trigger_sync


@pytest.mark.asyncio
async def test_trigger_sync_success():
    sync_result = {
        "status": "completed",
        "drive_files_found": 10,
        "new_files_synced": 3,
        "skipped_existing": 7,
        "errors": [],
        "duration_seconds": 5.2,
    }

    with patch("dam_mcp.core.tools_trigger_sync.sync_drive_to_gcs", return_value=sync_result):
        result = await trigger_sync(folder_id="test_folder_123")
        data = json.loads(result)
        assert data["status"] == "completed"
        assert data["new_files_synced"] == 3


@pytest.mark.asyncio
async def test_trigger_sync_uses_config_folder_id(mock_config):
    mock_config.gdrive_folder_id = "config_folder_456"
    sync_result = {
        "status": "completed",
        "drive_files_found": 0,
        "new_files_synced": 0,
        "skipped_existing": 0,
        "errors": [],
        "duration_seconds": 0.1,
    }

    with patch("dam_mcp.core.tools_trigger_sync.sync_drive_to_gcs", return_value=sync_result) as mock_sync:
        await trigger_sync()
        mock_sync.assert_called_once_with("config_folder_456")


@pytest.mark.asyncio
async def test_trigger_sync_no_folder_id(mock_config):
    mock_config.gdrive_folder_id = ""
    result = await trigger_sync()
    data = json.loads(result)
    assert "error" in data
    assert "GDRIVE_FOLDER_ID" in data["error"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `source .venv/bin/activate && python -m pytest tests/test_trigger_sync.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement trigger_sync tool**

Create `dam_mcp/core/tools_trigger_sync.py`:

```python
"""trigger_sync tool — on-demand Drive-to-GCS sync."""

import json
from typing import Optional

from .config import config
from .drive_sync import sync_drive_to_gcs
from .server import mcp_server


@mcp_server.tool()
async def trigger_sync(folder_id: Optional[str] = None) -> str:
    """Trigger a Google Drive to GCS sync immediately.

    Syncs all new files from the configured Drive folder to the GCS bucket.
    Files already synced (tracked by Drive file ID) are skipped.

    Args:
        folder_id: Google Drive folder ID to sync from. Uses GDRIVE_FOLDER_ID env var if not provided.
    """
    error = config.validate()
    if error:
        return json.dumps({"error": error}, indent=2)

    target_folder = folder_id or config.gdrive_folder_id
    if not target_folder:
        return json.dumps(
            {"error": "No folder ID provided. Set GDRIVE_FOLDER_ID or pass folder_id parameter."},
            indent=2,
        )

    result = sync_drive_to_gcs(target_folder)
    return json.dumps(result, indent=2)
```

- [ ] **Step 4: Register the tool in __init__.py**

In `dam_mcp/core/__init__.py`, add this import after the `tools_sync` import:

```python
from .tools_trigger_sync import trigger_sync
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `source .venv/bin/activate && python -m pytest tests/test_trigger_sync.py -v`
Expected: 3 passed

- [ ] **Step 6: Commit**

```bash
git add dam_mcp/core/tools_trigger_sync.py dam_mcp/core/__init__.py tests/test_trigger_sync.py
git commit -m "Add trigger_sync MCP tool for on-demand Drive sync"
```

---

### Task 5: Replace sync_status stub with real implementation

**Files:**
- Rewrite: `dam-mcp/dam_mcp/core/tools_sync.py`
- Create: `dam-mcp/tests/test_sync_status.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_sync_status.py`:

```python
"""Tests for sync_status MCP tool."""

import json
import pytest
from unittest.mock import patch

from dam_mcp.core.tools_sync import sync_status


@pytest.mark.asyncio
async def test_sync_status_with_state():
    state = {
        "last_sync_at": "2026-03-31T14:00:00+00:00",
        "last_sync_result": "completed",
        "files_synced": 5,
        "total_drive_files": 42,
        "errors": [],
    }

    with patch("dam_mcp.core.tools_sync.read_sync_state", return_value=state):
        result = await sync_status()
        data = json.loads(result)
        assert data["last_sync_at"] == "2026-03-31T14:00:00+00:00"
        assert data["files_synced"] == 5
        assert data["status"] == "completed"


@pytest.mark.asyncio
async def test_sync_status_no_state():
    with patch("dam_mcp.core.tools_sync.read_sync_state", return_value=None):
        result = await sync_status()
        data = json.loads(result)
        assert data["status"] == "never_synced"
        assert "trigger_sync" in data["message"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `source .venv/bin/activate && python -m pytest tests/test_sync_status.py -v`
Expected: FAIL — the current stub doesn't call `read_sync_state`

- [ ] **Step 3: Rewrite tools_sync.py**

Replace `dam_mcp/core/tools_sync.py` with:

```python
"""sync_status tool — report last Drive-to-GCS sync status."""

import json

from .gcs import read_sync_state
from .server import mcp_server


@mcp_server.tool()
async def sync_status() -> str:
    """Check the status of the last Google Drive to GCS sync.

    Reports when the last sync ran, how many files were synced,
    and any errors that occurred.
    """
    state = read_sync_state()

    if state is None:
        return json.dumps(
            {
                "status": "never_synced",
                "message": "No sync has been run yet. Use trigger_sync to start one.",
            },
            indent=2,
        )

    return json.dumps(
        {
            "status": state.get("last_sync_result", "unknown"),
            "last_sync_at": state.get("last_sync_at", ""),
            "files_synced": state.get("files_synced", 0),
            "total_drive_files": state.get("total_drive_files", 0),
            "errors": state.get("errors", []),
        },
        indent=2,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `source .venv/bin/activate && python -m pytest tests/test_sync_status.py -v`
Expected: 2 passed

- [ ] **Step 5: Run full test suite**

Run: `source .venv/bin/activate && python -m pytest tests/ -v`
Expected: all tests pass (27 previous + 5 drive_sync + 3 trigger_sync + 2 sync_status = 37)

- [ ] **Step 6: Commit**

```bash
git add dam_mcp/core/tools_sync.py tests/test_sync_status.py
git commit -m "Replace sync_status stub with real implementation reading GCS state"
```

---

### Task 6: Create Cloud Function

**Files:**
- Create: `dam-mcp/cloud_functions/drive_sync/main.py`
- Create: `dam-mcp/cloud_functions/drive_sync/requirements.txt`

- [ ] **Step 1: Create Cloud Function directory**

Run: `mkdir -p /Users/simonheinken/Documents/projects/meta/mcp/dam-mcp/cloud_functions/drive_sync`

- [ ] **Step 2: Create requirements.txt**

Create `cloud_functions/drive_sync/requirements.txt`:

```
google-cloud-storage>=2.0.0
google-api-python-client>=2.0.0
google-auth>=2.0.0
```

- [ ] **Step 3: Create main.py**

Create `cloud_functions/drive_sync/main.py`:

```python
"""Cloud Function entry point for scheduled Drive-to-GCS sync."""

import json
import os
import functions_framework
from google.oauth2 import service_account
from googleapiclient.discovery import build
from google.cloud import storage

DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
FOLDER_MIME = "application/vnd.google-apps.folder"
DAM_META_PREFIX = "dam_"
SYNC_STATE_BLOB = ".dam_sync_state.json"


def _get_config():
    return {
        "project_id": os.environ["GCP_PROJECT_ID"],
        "bucket_name": os.environ["GCS_BUCKET_NAME"],
        "folder_id": os.environ["GDRIVE_FOLDER_ID"],
    }


def _get_drive_service():
    import google.auth
    credentials, _ = google.auth.default(scopes=DRIVE_SCOPES)
    return build("drive", "v3", credentials=credentials)


def _get_gcs_bucket(cfg):
    client = storage.Client(project=cfg["project_id"])
    return client.bucket(cfg["bucket_name"])


def _list_drive_files(service, folder_id, path_prefix=""):
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
            item_path = f"{path_prefix}{item['name']}" if path_prefix else item["name"]
            if item["mimeType"] == FOLDER_MIME:
                results.extend(_list_drive_files(service, item["id"], f"{item_path}/"))
            else:
                results.append({"id": item["id"], "name": item["name"], "path": item_path, "mimeType": item["mimeType"]})
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return results


def _find_blob_by_drive_id(bucket, drive_file_id):
    for blob in bucket.list_blobs():
        blob.reload()
        meta = blob.metadata or {}
        if meta.get(f"{DAM_META_PREFIX}drive_file_id") == drive_file_id:
            return blob
    return None


def _now_iso():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


@functions_framework.http
def sync_handler(request):
    """HTTP Cloud Function entry point."""
    import time
    start = time.time()

    cfg = _get_config()
    service = _get_drive_service()
    bucket = _get_gcs_bucket(cfg)
    errors = []

    try:
        drive_files = _list_drive_files(service, cfg["folder_id"])
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)}), 500

    new_synced = 0
    skipped = 0

    for f in drive_files:
        existing = _find_blob_by_drive_id(bucket, f["id"])
        if existing is not None:
            skipped += 1
            continue
        try:
            data = service.files().get_media(fileId=f["id"]).execute()
            blob = bucket.blob(f["path"])
            blob.upload_from_string(data, content_type=f["mimeType"])
            blob.metadata = {
                f"{DAM_META_PREFIX}drive_file_id": f["id"],
                f"{DAM_META_PREFIX}original_filename": f["name"],
                f"{DAM_META_PREFIX}upload_source": "drive_sync",
                f"{DAM_META_PREFIX}campaign": f["path"].split("/")[0] if "/" in f["path"] else "",
                f"{DAM_META_PREFIX}created_at": _now_iso(),
                f"{DAM_META_PREFIX}tags": "",
            }
            blob.patch()
            new_synced += 1
        except Exception as e:
            errors.append(f"{f['path']}: {e}")

    duration = round(time.time() - start, 1)
    state = {
        "last_sync_at": _now_iso(),
        "last_sync_result": "completed",
        "files_synced": new_synced,
        "total_drive_files": len(drive_files),
        "errors": errors,
        "duration_seconds": duration,
    }

    state_blob = bucket.blob(SYNC_STATE_BLOB)
    state_blob.upload_from_string(json.dumps(state, indent=2), content_type="application/json")

    return json.dumps({
        "status": "completed",
        "drive_files_found": len(drive_files),
        "new_files_synced": new_synced,
        "skipped_existing": skipped,
        "errors": errors,
        "duration_seconds": duration,
    }), 200
```

- [ ] **Step 4: Commit**

```bash
git add cloud_functions/
git commit -m "Add Cloud Function for scheduled hourly Drive-to-GCS sync"
```

---

### Task 7: Enable Drive API and set up Cloud Scheduler

**Files:** None (GCP infrastructure setup)

- [ ] **Step 1: Enable required APIs**

Run:
```bash
gcloud services enable drive.googleapis.com --project=gold-blueprint-357814
gcloud services enable cloudfunctions.googleapis.com --project=gold-blueprint-357814
gcloud services enable cloudscheduler.googleapis.com --project=gold-blueprint-357814
gcloud services enable cloudbuild.googleapis.com --project=gold-blueprint-357814
gcloud services enable run.googleapis.com --project=gold-blueprint-357814
```

- [ ] **Step 2: Get the Drive folder ID from the user**

The user needs to share their Google Drive creatives folder with `dam-mcp@gold-blueprint-357814.iam.gserviceaccount.com` (Viewer access) and provide the folder ID (the string in the Drive URL after `/folders/`).

- [ ] **Step 3: Update .env with folder ID**

Add `GDRIVE_FOLDER_ID=<the-folder-id>` to `dam-mcp/.env`.

- [ ] **Step 4: Test sync locally via MCP tool**

Run: `source .venv/bin/activate && python -c "import asyncio; from dam_mcp.core.tools_trigger_sync import trigger_sync; print(asyncio.run(trigger_sync()))"`

Expected: JSON output showing files found and synced.

- [ ] **Step 5: Deploy Cloud Function**

Run:
```bash
gcloud functions deploy drive-sync \
  --gen2 \
  --runtime=python312 \
  --region=europe-west3 \
  --source=cloud_functions/drive_sync/ \
  --entry-point=sync_handler \
  --service-account=dam-mcp@gold-blueprint-357814.iam.gserviceaccount.com \
  --set-env-vars=GCP_PROJECT_ID=gold-blueprint-357814,GCS_BUCKET_NAME=ryzon-dam,GDRIVE_FOLDER_ID=<folder-id> \
  --trigger-http \
  --no-allow-unauthenticated \
  --timeout=300 \
  --memory=256Mi
```

- [ ] **Step 6: Grant invoker role for Cloud Scheduler**

Run:
```bash
gcloud functions add-invoker-policy-binding drive-sync \
  --region=europe-west3 \
  --member="serviceAccount:dam-mcp@gold-blueprint-357814.iam.gserviceaccount.com"
```

- [ ] **Step 7: Create Cloud Scheduler job**

Run (replace `<cloud-function-url>` with the URL from step 5 output):
```bash
gcloud scheduler jobs create http drive-sync-hourly \
  --location=europe-west3 \
  --schedule="0 * * * *" \
  --uri=<cloud-function-url> \
  --oidc-service-account-email=dam-mcp@gold-blueprint-357814.iam.gserviceaccount.com \
  --http-method=POST
```

- [ ] **Step 8: Test scheduled trigger**

Run: `gcloud scheduler jobs run drive-sync-hourly --location=europe-west3`

Then check: `gcloud functions logs read drive-sync --region=europe-west3 --limit=10`

Expected: logs showing sync completed with file counts.

- [ ] **Step 9: Final commit — update .env.example and push**

```bash
git add -A
git commit -m "Complete Drive-to-GCS sync: local tools + Cloud Function + scheduler"
git push
```
