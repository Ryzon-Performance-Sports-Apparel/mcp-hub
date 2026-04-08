# Knowledge Base Phase 2 — LLM Enrichment, PII Detection & Vector Search

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the document-processor Cloud Function with Claude Haiku for intelligent tagging/summarization/PII detection, add Voyage AI vector embeddings, and add a semantic search MCP tool.

**Architecture:** The existing Firestore-triggered `document-processor` Cloud Function is upgraded in-place. After rule-based extraction (kept), it calls Claude Haiku via tool_use for structured metadata extraction, then Voyage AI for embeddings. Documents flagged as PII are moved to `knowledge_base_restricted`. A new `search_knowledge_base_semantic` MCP tool enables KNN vector search.

**Tech Stack:** Python 3.12, Anthropic SDK (Claude Haiku 4.5), Voyage AI SDK, Google Cloud Firestore (native vector fields), FastMCP

**Spec:** `docs/superpowers/specs/2026-04-07-knowledge-base-phase2-design.md`

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `cloud_functions/document_processor/main.py` | Modify | Add LLM enrichment, embedding generation, PII move logic |
| `cloud_functions/document_processor/requirements.txt` | Modify | Add anthropic, voyageai deps |
| `dam_mcp/core/firestore.py` | Modify | Add `vector_search()` helper |
| `dam_mcp/core/tools_semantic_search.py` | Create | `search_knowledge_base_semantic` MCP tool |
| `dam_mcp/core/__init__.py` | Modify | Register new tool |
| `dam_mcp/pyproject.toml` | Modify | Add voyageai dep |
| `tests/test_document_processor.py` | Modify | Add LLM enrichment + PII tests |
| `tests/test_semantic_search.py` | Create | Tests for semantic search tool |
| `tests/test_firestore.py` | Modify | Add vector_search test |

---

### Task 1: Add LLM enrichment to document-processor

**Files:**
- Modify: `cloud_functions/document_processor/main.py`
- Modify: `cloud_functions/document_processor/requirements.txt`
- Modify: `tests/test_document_processor.py`

- [ ] **Step 1: Add dependencies to requirements.txt**

Replace `cloud_functions/document_processor/requirements.txt` with:

```
functions-framework==3.*
google-cloud-firestore>=2.0.0
cloudevents>=1.0.0
anthropic>=0.52.0
voyageai>=0.3.0
```

- [ ] **Step 2: Write failing tests for LLM enrichment**

Add to `tests/test_document_processor.py`:

```python
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
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd /Users/simonheinken/Documents/projects/meta/mcp/dam-mcp && python -m pytest tests/test_document_processor.py::TestLLMEnrichment -v`
Expected: FAIL — `_extract_with_llm` does not exist

- [ ] **Step 4: Implement LLM enrichment function**

Add to `cloud_functions/document_processor/main.py` after the existing imports:

```python
import os

EXTRACT_TOOL = {
    "name": "extract_meeting_metadata",
    "description": "Extract structured metadata from a meeting note",
    "input_schema": {
        "type": "object",
        "properties": {
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Topic tags — be specific (project names, team names, topic-specific terms), not generic. Include 3-8 tags.",
            },
            "summary": {
                "type": "string",
                "description": "2-3 sentence summary of what was discussed and decided",
            },
            "sensitivity": {
                "type": "string",
                "enum": ["safe", "contains_pii"],
                "description": "Flag 'contains_pii' only for genuinely personal data (health info, salary, personal phone/address). Business emails and professional names are NOT PII.",
            },
            "action_items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "task": {"type": "string"},
                        "assignee": {"type": "string"},
                        "due": {"type": "string"},
                    },
                    "required": ["task"],
                },
            },
            "key_decisions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Concrete decisions made during the meeting",
            },
            "meeting_type": {
                "type": "string",
                "enum": ["standup", "planning", "review", "retro", "1on1", "kickoff", "demo", "brainstorm", "sync", "other"],
            },
            "language": {
                "type": "string",
                "description": "ISO 639-1 code of the primary language (e.g. 'en', 'de')",
            },
        },
        "required": ["tags", "summary", "sensitivity", "action_items", "key_decisions", "meeting_type", "language"],
    },
}

SYSTEM_PROMPT = """You are a meeting notes analyst. Extract structured metadata from the provided meeting note.

Guidelines:
- Tags: Use specific terms (project names, team names, technologies) rather than generic labels. Include 3-8 tags.
- Summary: 2-3 sentences covering what was discussed and any outcomes.
- PII: Flag only genuinely personal data (health information, salary details, personal phone numbers, home addresses). Business email addresses and names in a professional context are NOT PII.
- Action items: Extract concrete tasks with assignees where mentioned. Omit vague intentions.
- Key decisions: Only include explicit decisions, not ongoing discussions.
- Meeting type: Classify based on the meeting's primary purpose.
- Language: The primary language of the content."""


def _extract_with_llm(client, title: str, content: str) -> dict | None:
    """Call Claude Haiku to extract structured metadata. Returns None on failure."""
    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=[EXTRACT_TOOL],
            tool_choice={"type": "tool", "name": "extract_meeting_metadata"},
            messages=[{
                "role": "user",
                "content": f"Meeting title: {title}\n\nMeeting notes:\n{content}",
            }],
        )
        for block in response.content:
            if block.type == "tool_use":
                return block.input
        return None
    except Exception:
        return None
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /Users/simonheinken/Documents/projects/meta/mcp/dam-mcp && python -m pytest tests/test_document_processor.py::TestLLMEnrichment -v`
Expected: 3 PASSED

