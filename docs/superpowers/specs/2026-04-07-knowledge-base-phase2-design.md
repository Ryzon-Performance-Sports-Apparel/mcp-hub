# Knowledge Base Phase 2 — LLM Enrichment, PII Detection & Vector Search

**Date:** 2026-04-07
**Status:** Draft — awaiting review
**Depends on:** Phase 1 (Firestore knowledge base + meeting notes sync)

---

## Problem

Phase 1 uses rule-based extraction (keyword matching, regex) which produces shallow metadata. Tags are limited to a hardcoded keyword list, there's no summarization, PII is not detected, and search is limited to exact field matches. Meeting notes contain rich semantic content that rule-based approaches can't unlock.

## Solution

Upgrade the existing `document-processor` Cloud Function with:
1. **LLM enrichment** — Claude Haiku 4.5 extracts tags, summary, action items, key decisions, meeting type, language, and PII flags via a single structured tool_use call
2. **PII handling** — Documents flagged as containing PII are moved to `knowledge_base_restricted`
3. **Vector embeddings** — Voyage AI generates embeddings stored as native Firestore vector fields, enabling semantic search via a new MCP tool

---

## Architecture

```
Firestore onCreate → document-processor Cloud Function (upgraded)
  ┌─ Step 1: Rule-based extraction (unchanged) ──────────┐
  │  - Parse date from title                               │
  │  - Extract email addresses as participants             │
  │  - Keyword-based topic tags                            │
  └────────────────────────────────────────────────────────┘
  ┌─ Step 2: LLM enrichment (NEW — Claude Haiku 4.5) ────┐
  │  - Single tool_use call → structured JSON:             │
  │    tags[], summary, sensitivity, action_items[],       │
  │    language, meeting_type, key_decisions[]              │
  │  - Merge LLM tags with rule-based tags (deduplicated)  │
  └────────────────────────────────────────────────────────┘
  ┌─ Step 3: Vector embedding (NEW — Voyage AI) ──────────┐
  │  - Generate embedding from title + summary + content   │
  │  - Store as vector field on the Firestore document     │
  └────────────────────────────────────────────────────────┘
  ┌─ Step 4: PII handling (NEW) ──────────────────────────┐
  │  - If sensitivity == "contains_pii":                   │
  │    → Write enriched doc to knowledge_base_restricted   │
  │    → Delete original from knowledge_base               │
  │  - Else: update doc in knowledge_base                  │
  └────────────────────────────────────────────────────────┘
```

---

## LLM Integration

### Model

Claude Haiku 4.5 (`claude-haiku-4-5-20251001`) — fast, cheap (~$0.001/doc), sufficient quality for structured extraction.

### Tool Definition

```json
{
  "name": "extract_meeting_metadata",
  "description": "Extract structured metadata from a meeting note",
  "input_schema": {
    "type": "object",
    "properties": {
      "tags": {
        "type": "array",
        "items": { "type": "string" },
        "description": "Topic tags — be specific (project names, team names, topic-specific terms), not generic"
      },
      "summary": {
        "type": "string",
        "description": "2-3 sentence summary of what was discussed and decided"
      },
      "sensitivity": {
        "type": "string",
        "enum": ["safe", "contains_pii"],
        "description": "Flag 'contains_pii' only for genuinely personal data (health info, salary, personal phone/address). Business emails and professional names are NOT PII."
      },
      "action_items": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "task": { "type": "string" },
            "assignee": { "type": "string", "description": "Person responsible, or null if unassigned" },
            "due": { "type": "string", "description": "Due date if mentioned, or null" }
          },
          "required": ["task"]
        }
      },
      "key_decisions": {
        "type": "array",
        "items": { "type": "string" },
        "description": "Concrete decisions made during the meeting"
      },
      "meeting_type": {
        "type": "string",
        "enum": ["standup", "planning", "review", "retro", "1on1", "kickoff", "demo", "brainstorm", "sync", "other"]
      },
      "language": {
        "type": "string",
        "description": "ISO 639-1 code of the primary language (e.g. 'en', 'de')"
      }
    },
    "required": ["tags", "summary", "sensitivity", "action_items", "key_decisions", "meeting_type", "language"]
  }
}
```

### System Prompt

```
You are a meeting notes analyst. Extract structured metadata from the provided meeting note.

Guidelines:
- Tags: Use specific terms (project names, team names, technologies) rather than generic labels. Include 3-8 tags.
- Summary: 2-3 sentences covering what was discussed and any outcomes.
- PII: Flag only genuinely personal data (health information, salary details, personal phone numbers, home addresses). Business email addresses and names in a professional context are NOT PII.
- Action items: Extract concrete tasks with assignees where mentioned. Omit vague intentions.
- Key decisions: Only include explicit decisions, not ongoing discussions.
- Meeting type: Classify based on the meeting's primary purpose.
- Language: The primary language of the content.
```

### User Message

```
Meeting title: {title}

Meeting notes:
{content}
```

### Error Handling

