"""Tests for query_knowledge_base MCP tool."""

import json
import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from dam_mcp.core.tools_query_kb import query_knowledge_base


@pytest.mark.asyncio
async def test_query_knowledge_base_basic():
    mock_docs = [
        {
            "id": "doc1",
            "type": "meeting_note",
            "title": "Weekly Standup",
            "content": "Discussion about sprint goals.",
            "tags": ["standup"],
            "processing_status": "processed",
            "created_at": datetime(2026, 4, 7, tzinfo=timezone.utc),
        }
    ]
    with patch("dam_mcp.core.tools_query_kb.query_documents", return_value=mock_docs):
        result = await query_knowledge_base(type="meeting_note")
        data = json.loads(result)
        assert data["count"] == 1
        assert data["documents"][0]["title"] == "Weekly Standup"
        # Content should be preview (short content)
        assert "content_preview" in data["documents"][0]


@pytest.mark.asyncio
async def test_query_knowledge_base_with_tags():
    with patch("dam_mcp.core.tools_query_kb.query_documents", return_value=[]) as mock_query:
        result = await query_knowledge_base(tags=["engineering", "standup"])
        data = json.loads(result)
        assert data["count"] == 0
        mock_query.assert_called_once()
        call_kwargs = mock_query.call_args[1]
        assert call_kwargs["tags"] == ["engineering", "standup"]


@pytest.mark.asyncio
async def test_query_knowledge_base_with_dates():
    with patch("dam_mcp.core.tools_query_kb.query_documents", return_value=[]) as mock_query:
        result = await query_knowledge_base(
            date_from="2026-04-01",
            date_to="2026-04-07",
        )
        data = json.loads(result)
        assert data["count"] == 0
        call_kwargs = mock_query.call_args[1]
        assert call_kwargs["date_from"] is not None
        assert call_kwargs["date_to"] is not None


@pytest.mark.asyncio
async def test_query_knowledge_base_invalid_date():
    result = await query_knowledge_base(date_from="not-a-date")
    data = json.loads(result)
    assert "error" in data
    assert "date_from" in data["error"]


@pytest.mark.asyncio
async def test_query_knowledge_base_config_error(mock_config):
    mock_config.gcp_project_id = ""
    mock_config.gcs_bucket_name = ""
    result = await query_knowledge_base()
    data = json.loads(result)
    assert "error" in data
