"""Tests for document-processor Cloud Function."""

import os
import sys
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone


def _make_processor_module():
    """Import the processor module."""
    sys.path.insert(
        0,
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "cloud_functions",
            "document_processor",
        ),
    )
    if "main" in sys.modules:
        del sys.modules["main"]
    import main
    sys.path.pop(0)
    return main


class TestExtractEmails:
    def test_extracts_emails(self):
        mod = _make_processor_module()
        content = "Attendees: alice@company.com, bob@company.com discussed the roadmap."
        emails = mod._extract_emails(content)
        assert "alice@company.com" in emails
        assert "bob@company.com" in emails

    def test_no_emails(self):
        mod = _make_processor_module()
        assert mod._extract_emails("No emails here.") == []

    def test_deduplicates(self):
        mod = _make_processor_module()
        content = "alice@co.com said hello. alice@co.com said goodbye."
        emails = mod._extract_emails(content)
        assert emails == ["alice@co.com"]


class TestParseDateFromTitle:
    def test_iso_date(self):
        mod = _make_processor_module()
        result = mod._parse_date_from_title("Weekly Standup 2026-04-07")
        assert result == datetime(2026, 4, 7, tzinfo=timezone.utc)

    def test_slash_ymd_date(self):
        mod = _make_processor_module()
        result = mod._parse_date_from_title("Raika / Simon: Intro - 2026/01/08 11:03 CET")
        assert result == datetime(2026, 1, 8, tzinfo=timezone.utc)

    def test_us_date(self):
        mod = _make_processor_module()
        result = mod._parse_date_from_title("Meeting 04/07/2026")
        assert result == datetime(2026, 4, 7, tzinfo=timezone.utc)

    def test_month_name_date(self):
        mod = _make_processor_module()
        result = mod._parse_date_from_title("Standup April 7, 2026")
        assert result == datetime(2026, 4, 7, tzinfo=timezone.utc)

    def test_day_month_year(self):
        mod = _make_processor_module()
        result = mod._parse_date_from_title("Notes 7 April 2026")
        assert result == datetime(2026, 4, 7, tzinfo=timezone.utc)

    def test_abbreviated_month(self):
        mod = _make_processor_module()
        result = mod._parse_date_from_title("Standup Apr 7, 2026")
        assert result == datetime(2026, 4, 7, tzinfo=timezone.utc)

    def test_no_date(self):
        mod = _make_processor_module()
        result = mod._parse_date_from_title("Weekly Standup Notes")
        assert result is None


class TestExtractTopicTags:
    def test_extracts_from_title(self):
        mod = _make_processor_module()
        tags = mod._extract_topic_tags("Sprint Planning Meeting", "")
        assert "sprint" in tags
        assert "planning" in tags

    def test_extracts_from_content(self):
        mod = _make_processor_module()
        tags = mod._extract_topic_tags("Meeting", "We discussed the roadmap and hiring plans.")
        assert "roadmap" in tags
        assert "hiring" in tags

    def test_normalizes_variants(self):
        mod = _make_processor_module()
        tags = mod._extract_topic_tags("Stand-up meeting", "post-mortem discussion")
        assert "standup" in tags
        assert "postmortem" in tags

    def test_no_matches(self):
        mod = _make_processor_module()
        tags = mod._extract_topic_tags("Hello", "World")
        assert tags == []


