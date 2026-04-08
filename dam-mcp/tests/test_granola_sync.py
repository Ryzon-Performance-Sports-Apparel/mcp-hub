"""Tests for Granola sync Cloud Function."""

import json
import os
import sys
import pytest
from unittest.mock import MagicMock, patch


def _make_module():
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "cloud_functions", "granola_sync"))
    if "main" in sys.modules:
        del sys.modules["main"]
    import main
    sys.path.pop(0)
    return main


class TestParseFrontmatter:
    def test_parses_yaml_frontmatter(self):
        mod = _make_module()
        content = '---\ngranola_id: abc123\ntitle: "Test"\ntags: [a, b]\n---\n\n# Body\nHello'
        meta, body = mod._parse_frontmatter(content)
        assert meta["granola_id"] == "abc123"
        assert meta["title"] == "Test"
        assert meta["tags"] == ["a", "b"]
        assert body.strip() == "# Body\nHello"

    def test_no_frontmatter(self):
        mod = _make_module()
        content = "# Just markdown\nNo frontmatter here"
        meta, body = mod._parse_frontmatter(content)
        assert meta == {}
        assert body == content

    def test_invalid_yaml(self):
        mod = _make_module()
        content = "---\n: invalid: yaml: [[\n---\n\nBody"
        meta, body = mod._parse_frontmatter(content)
        assert meta == {}


class TestParseDate:
    def test_iso_string(self):
        mod = _make_module()
        result = mod._parse_date("2026-02-25T07:45:04.128Z")
        assert result.year == 2026
        assert result.month == 2

    def test_none_input(self):
        mod = _make_module()
        assert mod._parse_date(None) is None

    def test_invalid_string(self):
        mod = _make_module()
        assert mod._parse_date("not-a-date") is None


class TestSyncHandler:
    @patch.dict("os.environ", {"GCP_PROJECT_ID": "test-project", "GRANOLA_DRIVE_FOLDER_ID": "folder1"})
    def test_syncs_new_granola_note(self):
        mod = _make_module()
        mock_request = MagicMock()
        file_content = '---\ngranola_id: abc123\ntitle: "Test Meeting"\ntags: [erp, planning]\nparticipants: [Simon, Moritz]\nmeeting-series: "Weekly"\ncreated_at: "2026-03-17T08:31:28.028Z"\narea: engineering/erp\n---\n\n# Meeting Notes\nWe discussed ERP.'
        mock_fs = MagicMock()

        with patch.object(mod, "_get_credentials", return_value=MagicMock()), \
             patch.object(mod, "_get_drive_service", return_value=MagicMock()), \
             patch.object(mod, "_get_firestore_client", return_value=mock_fs), \
             patch.object(mod, "_list_markdown_files", return_value=[{"id": "file1", "name": "Test_Meeting.md"}]), \
             patch.object(mod, "_download_file", return_value=file_content), \
             patch.object(mod, "_document_exists", return_value=False):
            result, status = mod.sync_handler(mock_request)
            data = json.loads(result)
            assert status == 200
            assert data["new_docs_synced"] == 1
            call_args = mock_fs.collection.return_value.add.call_args[0][0]
            assert call_args["source"] == "granola"
            assert call_args["source_id"] == "abc123"
            assert call_args["tags"] == ["erp", "planning"]
            assert call_args["participants"] == ["Simon", "Moritz"]
            assert call_args["meeting_series"] == "Weekly"
            assert call_args["area"] == "engineering/erp"
            assert "We discussed ERP." in call_args["content"]

    @patch.dict("os.environ", {"GCP_PROJECT_ID": "test-project", "GRANOLA_DRIVE_FOLDER_ID": "folder1"})
    def test_skips_existing_note(self):
        mod = _make_module()
        with patch.object(mod, "_get_credentials", return_value=MagicMock()), \
             patch.object(mod, "_get_drive_service", return_value=MagicMock()), \
             patch.object(mod, "_get_firestore_client", return_value=MagicMock()), \
             patch.object(mod, "_list_markdown_files", return_value=[{"id": "f1", "name": "test.md"}]), \
             patch.object(mod, "_download_file", return_value='---\ngranola_id: abc\n---\nBody'), \
             patch.object(mod, "_document_exists", return_value=True):
            result, status = mod.sync_handler(MagicMock())
            data = json.loads(result)
            assert data["skipped_existing"] == 1
            assert data["new_docs_synced"] == 0

    @patch.dict("os.environ", {"GCP_PROJECT_ID": "test-project", "GRANOLA_DRIVE_FOLDER_ID": "folder1"})
    def test_skips_file_without_granola_id(self):
        mod = _make_module()
        with patch.object(mod, "_get_credentials", return_value=MagicMock()), \
             patch.object(mod, "_get_drive_service", return_value=MagicMock()), \
             patch.object(mod, "_get_firestore_client", return_value=MagicMock()), \
             patch.object(mod, "_list_markdown_files", return_value=[{"id": "f1", "name": "no_id.md"}]), \
             patch.object(mod, "_download_file", return_value='---\ntitle: No ID\n---\nBody'):
            result, status = mod.sync_handler(MagicMock())
            data = json.loads(result)
            assert data["new_docs_synced"] == 0
            assert len(data["errors"]) == 1
