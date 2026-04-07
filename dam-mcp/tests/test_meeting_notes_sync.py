"""Tests for meeting-notes-sync Cloud Function."""

import json
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from datetime import datetime, timezone


def _make_sync_module():
    """Import the sync module with mocked dependencies."""
    import importlib
    import sys

    # We need to test the cloud function module directly
    # Since it's standalone, we import it by manipulating the path
    import os
    sys.path.insert(
        0,
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "cloud_functions",
            "meeting_notes_sync",
        ),
    )
    # Clear cached import if any
    if "main" in sys.modules:
        del sys.modules["main"]
    import main

    sys.path.pop(0)
    return main


class TestParsingHelpers:
    def test_parse_tags_empty(self):
        mod = _make_sync_module()
        assert mod._parse_tags("") == []
        assert mod._parse_tags(None) == []

    def test_parse_tags_single(self):
        mod = _make_sync_module()
        assert mod._parse_tags("engineering") == ["engineering"]

    def test_parse_tags_multiple(self):
        mod = _make_sync_module()
        result = mod._parse_tags("engineering, product, design")
        assert result == ["engineering", "product", "design"]

    def test_parse_tags_strips_whitespace(self):
        mod = _make_sync_module()
        result = mod._parse_tags("  eng ,  prod  ")
        assert result == ["eng", "prod"]


class TestVerifyFolderAccess:
    def test_access_granted(self):
        mod = _make_sync_module()
        mock_service = MagicMock()
        mock_service.files.return_value.get.return_value.execute.return_value = {
            "id": "folder1",
            "name": "Notes",
        }
        assert mod._verify_folder_access(mock_service, "folder1") is True

    def test_access_denied(self):
        mod = _make_sync_module()
        mock_service = MagicMock()
        mock_service.files.return_value.get.return_value.execute.side_effect = Exception("403")
        assert mod._verify_folder_access(mock_service, "folder1") is False


class TestListGoogleDocs:
    def test_lists_docs_with_pagination(self):
        mod = _make_sync_module()
        mock_service = MagicMock()

        # First page
        page1 = {
            "files": [
                {"id": "doc1", "name": "Standup 2026-04-01", "createdTime": "2026-04-01", "modifiedTime": "2026-04-01", "webViewLink": "https://docs.google.com/doc1"},
            ],
            "nextPageToken": "token2",
        }
        # Second page
        page2 = {
            "files": [
                {"id": "doc2", "name": "Standup 2026-04-07", "createdTime": "2026-04-07", "modifiedTime": "2026-04-07", "webViewLink": "https://docs.google.com/doc2"},
            ],
        }
        mock_service.files.return_value.list.return_value.execute.side_effect = [page1, page2]

        results = mod._list_google_docs_in_folder(mock_service, "folder1")
        assert len(results) == 2
        assert results[0]["id"] == "doc1"
        assert results[1]["id"] == "doc2"


class TestDocumentExistsInFirestore:
    def test_exists(self):
        mod = _make_sync_module()
        mock_fs = MagicMock()
        mock_fs.collection.return_value.where.return_value.where.return_value.limit.return_value.get.return_value = [MagicMock()]
        assert mod._document_exists_in_firestore(mock_fs, "doc1") is True

    def test_not_exists(self):
        mod = _make_sync_module()
        mock_fs = MagicMock()
        mock_fs.collection.return_value.where.return_value.where.return_value.limit.return_value.get.return_value = []
        assert mod._document_exists_in_firestore(mock_fs, "doc1") is False