class TestProcessDocument:
    @patch.dict("os.environ", {
        "GCP_PROJECT_ID": "test-project",
    })
    def test_processes_document_successfully(self):
        mod = _make_processor_module()

        mock_fs = MagicMock()
        mock_doc_ref = MagicMock()
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "title": "Weekly Standup 2026-04-07",
            "content": "alice@company.com discussed sprint goals with bob@company.com.",
            "tags": ["engineering"],
            "processing_status": "raw",
        }
        mock_doc_ref.get.return_value = mock_doc
        mock_fs.collection.return_value.document.return_value = mock_doc_ref

        cloud_event = MagicMock()
        cloud_event.__getitem__ = lambda self, key: "documents/knowledge_base/doc123" if key == "subject" else None

        with patch.object(mod, "_get_firestore_client", return_value=mock_fs):
            mod.process_document(cloud_event)

        # Should have been called twice: once for "processing", once for final update
        assert mock_doc_ref.update.call_count == 2

        # Check final update
        final_update = mock_doc_ref.update.call_args_list[1][0][0]
        assert final_update["processing_status"] == "processed"
        assert "alice@company.com" in final_update["participants"]
        assert "bob@company.com" in final_update["participants"]
        assert "sprint" in final_update["tags"]
        assert "engineering" in final_update["tags"]  # preserved from original
        assert final_update["meeting_date"] == datetime(2026, 4, 7, tzinfo=timezone.utc)

    @patch.dict("os.environ", {
        "GCP_PROJECT_ID": "test-project",
    })
    def test_handles_processing_failure(self):
        mod = _make_processor_module()

        mock_fs = MagicMock()
        mock_doc_ref = MagicMock()
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "title": "Test",
            "content": "Content",
            "tags": [],
        }
        mock_doc_ref.get.return_value = mock_doc

        # Make the final update raise an error to test failure handling
        def update_side_effect(data):
            if data.get("processing_status") == "processing":
                return  # First call succeeds
            raise Exception("Firestore write failed")

        mock_doc_ref.update.side_effect = update_side_effect
        mock_fs.collection.return_value.document.return_value = mock_doc_ref

        cloud_event = MagicMock()
        cloud_event.__getitem__ = lambda self, key: "documents/knowledge_base/doc456" if key == "subject" else None

        with patch.object(mod, "_get_firestore_client", return_value=mock_fs):
            with pytest.raises(Exception, match="Firestore write failed"):
                mod.process_document(cloud_event)

    @patch.dict("os.environ", {
        "GCP_PROJECT_ID": "test-project",
    })
    def test_skips_nonexistent_document(self):
        mod = _make_processor_module()

        mock_fs = MagicMock()
        mock_doc_ref = MagicMock()
        mock_doc = MagicMock()
        mock_doc.exists = False
        mock_doc_ref.get.return_value = mock_doc
        mock_fs.collection.return_value.document.return_value = mock_doc_ref

        cloud_event = MagicMock()
        cloud_event.__getitem__ = lambda self, key: "documents/knowledge_base/gone" if key == "subject" else None

        with patch.object(mod, "_get_firestore_client", return_value=mock_fs):
            mod.process_document(cloud_event)

        # Should not attempt any updates
        mock_doc_ref.update.assert_not_called()


class TestLLMEnrichment:
    @patch.dict("os.environ", {
        "GCP_PROJECT_ID": "test-project",
        "ANTHROPIC_API_KEY": "test-key",
    })
    def test_extract_with_llm_success(self):
        mod = _make_processor_module()
        mock_anthropic = MagicMock()
        mock_response = MagicMock()
        mock_tool_block = MagicMock()
        mock_tool_block.type = "tool_use"
        mock_tool_block.input = {
            "tags": ["erp-selection", "vendor-evaluation"],
            "summary": "Team discussed ERP vendor options and narrowed to two finalists.",
            "sensitivity": "safe",
            "action_items": [{"task": "Schedule demo with Odoo", "assignee": "Simon", "due": "2026-04-14"}],
            "key_decisions": ["Shortlisted Odoo and NetSuite"],
            "meeting_type": "review",
            "language": "en",
        }
        mock_response.content = [mock_tool_block]
        mock_anthropic.messages.create.return_value = mock_response
        result = mod._extract_with_llm(mock_anthropic, "ERP Review Meeting", "We reviewed Odoo and NetSuite...")
        assert result["tags"] == ["erp-selection", "vendor-evaluation"]
        assert result["summary"].startswith("Team discussed")
        assert result["sensitivity"] == "safe"
        assert len(result["action_items"]) == 1
        assert result["action_items"][0]["assignee"] == "Simon"
        assert result["meeting_type"] == "review"
        assert result["language"] == "en"

    @patch.dict("os.environ", {
        "GCP_PROJECT_ID": "test-project",
        "ANTHROPIC_API_KEY": "test-key",
    })
    def test_extract_with_llm_api_failure_returns_none(self):
        mod = _make_processor_module()
        mock_anthropic = MagicMock()
        mock_anthropic.messages.create.side_effect = Exception("API timeout")
        result = mod._extract_with_llm(mock_anthropic, "Title", "Content")
        assert result is None

    @patch.dict("os.environ", {
        "GCP_PROJECT_ID": "test-project",
        "ANTHROPIC_API_KEY": "test-key",
    })
    def test_extract_with_llm_no_tool_use_returns_none(self):
        mod = _make_processor_module()
        mock_anthropic = MagicMock()
        mock_response = MagicMock()
        mock_text_block = MagicMock()
        mock_text_block.type = "text"
        mock_response.content = [mock_text_block]
        mock_anthropic.messages.create.return_value = mock_response
        result = mod._extract_with_llm(mock_anthropic, "Title", "Content")
        assert result is None


