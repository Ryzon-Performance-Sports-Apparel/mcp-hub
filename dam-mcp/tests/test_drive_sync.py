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
    folder_and_file = [
        {"id": "folder1", "name": "Summer-2026", "mimeType": "application/vnd.google-apps.folder", "parents": ["root"]},
        {"id": "f1", "name": "logo.png", "mimeType": "image/png", "parents": ["root"]},
    ]
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