- [ ] **Step 6: Commit**

```bash
git add cloud_functions/document_processor/ tests/test_document_processor.py
git commit -m "feat: add LLM enrichment function to document processor"
```

---

### Task 2: Add embedding generation to document-processor

**Files:**
- Modify: `cloud_functions/document_processor/main.py`
- Modify: `tests/test_document_processor.py`

- [ ] **Step 1: Write failing tests for embedding generation**

Add to `tests/test_document_processor.py`:

```python
class TestEmbeddingGeneration:
    @patch.dict("os.environ", {
        "GCP_PROJECT_ID": "test-project",
        "VOYAGE_API_KEY": "test-key",
    })
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

    @patch.dict("os.environ", {
        "GCP_PROJECT_ID": "test-project",
        "VOYAGE_API_KEY": "test-key",
    })
    def test_generate_embedding_api_failure_returns_none(self):
        mod = _make_processor_module()

        mock_voyage = MagicMock()
        mock_voyage.embed.side_effect = Exception("API error")

        embedding = mod._generate_embedding(mock_voyage, "Title", "Summary", "Content")
        assert embedding is None

    @patch.dict("os.environ", {
        "GCP_PROJECT_ID": "test-project",
        "VOYAGE_API_KEY": "test-key",
    })
    def test_generate_embedding_truncates_long_content(self):
        mod = _make_processor_module()

        mock_voyage = MagicMock()
        mock_result = MagicMock()
        mock_result.embeddings = [[0.1] * 1024]
        mock_voyage.embed.return_value = mock_result

        long_content = "x" * 20000
        mod._generate_embedding(mock_voyage, "Title", "Summary", long_content)
        call_args = mock_voyage.embed.call_args
        input_text = call_args[1]["input"][0]
        # Title + \n\n + Summary + \n\n + truncated content
        assert len(input_text) < 8200
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/simonheinken/Documents/projects/meta/mcp/dam-mcp && python -m pytest tests/test_document_processor.py::TestEmbeddingGeneration -v`
Expected: FAIL — `_generate_embedding` does not exist

- [ ] **Step 3: Implement embedding generation function**

Add to `cloud_functions/document_processor/main.py`:

```python
MAX_CONTENT_CHARS = 8000


def _generate_embedding(client, title: str, summary: str, content: str) -> list[float] | None:
    """Generate a vector embedding via Voyage AI. Returns None on failure."""
    try:
        truncated_content = content[:MAX_CONTENT_CHARS]
        input_text = f"{title}\n\n{summary}\n\n{truncated_content}"
        result = client.embed(
            input=[input_text],
            model="voyage-3-lite",
            input_type="document",
        )
        return result.embeddings[0]
    except Exception:
        return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/simonheinken/Documents/projects/meta/mcp/dam-mcp && python -m pytest tests/test_document_processor.py::TestEmbeddingGeneration -v`
Expected: 3 PASSED

- [ ] **Step 5: Commit**

```bash
git add cloud_functions/document_processor/main.py tests/test_document_processor.py
git commit -m "feat: add Voyage AI embedding generation to document processor"
```

---

### Task 3: Wire LLM + embeddings into the process_document flow

**Files:**
- Modify: `cloud_functions/document_processor/main.py`
- Modify: `tests/test_document_processor.py`