class TestEmbeddingGeneration:
    @patch.dict("os.environ", {"GCP_PROJECT_ID": "test-project", "VOYAGE_API_KEY": "test-key"})
    def test_generate_embedding_success(self):
        mod = _make_processor_module()
        mock_voyage = MagicMock()
        mock_result = MagicMock()
        mock_result.embeddings = [[0.1, 0.2, 0.3] * 341 + [0.1]]  # 1024 dims
        mock_voyage.embed.return_value = mock_result
        embedding = mod._generate_embedding(mock_voyage, "Title", "Summary", "Content here")
        assert embedding is not None
        assert len(embedding) == 1024
        mock_voyage.embed.assert_called_once()
        call_args = mock_voyage.embed.call_args
        assert call_args[1]["model"] == "voyage-3-lite"

    @patch.dict("os.environ", {"GCP_PROJECT_ID": "test-project", "VOYAGE_API_KEY": "test-key"})
    def test_generate_embedding_api_failure_returns_none(self):
        mod = _make_processor_module()
        mock_voyage = MagicMock()
        mock_voyage.embed.side_effect = Exception("API error")
        embedding = mod._generate_embedding(mock_voyage, "Title", "Summary", "Content")
        assert embedding is None

    @patch.dict("os.environ", {"GCP_PROJECT_ID": "test-project", "VOYAGE_API_KEY": "test-key"})
    def test_generate_embedding_truncates_long_content(self):
        mod = _make_processor_module()
        mock_voyage = MagicMock()
        mock_result = MagicMock()
        mock_result.embeddings = [[0.1] * 1024]
        mock_voyage.embed.return_value = mock_result
        long_content = "x" * 20000
        mod._generate_embedding(mock_voyage, "Title", "Summary", long_content)
        call_args = mock_voyage.embed.call_args
        input_text = call_args[1]["texts"][0]
        assert len(input_text) < 8200