If the Claude API call fails (rate limit, timeout, auth error):
- Keep rule-based extraction results
- Set `llm_enriched: false` on the document
- Set `processing_status: "processed"` (don't block on LLM failure)
- Log the error for monitoring

---

## Vector Embeddings

### Model

Voyage AI `voyage-3-lite` — 1024 dimensions, optimized for retrieval. Cost-effective for batch processing.

### Embedding Input

Concatenation of: `{title}\n\n{summary}\n\n{content[:8000]}`

Content is truncated to 8000 chars to stay within Voyage AI's context window while including the most relevant content. The summary (generated by the LLM in Step 2) provides a dense semantic representation even when content is truncated.

### Storage

Native Firestore vector field: `embedding` of type `vector(1024)`.

### Vector Index

```bash
gcloud firestore indexes composite create \
  --collection-group=knowledge_base \
  --field-config=field-path=embedding,vector-config='{"dimension":"1024","flat":{}}' \
  --project=gold-blueprint-357814

gcloud firestore indexes composite create \
  --collection-group=knowledge_base_restricted \
  --field-config=field-path=embedding,vector-config='{"dimension":"1024","flat":{}}' \
  --project=gold-blueprint-357814
```

### Error Handling

If the Voyage AI call fails:
- Set `embedding` to null
- Set `llm_enriched: true` (LLM enrichment is separate from embedding)
- Document is still searchable via tags/metadata, just not via semantic search

---

## PII Handling

When the LLM flags `sensitivity: "contains_pii"`:

1. Build the complete enriched document (all fields including embedding)
2. Write the document to `knowledge_base_restricted` with the same document ID
3. Delete the document from `knowledge_base`

This ensures the document is always in exactly one collection. The move is atomic from the consumer's perspective — the document disappears from `knowledge_base` and appears in `knowledge_base_restricted`.

Documents flagged `safe` stay in `knowledge_base` as before.

---

## Schema Changes

### New Fields (added to both collections)

| Field | Type | Description |
|-------|------|-------------|
| `summary` | string | LLM-generated 2-3 sentence summary |
| `action_items` | array of objects | `{ task, assignee, due }` |
| `key_decisions` | string[] | Explicit decisions from the meeting |
| `meeting_type` | string | standup, planning, review, retro, 1on1, kickoff, demo, brainstorm, sync, other |
| `language` | string | ISO 639-1 code (e.g. "en", "de") |
| `embedding` | vector(1024) | Voyage AI embedding for semantic search |
| `llm_enriched` | boolean | Whether LLM enrichment succeeded |

### Changed Fields

| Field | Change |
|-------|--------|
| `sensitivity` | Now set by LLM ("safe" or "contains_pii") instead of always "unreviewed" |
| `tags` | Now includes LLM-generated semantic tags merged with rule-based tags |

---

## New MCP Tool: `search_knowledge_base_semantic`

```python
search_knowledge_base_semantic(
    query: str,                          # natural language query
    type: Optional[str] = None,          # optional type filter (e.g. "meeting_note")
    limit: int = 10,                     # max results
) -> str  # JSON array of document metadata + content preview
```

**Flow:**
1. Generate embedding for the query using Voyage AI
2. Run Firestore KNN vector search with the query embedding
3. Optionally filter by `type` field
4. Return results sorted by similarity (metadata + content preview, no full content)

This tool lives in `dam_mcp/core/tools_semantic_search.py` and is registered in `__init__.py`.

---

## Infrastructure Changes

### Cloud Function: `document-processor`

| Setting | v1 | v2 |
|---------|----|----|
| Timeout | 60s | 300s |
| Memory | 256Mi | 512Mi |
| Dependencies | google-cloud-firestore, cloudevents | + anthropic, voyageai |

### New Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes (for processor) | Claude API key for Haiku calls |
| `VOYAGE_API_KEY` | Yes (for processor + dam-mcp) | Voyage AI API key for embeddings |

### New Dependencies

**document-processor (`requirements.txt`):**
- `anthropic>=0.52.0`
- `voyageai>=0.3.0`

**dam-mcp (`pyproject.toml`):**
- `voyageai>=0.3.0` (for generating query embeddings in the semantic search tool)

### Firestore Vector Indexes

Two new vector indexes (one per collection) for KNN search on the `embedding` field.

---

## Files to Create/Modify

**Modified:**
- `cloud_functions/document_processor/main.py` — Add LLM enrichment, embedding generation, PII handling
- `cloud_functions/document_processor/requirements.txt` — Add anthropic, voyageai
- `dam_mcp/core/__init__.py` — Register new semantic search tool
- `dam_mcp/core/firestore.py` — Add vector search helper
- `pyproject.toml` — Add voyageai dependency

**New:**
- `dam_mcp/core/tools_semantic_search.py` — Semantic search MCP tool
- `tests/test_semantic_search.py` — Tests for semantic search tool
- `tests/test_document_processor_llm.py` — Tests for LLM enrichment logic

---

## Testing

### Unit Tests

- **LLM enrichment:** Mock Anthropic client. Verify: tool_use response is correctly parsed into document fields, tags are merged with rule-based tags, error handling when API fails (falls back to rule-based only).
- **Embedding generation:** Mock Voyage AI client. Verify: embedding is stored as vector field, graceful fallback when API fails.
- **PII handling:** Mock Firestore. Verify: document is moved to `knowledge_base_restricted` when PII detected, stays in `knowledge_base` when safe.
- **Semantic search tool:** Mock Firestore vector search + Voyage AI. Verify: query embedding generated, KNN search executed, results formatted correctly.

### Integration Tests

- Sync a test document → verify full pipeline: rule-based + LLM + embedding + correct collection placement
- Run semantic search → verify relevant documents are returned

---

## Cost Estimate

Per meeting note processed:
- Claude Haiku 4.5: ~$0.001 (input ~2K tokens, output ~500 tokens)
- Voyage AI embedding: ~$0.0001 (1 embedding per doc)
- Total: ~$0.001/doc

At 100 meeting notes/month: ~$0.10/month. Negligible.

---

## Rollback Plan

If LLM enrichment causes issues:
- Set `ANTHROPIC_API_KEY` to empty → processor falls back to rule-based only
- Set `VOYAGE_API_KEY` to empty → embeddings skipped, metadata still works
- Documents already enriched retain their LLM fields (no data loss)
