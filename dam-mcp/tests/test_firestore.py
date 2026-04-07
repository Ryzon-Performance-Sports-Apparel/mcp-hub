"""Tests for Firestore client wrapper."""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, PropertyMock


def _make_mock_doc(doc_id="abc123", data=None, exists=True):
    """Create a mock Firestore document snapshot."""
    doc = MagicMock()
    doc.id = doc_id
    doc.exists = exists
    doc.to_dict.return_value = data or {
        "type": "meeting_note",
        "title": "Weekly Standup 2026-04-07",
        "content": "Discussion about sprint goals.",
        "tags": ["engineering", "standup"],
        "processing_status": "processed",
    }
    return doc


@patch("dam_mcp.core.firestore._client", None)
@patch("dam_mcp.core.firestore.firestore.Client")
def test_get_client_creates_singleton(mock_client_cls):
    from dam_mcp.core.firestore import get_client
    import dam_mcp.core.firestore as fs_module

    mock_instance = MagicMock()
    mock_client_cls.return_value = mock_instance

    client = get_client()
    assert client == mock_instance
    mock_client_cls.assert_called_once()

    # Reset for other tests
    fs_module._client = None


@patch("dam_mcp.core.firestore.get_client")
def test_write_document_with_auto_id(mock_get_client):
    from dam_mcp.core.firestore import write_document

    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_col = MagicMock()
    mock_client.collection.return_value = mock_col
    mock_doc_ref = MagicMock()
    mock_doc_ref.id = "auto_generated_id"
    mock_col.add.return_value = (None, mock_doc_ref)

    doc_id = write_document({"title": "Test", "content": "Hello"})
    assert doc_id == "auto_generated_id"
    mock_col.add.assert_called_once()


@patch("dam_mcp.core.firestore.get_client")
def test_write_document_with_explicit_id(mock_get_client):
    from dam_mcp.core.firestore import write_document

    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_col = MagicMock()
    mock_client.collection.return_value = mock_col

    doc_id = write_document({"title": "Test"}, document_id="my_id")
    assert doc_id == "my_id"
    mock_col.document.assert_called_with("my_id")


@patch("dam_mcp.core.firestore.get_client")
def test_get_document_found(mock_get_client):
    from dam_mcp.core.firestore import get_document

    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_doc = _make_mock_doc()
    mock_client.collection.return_value.document.return_value.get.return_value = mock_doc

    result = get_document("abc123")
    assert result is not None
    assert result["id"] == "abc123"
    assert result["type"] == "meeting_note"


@patch("dam_mcp.core.firestore.get_client")
def test_get_document_not_found(mock_get_client):
    from dam_mcp.core.firestore import get_document

    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_doc = _make_mock_doc(exists=False)
    mock_client.collection.return_value.document.return_value.get.return_value = mock_doc

    result = get_document("nonexistent")
    assert result is None


@patch("dam_mcp.core.firestore.get_client")
def test_document_exists_true(mock_get_client):
    from dam_mcp.core.firestore import document_exists

    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_query = MagicMock()
    mock_client.collection.return_value.where.return_value.where.return_value.limit.return_value = mock_query
    mock_query.get.return_value = [_make_mock_doc()]

    assert document_exists("google_drive", "file123") is True


@patch("dam_mcp.core.firestore.get_client")
def test_document_exists_false(mock_get_client):
    from dam_mcp.core.firestore import document_exists

    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_query = MagicMock()
    mock_client.collection.return_value.where.return_value.where.return_value.limit.return_value = mock_query
    mock_query.get.return_value = []

    assert document_exists("google_drive", "file123") is False


@patch("dam_mcp.core.firestore.get_client")
def test_update_document_success(mock_get_client):
    from dam_mcp.core.firestore import update_document

    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_doc_ref = MagicMock()
    mock_client.collection.return_value.document.return_value = mock_doc_ref
    mock_doc_ref.get.return_value = _make_mock_doc()

    result = update_document("abc123", {"tags": ["new_tag"]})
    assert result is True
    mock_doc_ref.update.assert_called_once()


@patch("dam_mcp.core.firestore.get_client")
def test_update_document_not_found(mock_get_client):
    from dam_mcp.core.firestore import update_document

    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_doc_ref = MagicMock()
    mock_client.collection.return_value.document.return_value = mock_doc_ref
    mock_doc_ref.get.return_value = _make_mock_doc(exists=False)

    result = update_document("nonexistent", {"tags": ["new_tag"]})
    assert result is False


def test_document_to_json_with_content():
    from dam_mcp.core.firestore import document_to_json

    doc = {
        "id": "abc",
        "title": "Test",
        "content": "Full content here",
        "created_at": datetime(2026, 4, 7, tzinfo=timezone.utc),
    }
    result = document_to_json(doc, include_content=True)
    assert result["content"] == "Full content here"
    assert result["created_at"] == "2026-04-07T00:00:00+00:00"


def test_document_to_json_without_content_short():
    from dam_mcp.core.firestore import document_to_json

    doc = {"id": "abc", "title": "Test", "content": "Short content"}
    result = document_to_json(doc, include_content=False)
    assert "content" not in result
    assert result["content_preview"] == "Short content"


def test_document_to_json_without_content_long():
    from dam_mcp.core.firestore import document_to_json

    doc = {"id": "abc", "title": "Test", "content": "x" * 1000}
    result = document_to_json(doc, include_content=False)
    assert "content" not in result
    assert result["content_preview"].endswith("...")
    assert len(result["content_preview"]) == 503  # 500 + "..."