class TestProcessDocumentWithLLM:
    @patch.dict("os.environ", {
        "GCP_PROJECT_ID": "test-project",
        "ANTHROPIC_API_KEY": "test-key",
        "VOYAGE_API_KEY": "test-key",
    })
    def test_process_with_llm_enrichment(self):
        mod = _make_processor_module()

        mock_fs = MagicMock()
        mock_doc_ref = MagicMock()
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "title": "Sprint Planning 2026-04-07",
            "content": "We planned the sprint. alice@co.com will handle the auth module.",
            "tags": ["engineering"],
            "processing_status": "raw",
        }
        mock_doc_ref.get.return_value = mock_doc
        mock_fs.collection.return_value.document.return_value = mock_doc_ref

        llm_result = {
            "tags": ["sprint-planning", "auth-module"],
            "summary": "Sprint planned with auth module as top priority.",
            "sensitivity": "safe",
            "action_items": [{"task": "Implement auth module", "assignee": "alice@co.com"}],
            "key_decisions": ["Auth module is top priority"],
            "meeting_type": "planning",
            "language": "en",
        }
        mock_embedding = [0.1] * 1024

        cloud_event = MagicMock()
        cloud_event.__getitem__ = lambda self, key: "documents/knowledge_base/doc1" if key == "subject" else None

        with patch.object(mod, "_get_firestore_client", return_value=mock_fs), \
             patch.object(mod, "_get_anthropic_client", return_value=MagicMock()), \
             patch.object(mod, "_get_voyage_client", return_value=MagicMock()), \
             patch.object(mod, "_extract_with_llm", return_value=llm_result), \
             patch.object(mod, "_generate_embedding", return_value=mock_embedding):
            mod.process_document(cloud_event)

        final_update = mock_doc_ref.update.call_args_list[-1][0][0]
        assert final_update["processing_status"] == "processed"
        assert final_update["llm_enriched"] is True
        assert final_update["summary"] == "Sprint planned with auth module as top priority."
        assert "sprint-planning" in final_update["tags"]
        assert "engineering" in final_update["tags"]
        assert final_update["meeting_type"] == "planning"
        assert final_update["embedding"] is not None

    @patch.dict("os.environ", {
        "GCP_PROJECT_ID": "test-project",
    })
    def test_process_without_api_keys_falls_back_to_rule_based(self):
        mod = _make_processor_module()

        mock_fs = MagicMock()
        mock_doc_ref = MagicMock()
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "title": "Standup 2026-04-07",
            "content": "Quick sync on progress.",
            "tags": [],
            "processing_status": "raw",
        }
        mock_doc_ref.get.return_value = mock_doc
        mock_fs.collection.return_value.document.return_value = mock_doc_ref

        cloud_event = MagicMock()
        cloud_event.__getitem__ = lambda self, key: "documents/knowledge_base/doc2" if key == "subject" else None

        with patch.object(mod, "_get_firestore_client", return_value=mock_fs):
            mod.process_document(cloud_event)

        final_update = mock_doc_ref.update.call_args_list[-1][0][0]
        assert final_update["processing_status"] == "processed"
        assert final_update["llm_enriched"] is False


class TestPIIHandling:
    @patch.dict("os.environ", {
        "GCP_PROJECT_ID": "test-project",
        "ANTHROPIC_API_KEY": "test-key",
    })
    def test_pii_document_moved_to_restricted(self):
        mod = _make_processor_module()

        mock_fs = MagicMock()
        mock_doc_ref = MagicMock()
        mock_restricted_doc_ref = MagicMock()
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "title": "HR Review 2026-04-07",
            "content": "Discussed salary adjustments for the team.",
            "tags": [],
            "processing_status": "raw",
        }
        mock_doc_ref.get.return_value = mock_doc

        def collection_router(name):
            mock_col = MagicMock()
            if name == "knowledge_base_restricted":
                mock_col.document.return_value = mock_restricted_doc_ref
            else:
                mock_col.document.return_value = mock_doc_ref
            return mock_col

        mock_fs.collection.side_effect = collection_router

        llm_result = {
            "tags": ["hr", "salary"],
            "summary": "Salary adjustments discussed.",
            "sensitivity": "contains_pii",
            "action_items": [],
            "key_decisions": [],
            "meeting_type": "review",
            "language": "en",
        }

        cloud_event = MagicMock()
        cloud_event.__getitem__ = lambda self, key: "documents/knowledge_base/pii_doc" if key == "subject" else None

        with patch.object(mod, "_get_firestore_client", return_value=mock_fs), \
             patch.object(mod, "_get_anthropic_client", return_value=MagicMock()), \
             patch.object(mod, "_get_voyage_client", return_value=None), \
             patch.object(mod, "_extract_with_llm", return_value=llm_result):
            mod.process_document(cloud_event)

        mock_restricted_doc_ref.set.assert_called_once()
        written_doc = mock_restricted_doc_ref.set.call_args[0][0]
        assert written_doc["sensitivity"] == "contains_pii"
        mock_doc_ref.delete.assert_called_once()
