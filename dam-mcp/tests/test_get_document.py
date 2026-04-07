"""Tests for get_document MCP tool."""

import json
import pytest
from datetime import datetime, timezone
from unittest.mock import patch

from dam_mcp.core.tools_get_document import get_document


@pytest.mark.asyncio
async def test_get_document_found():
    mock_doc = {
        "id": "doc1",
        "type": "meeting_note",
        "title": "Weekly Standup",
        "content": "Full meeting content here.",
        "tags": ["standup"],
        "created_at": datetime(2026, 4, 7, tzinfo=timezone.utc),
    }
    with patch("dam_mcp.core.tools_get_document.fs_get_document", return_value=mock_doc):
        result = await get_document("doc1")
        data = json.loads(result)
        assert data["title"] == "Weekly Standup"
        assert data["content"] == "Full meeting content here."


@pytest.mark.asyncio
async def test_get_document_not_found():
    with patch("dam_mcp.core.tools_get_document.fs_get_document", return_value=None):
        result = await get_document("nonexistent")
        data = json.loads(result)
        assert "error" in data
        assert "not found" in data["error"].lower()


@pytest.mark.asyncio
async def test_get_document_config_error(mock_config):
    mock_config.gcp_project_id = ""
    mock_config.gcs_bucket_name = ""
    result = await get_document("doc1")
    data = json.loads(result)
    assert "error" in data
    assert "GCP_PROJECT_ID" in data["error"]