- [ ] **Step 1: Write failing test for full enriched processing**

Add to `tests/test_document_processor.py`:

```python
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

        # Check final update call
        final_update = mock_doc_ref.update.call_args_list[-1][0][0]
        assert final_update["processing_status"] == "processed"
        assert final_update["llm_enriched"] is True
        assert final_update["summary"] == "Sprint planned with auth module as top priority."
        assert "sprint-planning" in final_update["tags"]
        assert "engineering" in final_update["tags"]  # preserved from original
        assert final_update["meeting_type"] == "planning"
        assert final_update["embedding"] is not None
        assert len(final_update["embedding"]) == 1024

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
        assert "embedding" not in final_update or final_update["embedding"] is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/simonheinken/Documents/projects/meta/mcp/dam-mcp && python -m pytest tests/test_document_processor.py::TestProcessDocumentWithLLM -v`
Expected: FAIL

- [ ] **Step 3: Update process_document to integrate LLM + embeddings**

Replace the `process_document` function and add client helpers in `cloud_functions/document_processor/main.py`:

```python
def _get_anthropic_client():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    import anthropic
    return anthropic.Anthropic(api_key=api_key)


def _get_voyage_client():
    api_key = os.environ.get("VOYAGE_API_KEY")
    if not api_key:
        return None
    import voyageai
    return voyageai.Client(api_key=api_key)


@functions_framework.cloud_event
def process_document(cloud_event: CloudEvent):
    """Process a newly created document in the knowledge_base collection.

    Step 1: Rule-based extraction (dates, emails, keyword tags)
    Step 2: LLM enrichment via Claude Haiku (tags, summary, PII, action items, etc.)
    Step 3: Vector embedding via Voyage AI
    Step 4: PII handling (move to restricted collection if flagged)
    """
    subject = cloud_event["subject"]
    parts = subject.split("/")
    if len(parts) < 3:
        return
    collection = parts[1]
    doc_id = parts[2]

    fs_client = _get_firestore_client()
    doc_ref = fs_client.collection(collection).document(doc_id)
    doc = doc_ref.get()

    if not doc.exists:
        return

    data = doc.to_dict()
    title = data.get("title", "")
    content = data.get("content", "")

    doc_ref.update({"processing_status": "processing"})

    try:
        # Step 1: Rule-based extraction
        participants = _extract_emails(content)
        meeting_date = _parse_date_from_title(title)
        rule_tags = _extract_topic_tags(title, content)

        existing_tags = data.get("tags", []) or []
        merged_tags = list(dict.fromkeys(existing_tags + rule_tags))

        updates = {
            "participants": participants if participants else None,
            "meeting_date": meeting_date,
            "tags": merged_tags,
            "sensitivity": "safe",
            "processing_status": "processed",
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": firestore.SERVER_TIMESTAMP,
            "llm_enriched": False,
        }

        # Step 2: LLM enrichment
        anthropic_client = _get_anthropic_client()
        if anthropic_client:
            llm_result = _extract_with_llm(anthropic_client, title, content)
            if llm_result:
                updates["llm_enriched"] = True
                updates["summary"] = llm_result.get("summary")
                updates["sensitivity"] = llm_result.get("sensitivity", "safe")
                updates["action_items"] = llm_result.get("action_items", [])
                updates["key_decisions"] = llm_result.get("key_decisions", [])
                updates["meeting_type"] = llm_result.get("meeting_type")
                updates["language"] = llm_result.get("language")
                # Merge LLM tags with existing
                llm_tags = llm_result.get("tags", [])
                updates["tags"] = list(dict.fromkeys(merged_tags + llm_tags))

        # Step 3: Vector embedding
        summary_for_embedding = updates.get("summary", "")
        voyage_client = _get_voyage_client()
        if voyage_client:
            embedding = _generate_embedding(voyage_client, title, summary_for_embedding, content)
            if embedding:
                from google.cloud.firestore_v1.vector import Vector
                updates["embedding"] = Vector(embedding)

        # Step 4: PII handling
        if updates.get("sensitivity") == "contains_pii":
            # Build full document for restricted collection
            full_doc = {**data, **updates}
            full_doc.pop("id", None)
            full_doc["created_at"] = firestore.SERVER_TIMESTAMP
            full_doc["updated_at"] = firestore.SERVER_TIMESTAMP
            fs_client.collection("knowledge_base_restricted").document(doc_id).set(full_doc)
            doc_ref.delete()
        else:
            doc_ref.update(updates)

    except Exception as e:
        doc_ref.update({
            "processing_status": "failed",
            "updated_at": firestore.SERVER_TIMESTAMP,
        })
        raise e
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/simonheinken/Documents/projects/meta/mcp/dam-mcp && python -m pytest tests/test_document_processor.py -v`
Expected: ALL PASSED (existing + new tests)

