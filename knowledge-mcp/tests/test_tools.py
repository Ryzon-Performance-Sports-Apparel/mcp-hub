"""Tests for Knowledge MCP tools."""

import json
import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock, call

from knowledge_mcp.core.tools_query import query_knowledge_base
from knowledge_mcp.core.tools_get import get_document
from knowledge_mcp.core.tools_semantic import search_knowledge_base_semantic


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
    with patch("knowledge_mcp.core.tools_query.query_documents", return_value=mock_docs):
        result = await query_knowledge_base(type="meeting_note")
        data = json.loads(result)
        assert data["count"] == 1
        assert "content_preview" in data["documents"][0]


@pytest.mark.asyncio
async def test_query_knowledge_base_invalid_date():
    result = await query_knowledge_base(date_from="not-a-date")
    data = json.loads(result)
    assert "error" in data


@pytest.mark.asyncio
async def test_get_document_found():
    mock_doc = {
        "id": "doc1",
        "title": "Test",
        "content": "Full content",
        "created_at": datetime(2026, 4, 7, tzinfo=timezone.utc),
    }
    with patch("knowledge_mcp.core.tools_get.fs_get_document", return_value=mock_doc):
        result = await get_document("doc1")
        data = json.loads(result)
        assert data["content"] == "Full content"


@pytest.mark.asyncio
async def test_get_document_not_found():
    with patch("knowledge_mcp.core.tools_get.fs_get_document", return_value=None):
        result = await get_document("nonexistent")
        data = json.loads(result)
        assert "error" in data


@pytest.mark.asyncio
async def test_semantic_search_no_api_key():
    with patch("knowledge_mcp.core.tools_semantic._get_voyage_client", return_value=None):
        result = await search_knowledge_base_semantic(query="test")
        data = json.loads(result)
        assert "error" in data
        assert "VOYAGE_API_KEY" in data["error"]


@pytest.mark.asyncio
async def test_semantic_search_returns_results():
    mock_docs = [{"id": "doc1", "title": "Sprint Planning", "content": "We planned.", "tags": ["sprint"], "created_at": datetime(2026, 4, 7, tzinfo=timezone.utc)}]
    mock_voyage = MagicMock()
    mock_result = MagicMock()
    mock_result.embeddings = [[0.1] * 512]
    mock_voyage.embed.return_value = mock_result
    with patch("knowledge_mcp.core.tools_semantic._get_voyage_client", return_value=mock_voyage), \
         patch("knowledge_mcp.core.tools_semantic.vector_search", return_value=mock_docs):
        result = await search_knowledge_base_semantic(query="sprint planning")
        data = json.loads(result)
        assert data["count"] == 1


@pytest.mark.asyncio
async def test_config_error(mock_config):
    mock_config.gcp_project_id = ""
    result = await query_knowledge_base()
    data = json.loads(result)
    assert "error" in data


@pytest.mark.asyncio
async def test_query_documents_with_sensitivity_filter():
    """Verify that sensitivity_in parameter adds a Firestore 'in' filter."""
    with patch("knowledge_mcp.core.firestore.get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_query = MagicMock()
        mock_client.collection.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.stream.return_value = []

        from knowledge_mcp.core.firestore import query_documents
        query_documents(sensitivity_in=["public", "internal"])

        where_calls = mock_query.where.call_args_list
        sensitivity_call = [c for c in where_calls if c[0][0] == "sensitivity"]
        assert len(sensitivity_call) == 1
        assert sensitivity_call[0] == call("sensitivity", "in", ["public", "internal"])
