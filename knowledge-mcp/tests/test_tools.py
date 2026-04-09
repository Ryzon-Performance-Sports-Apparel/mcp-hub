"""Tests for Knowledge MCP tools."""

import json
import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock, call

from knowledge_mcp.core.access import UserContext, AccessDecision
from knowledge_mcp.core.tools_query import query_knowledge_base
from knowledge_mcp.core.tools_get import get_document
from knowledge_mcp.core.tools_semantic import search_knowledge_base_semantic


# Helper to mock PolicyEngine for all tool tests
def _mock_policy_engine(module_path, user_email="test@ryzon.net", roles=None, allowed_sensitivity=None):
    """Return a patch context manager that mocks PolicyEngine in the given module."""
    if roles is None:
        roles = ["admin"]
    if allowed_sensitivity is None:
        allowed_sensitivity = ["public", "internal", "confidential", "restricted"]

    mock_engine_class = MagicMock()
    engine_instance = MagicMock()
    mock_engine_class.return_value = engine_instance
    mock_engine_class.load_policies_from_firestore.return_value = []
    engine_instance.resolve_user.return_value = UserContext(email=user_email, roles=roles)
    engine_instance.get_allowed_sensitivity.return_value = allowed_sensitivity
    # Default: allow everything through filter_results
    engine_instance.filter_results.side_effect = lambda user, docs: docs
    # Default: allow access for evaluate
    engine_instance.evaluate.return_value = AccessDecision(allowed=True, reason="admin")

    return patch(f"{module_path}.PolicyEngine", mock_engine_class), engine_instance


@pytest.mark.asyncio
async def test_query_knowledge_base_basic():
    mock_docs = [
        {
            "id": "doc1",
            "type": "meeting_note",
            "title": "Weekly Standup",
            "content": "Discussion about sprint goals.",
            "tags": ["standup"],
            "sensitivity": "public",
            "content_categories": ["project_update"],
            "participants": ["test@ryzon.net"],
            "mentioned_persons": [],
            "processing_status": "processed",
            "created_at": datetime(2026, 4, 7, tzinfo=timezone.utc),
        }
    ]
    policy_patch, engine = _mock_policy_engine("knowledge_mcp.core.tools_query")
    with patch("knowledge_mcp.core.tools_query.query_documents", return_value=mock_docs), policy_patch:
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
        "sensitivity": "public",
        "content_categories": [],
        "participants": ["test@ryzon.net"],
        "mentioned_persons": [],
        "created_at": datetime(2026, 4, 7, tzinfo=timezone.utc),
    }
    policy_patch, engine = _mock_policy_engine("knowledge_mcp.core.tools_get")
    with patch("knowledge_mcp.core.tools_get.fs_get_document", return_value=mock_doc), policy_patch:
        result = await get_document("doc1")
        data = json.loads(result)
        assert data["content"] == "Full content"


@pytest.mark.asyncio
async def test_get_document_not_found():
    policy_patch, _ = _mock_policy_engine("knowledge_mcp.core.tools_get")
    with patch("knowledge_mcp.core.tools_get.fs_get_document", return_value=None), policy_patch:
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
    mock_docs = [{"id": "doc1", "title": "Sprint Planning", "content": "We planned.", "tags": ["sprint"], "sensitivity": "public", "content_categories": ["project_update"], "participants": ["test@ryzon.net"], "mentioned_persons": [], "created_at": datetime(2026, 4, 7, tzinfo=timezone.utc)}]
    mock_voyage = MagicMock()
    mock_result = MagicMock()
    mock_result.embeddings = [[0.1] * 512]
    mock_voyage.embed.return_value = mock_result
    policy_patch, engine = _mock_policy_engine("knowledge_mcp.core.tools_semantic")
    with patch("knowledge_mcp.core.tools_semantic._get_voyage_client", return_value=mock_voyage), \
         patch("knowledge_mcp.core.tools_semantic.vector_search", return_value=mock_docs), \
         policy_patch:
        result = await search_knowledge_base_semantic(query="sprint planning")
        data = json.loads(result)
        assert data["count"] == 1


@pytest.mark.asyncio
async def test_config_error(mock_config):
    mock_config.gcp_project_id = ""
    result = await query_knowledge_base()
    data = json.loads(result)
    assert "error" in data


# -- Access control integration tests --

@pytest.mark.asyncio
async def test_query_filters_by_access(mock_config):
    """Documents the user cannot access are filtered out of results."""
    mock_docs = [
        {
            "id": "public1",
            "type": "meeting_note",
            "title": "Sprint Update",
            "content": "Sprint discussion.",
            "tags": ["sprint"],
            "sensitivity": "public",
            "content_categories": ["project_update"],
            "participants": ["dev@ryzon.net"],
            "mentioned_persons": [],
            "processing_status": "processed",
            "created_at": datetime(2026, 4, 9, tzinfo=timezone.utc),
        },
        {
            "id": "confidential1",
            "type": "meeting_note",
            "title": "HR Review",
            "content": "Performance feedback.",
            "tags": ["hr"],
            "sensitivity": "confidential",
            "content_categories": ["interpersonal_feedback"],
            "participants": ["boss@ryzon.net"],
            "mentioned_persons": [],
            "processing_status": "processed",
            "created_at": datetime(2026, 4, 9, tzinfo=timezone.utc),
        },
    ]
    policy_patch, engine = _mock_policy_engine(
        "knowledge_mcp.core.tools_query",
        user_email="dev@ryzon.net",
        roles=["employee"],
        allowed_sensitivity=["public", "internal"],
    )
    # filter_results should only keep the public doc
    engine.filter_results.side_effect = lambda user, docs: [d for d in docs if d["sensitivity"] in ["public", "internal"]]

    with patch("knowledge_mcp.core.tools_query.query_documents", return_value=mock_docs), policy_patch:
        result = await query_knowledge_base(type="meeting_note")
        data = json.loads(result)
        assert data["count"] == 1
        assert data["documents"][0]["id"] == "public1"
        engine.filter_results.assert_called_once()


@pytest.mark.asyncio
async def test_get_document_access_denied(mock_config):
    """get_document returns access denied when policy denies."""
    mock_doc = {
        "id": "secret1",
        "title": "Secret",
        "content": "Confidential",
        "sensitivity": "restricted",
        "content_categories": ["compensation"],
        "participants": [],
        "mentioned_persons": [],
        "created_at": datetime(2026, 4, 9, tzinfo=timezone.utc),
    }
    policy_patch, engine = _mock_policy_engine(
        "knowledge_mcp.core.tools_get",
        user_email="dev@ryzon.net",
        roles=["employee"],
    )
    engine.evaluate.return_value = AccessDecision(allowed=False, reason="sensitivity 'restricted' not allowed")

    with patch("knowledge_mcp.core.tools_get.fs_get_document", return_value=mock_doc), policy_patch:
        result = await get_document("secret1")
        data = json.loads(result)
        assert "error" in data
        assert "access denied" in data["error"].lower()


@pytest.mark.asyncio
async def test_query_no_auth_returns_error(mock_config):
    """When no user email is set, tools return an auth error."""
    mock_config._user_email = None
    result = await query_knowledge_base()
    data = json.loads(result)
    assert "error" in data
    assert "authentication" in data["error"].lower()


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