- [ ] **Step 5: Commit**

```bash
git add cloud_functions/document_processor/main.py tests/test_document_processor.py
git commit -m "feat: wire LLM enrichment + embeddings into document processor flow"
```

---

### Task 4: Add PII move test

**Files:**
- Modify: `tests/test_document_processor.py`

- [ ] **Step 1: Write test for PII document move**

Add to `tests/test_document_processor.py`:

```python
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

        # Document written to restricted collection
        mock_restricted_doc_ref.set.assert_called_once()
        written_doc = mock_restricted_doc_ref.set.call_args[0][0]
        assert written_doc["sensitivity"] == "contains_pii"

        # Original deleted from knowledge_base
        mock_doc_ref.delete.assert_called_once()
```

- [ ] **Step 2: Run test**

Run: `cd /Users/simonheinken/Documents/projects/meta/mcp/dam-mcp && python -m pytest tests/test_document_processor.py::TestPIIHandling -v`
Expected: PASS (implementation already handles this from Task 3)

- [ ] **Step 3: Commit**

```bash
git add tests/test_document_processor.py
git commit -m "test: add PII document move to restricted collection test"
```

---

### Task 5: Add vector_search helper to firestore.py

**Files:**
- Modify: `dam_mcp/core/firestore.py`
- Modify: `tests/test_firestore.py`

- [ ] **Step 1: Write failing test for vector_search**

Add to `tests/test_firestore.py`:

```python
@patch("dam_mcp.core.firestore.get_client")
def test_vector_search(mock_get_client):
    from dam_mcp.core.firestore import vector_search

    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    mock_doc = MagicMock()
    mock_doc.id = "doc1"
    mock_doc.to_dict.return_value = {
        "type": "meeting_note",
        "title": "Sprint Planning",
        "content": "Planned the sprint.",
        "tags": ["sprint"],
    }

    mock_query = MagicMock()
    mock_query.where.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_query.stream.return_value = [mock_doc]
    mock_client.collection.return_value.find_nearest.return_value = mock_query

    results = vector_search(
        query_embedding=[0.1] * 1024,
        limit=5,
    )
    assert len(results) == 1
    assert results[0]["id"] == "doc1"
    mock_client.collection.return_value.find_nearest.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/simonheinken/Documents/projects/meta/mcp/dam-mcp && python -m pytest tests/test_firestore.py::test_vector_search -v`
Expected: FAIL — `vector_search` does not exist

- [ ] **Step 3: Implement vector_search**

Add to `dam_mcp/core/firestore.py`:

```python
from google.cloud.firestore_v1.vector import Vector
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure


def vector_search(
    query_embedding: list[float],
    collection: str = COLLECTION_GENERAL,
    doc_type: str | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Perform KNN vector search using Firestore native vector fields."""
    client = get_client()
    query = client.collection(collection).find_nearest(
        vector_field="embedding",
        query_vector=Vector(query_embedding),
        distance_measure=DistanceMeasure.COSINE,
        limit=limit,
    )

    if doc_type:
        query = query.where("type", "==", doc_type)

    results = []
    for doc in query.stream():
        data = doc.to_dict()
        data["id"] = doc.id
        data.pop("embedding", None)  # Don't return the raw vector
        results.append(data)

    return results
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/simonheinken/Documents/projects/meta/mcp/dam-mcp && python -m pytest tests/test_firestore.py::test_vector_search -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add dam_mcp/core/firestore.py tests/test_firestore.py
git commit -m "feat: add vector_search helper to Firestore client"
```

---

### Task 6: Create semantic search MCP tool

**Files:**
- Create: `dam_mcp/core/tools_semantic_search.py`
- Modify: `dam_mcp/core/__init__.py`
- Modify: `pyproject.toml`
- Create: `tests/test_semantic_search.py`

- [ ] **Step 1: Add voyageai to pyproject.toml**

Add `"voyageai>=0.3.0",` to the dependencies list in `pyproject.toml`.

- [ ] **Step 2: Write failing tests**