class TestSyncHandler:
    @patch.dict("os.environ", {
        "GCP_PROJECT_ID": "test-project",
        "CONFIG_SHEET_ID": "sheet123",
    })
    def test_sync_handler_empty_sheet(self):
        mod = _make_sync_module()

        mock_request = MagicMock()
        mock_credentials = MagicMock()
        mock_drive = MagicMock()
        mock_fs = MagicMock()
        mock_sheets = MagicMock()
        mock_worksheet = MagicMock()

        mock_sheets.open_by_key.return_value.worksheet.return_value = mock_worksheet
        mock_worksheet.get_all_records.return_value = []

        with patch.object(mod, "_get_credentials", return_value=mock_credentials), \
             patch.object(mod, "_get_drive_service", return_value=mock_drive), \
             patch.object(mod, "_get_firestore_client", return_value=mock_fs), \
             patch.object(mod, "_get_sheets_client", return_value=mock_sheets), \
             patch.object(mod, "_read_config_sheet", return_value=([], mock_worksheet)):
            result, status = mod.sync_handler(mock_request)
            data = json.loads(result)
            assert status == 200
            assert data["status"] == "completed"
            assert data["new_docs_synced"] == 0

    @patch.dict("os.environ", {
        "GCP_PROJECT_ID": "test-project",
        "CONFIG_SHEET_ID": "sheet123",
    })
    def test_sync_handler_syncs_new_doc(self):
        mod = _make_sync_module()

        mock_request = MagicMock()
        mock_credentials = MagicMock()
        mock_drive = MagicMock()
        mock_fs = MagicMock()
        mock_sheets = MagicMock()
        mock_worksheet = MagicMock()

        config_rows = [{
            "folder_id": "folder1",
            "owner_email": "simon@company.com",
            "meeting_series": "weekly-standup",
            "sync_frequency": "hourly",
            "tags": "engineering",
            "sharing_confirmed": "TRUE",
        }]

        drive_docs = [{
            "id": "gdoc1",
            "name": "Standup 2026-04-07",
            "webViewLink": "https://docs.google.com/gdoc1",
        }]

        # Doc doesn't exist in Firestore yet
        mock_fs.collection.return_value.where.return_value.where.return_value.limit.return_value.get.return_value = []
        # Export returns text
        mock_drive.files.return_value.export.return_value.execute.return_value = b"Meeting notes content"

        with patch.object(mod, "_get_credentials", return_value=mock_credentials), \
             patch.object(mod, "_get_drive_service", return_value=mock_drive), \
             patch.object(mod, "_get_firestore_client", return_value=mock_fs), \
             patch.object(mod, "_get_sheets_client", return_value=mock_sheets), \
             patch.object(mod, "_read_config_sheet", return_value=(config_rows, mock_worksheet)), \
             patch.object(mod, "_list_google_docs_in_folder", return_value=drive_docs), \
             patch.object(mod, "_document_exists_in_firestore", return_value=False), \
             patch.object(mod, "_export_google_doc_as_text", return_value="Meeting notes content"):
            result, status = mod.sync_handler(mock_request)
            data = json.loads(result)
            assert status == 200
            assert data["new_docs_synced"] == 1
            # Verify Firestore write was called
            mock_fs.collection.return_value.add.assert_called_once()

    @patch.dict("os.environ", {
        "GCP_PROJECT_ID": "test-project",
        "CONFIG_SHEET_ID": "sheet123",
    })
    def test_sync_handler_skips_existing_doc(self):
        mod = _make_sync_module()

        mock_request = MagicMock()
        mock_credentials = MagicMock()
        mock_drive = MagicMock()
        mock_fs = MagicMock()
        mock_sheets = MagicMock()
        mock_worksheet = MagicMock()

        config_rows = [{
            "folder_id": "folder1",
            "owner_email": "simon@company.com",
            "meeting_series": "",
            "sync_frequency": "hourly",
            "tags": "",
            "sharing_confirmed": "TRUE",
        }]

        drive_docs = [{"id": "gdoc1", "name": "Existing Doc", "webViewLink": ""}]

        with patch.object(mod, "_get_credentials", return_value=mock_credentials), \
             patch.object(mod, "_get_drive_service", return_value=mock_drive), \
             patch.object(mod, "_get_firestore_client", return_value=mock_fs), \
             patch.object(mod, "_get_sheets_client", return_value=mock_sheets), \
             patch.object(mod, "_read_config_sheet", return_value=(config_rows, mock_worksheet)), \
             patch.object(mod, "_list_google_docs_in_folder", return_value=drive_docs), \
             patch.object(mod, "_document_exists_in_firestore", return_value=True):
            result, status = mod.sync_handler(mock_request)
            data = json.loads(result)
            assert data["skipped_existing"] == 1
            assert data["new_docs_synced"] == 0