Create `tests/test_semantic_search.py`:

```python
"""Tests for search_knowledge_base_semantic MCP tool."""

import json
import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from dam_mcp.core.tools_semantic_search import search_knowledge_base_semantic


@pytest.mark.asyncio
async def test_semantic_search_returns_results():
    mock_docs = [
        {
            "id": "doc1",
            "type": "meeting_note",
            "title": "Sprint Planning",
            "content": "We planned the sprint.",
            "tags": ["sprint"],
            "created_at": datetime(2026, 4, 7, tzinfo=timezone.utc),
        }
    ]
    mock_voyage = MagicMock()
    mock_result = MagicMock()
    mock_result.embeddings = [[0.1] * 1024]
    mock_voyage.embed.return_value = mock_result

    with patch("dam_mcp.core.tools_semantic_search._get_voyage_client", return_value=mock_voyage), \
         patch("dam_mcp.core.tools_semantic_search.vector_search", return_value=mock_docs):
        result = await search_knowledge_base_semantic(query="sprint planning")
        data = json.loads(result)
        assert data["count"] == 1
        assert data["documents"][0]["title"] == "Sprint Planning"
        assert "content_preview" in data["documents"][0]


@pytest.mark.asyncio
async def test_semantic_search_with_type_filter():
    mock_voyage = MagicMock()
    mock_result = MagicMock()
    mock_result.embeddings = [[0.1] * 1024]
    mock_voyage.embed.return_value = mock_result

    with patch("dam_mcp.core.tools_semantic_search._get_voyage_client", return_value=mock_voyage), \
         patch("dam_mcp.core.tools_semantic_search.vector_search", return_value=[]) as mock_vs:
        result = await search_knowledge_base_semantic(query="test", type="meeting_note")
        mock_vs.assert_called_once()
        call_kwargs = mock_vs.call_args[1]
        assert call_kwargs["doc_type"] == "meeting_note"


@pytest.mark.asyncio
async def test_semantic_search_no_api_key():
    with patch("dam_mcp.core.tools_semantic_search._get_voyage_client", return_value=None):
        result = await search_knowledge_base_semantic(query="test")
        data = json.loads(result)
        assert "error" in data
        assert "VOYAGE_API_KEY" in data["error"]


@pytest.mark.asyncio
async def test_semantic_search_config_error(mock_config):
    mock_config.gcp_project_id = ""
    mock_config.gcs_bucket_name = ""
    result = await search_knowledge_base_semantic(query="test")
    data = json.loads(result)
    assert "error" in data
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd /Users/simonheinken/Documents/projects/meta/mcp/dam-mcp && python -m pytest tests/test_semantic_search.py -v`
Expected: FAIL — module not found

- [ ] **Step 4: Implement semantic search tool**

Create `dam_mcp/core/tools_semantic_search.py`:

```python
"""search_knowledge_base_semantic tool — vector-based semantic search."""

import json
import os
from typing import Optional

from .config import config
from .firestore import document_to_json, vector_search
from .server import mcp_server


def _get_voyage_client():
    api_key = os.environ.get("VOYAGE_API_KEY")
    if not api_key:
        return None
    import voyageai
    return voyageai.Client(api_key=api_key)


@mcp_server.tool()
async def search_knowledge_base_semantic(
    query: str,
    type: Optional[str] = None,
    limit: int = 10,
) -> str:
    """Search the knowledge base using natural language semantic similarity.

    Generates a vector embedding for your query and finds the most similar
    documents using Firestore vector search. More powerful than tag-based
    search for finding conceptually related content.

    Args:
        query: Natural language search query
        type: Optional document type filter (e.g. "meeting_note")
        limit: Maximum results to return (default: 10)
    """
    error = config.validate()
    if error:
        return json.dumps({"error": error}, indent=2)

    voyage_client = _get_voyage_client()
    if voyage_client is None:
        return json.dumps({"error": "VOYAGE_API_KEY not configured — semantic search unavailable"}, indent=2)

    try:
        result = voyage_client.embed(
            input=[query],
            model="voyage-3-lite",
            input_type="query",
        )
        query_embedding = result.embeddings[0]
    except Exception as e:
        return json.dumps({"error": f"Embedding generation failed: {e}"}, indent=2)

    docs = vector_search(
        query_embedding=query_embedding,
        doc_type=type,
        limit=limit,
    )

    results = [document_to_json(doc, include_content=False) for doc in docs]
    return json.dumps({"documents": results, "count": len(results)}, indent=2)
```

- [ ] **Step 5: Register tool in __init__.py**

Add to `dam_mcp/core/__init__.py`:

```python
from .tools_semantic_search import search_knowledge_base_semantic
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd /Users/simonheinken/Documents/projects/meta/mcp/dam-mcp && pip install -e . && python -m pytest tests/test_semantic_search.py -v`
Expected: 4 PASSED

- [ ] **Step 7: Run full test suite**

Run: `cd /Users/simonheinken/Documents/projects/meta/mcp/dam-mcp && python -m pytest tests/ -v`
Expected: ALL PASSED

- [ ] **Step 8: Commit**

```bash
git add dam_mcp/core/tools_semantic_search.py dam_mcp/core/__init__.py dam_mcp/core/firestore.py pyproject.toml tests/test_semantic_search.py
git commit -m "feat: add semantic search MCP tool with Voyage AI embeddings"
```

---

### Task 7: Deploy and create vector indexes

**Files:** None (infrastructure only)

- [ ] **Step 1: Create Firestore vector indexes**

```bash
gcloud firestore indexes composite create \
  --collection-group=knowledge_base \
  --field-config=field-path=embedding,vector-config='{"dimension":"1024","flat":{}}' \
  --project=gold-blueprint-357814 --async

gcloud firestore indexes composite create \
  --collection-group=knowledge_base_restricted \
  --field-config=field-path=embedding,vector-config='{"dimension":"1024","flat":{}}' \
  --project=gold-blueprint-357814 --async
```

- [ ] **Step 2: Redeploy document-processor with new deps and settings**

```bash
cd /Users/simonheinken/Documents/projects/meta/mcp && \
gcloud functions deploy document-processor \
  --gen2 \
  --runtime=python312 \
  --region=europe-west3 \
  --source=dam-mcp/cloud_functions/document_processor/ \
  --entry-point=process_document \
  --service-account=dam-mcp@gold-blueprint-357814.iam.gserviceaccount.com \
  --set-env-vars=GCP_PROJECT_ID=gold-blueprint-357814,ANTHROPIC_API_KEY=<key>,VOYAGE_API_KEY=<key> \
  --trigger-event-filters="type=google.cloud.firestore.document.v1.created" \
  --trigger-event-filters="database=(default)" \
  --trigger-event-filters-path-pattern="document=knowledge_base/{docId}" \
  --trigger-location=europe-west3 \
  --trigger-service-account=dam-mcp@gold-blueprint-357814.iam.gserviceaccount.com \
  --no-allow-unauthenticated \
  --timeout=300 \
  --memory=512Mi \
  --project=gold-blueprint-357814
```

Note: Replace `<key>` with actual API keys for ANTHROPIC_API_KEY and VOYAGE_API_KEY.

- [ ] **Step 3: Test end-to-end — delete existing docs and re-sync**

```bash
# Delete existing docs
python3 -c "
from google.cloud import firestore
client = firestore.Client(project='gold-blueprint-357814')
for doc in client.collection('knowledge_base').get():
    doc.reference.delete()
print('Deleted')
"

# Re-sync
curl -s -X POST \
  https://europe-west3-gold-blueprint-357814.cloudfunctions.net/meeting-notes-sync \
  -H "Authorization: bearer $(gcloud auth print-identity-token)"

# Wait for processing
sleep 15

# Verify enrichment
python3 -c "
from google.cloud import firestore
client = firestore.Client(project='gold-blueprint-357814')
for doc in client.collection('knowledge_base').get():
    d = doc.to_dict()
    print(f'--- {doc.id} ---')
    print(f'  title: {d.get(\"title\")}')
    print(f'  status: {d.get(\"processing_status\")}')
    print(f'  llm_enriched: {d.get(\"llm_enriched\")}')
    print(f'  summary: {d.get(\"summary\")}')
    print(f'  tags: {d.get(\"tags\")}')
    print(f'  meeting_type: {d.get(\"meeting_type\")}')
    print(f'  language: {d.get(\"language\")}')
    print(f'  action_items: {d.get(\"action_items\")}')
    print(f'  has_embedding: {d.get(\"embedding\") is not None}')
    print()
"
```

- [ ] **Step 4: Commit all remaining changes and push**

```bash
git add -A
git commit -m "deploy: upgrade document-processor with LLM enrichment and vector search"
git push origin main
```
