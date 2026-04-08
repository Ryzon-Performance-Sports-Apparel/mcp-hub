# Knowledge MCP Server + Granola Sync

**Date:** 2026-04-08
**Status:** Draft — awaiting review

---

## Problem

The Firestore knowledge base query tools currently live inside dam-mcp alongside asset management tools. This couples two distinct concerns (creative assets vs. team knowledge). As the knowledge base grows with more sources (Google Meet, Granola, and future: Asana, ERP, email), it needs a dedicated MCP server. Additionally, 88 Granola.ai meeting notes stored locally as Markdown need to be synced into the knowledge base.

## Solution

1. **New `knowledge-mcp` server** — standalone MCP server for querying the Firestore knowledge base
2. **Granola-Sync Cloud Function** — syncs Granola Markdown files from Google Drive to Firestore
3. **Document-Processor update** — preserve existing metadata from Granola frontmatter, only supplement with LLM
4. **Remove knowledge tools from dam-mcp** — clean separation

---

## Architecture

```
Monorepo structure:
├── meta-ads-mcp/              (unchanged)
├── google-ads-mcp/            (unchanged)
├── dam-mcp/                   (knowledge tools removed)
│   ├── dam_mcp/core/
│   │   ├── tools_query_kb.py      → DELETED
│   │   ├── tools_get_document.py  → DELETED
│   │   ├── tools_semantic_search.py → DELETED
│   │   ├── firestore.py          → stays (used by sync_status)
│   │   └── ...                    (asset tools unchanged)
│
├── knowledge-mcp/             (NEW)
│   ├── knowledge_mcp/
│   │   ├── __init__.py
│   │   ├── core/
│   │   │   ├── __init__.py        tool registration
│   │   │   ├── server.py          FastMCP("knowledge")
│   │   │   ├── config.py          env vars: GCP_PROJECT_ID, FIRESTORE_DATABASE, VOYAGE_API_KEY
│   │   │   ├── firestore.py       Firestore client (copy from dam-mcp, includes vector_search)
│   │   │   ├── tools_query.py     query_knowledge_base
│   │   │   ├── tools_get.py       get_document
│   │   │   └── tools_semantic.py  search_knowledge_base_semantic
│   │   └── utils.py               logger, helpers
│   ├── tests/
│   ├── pyproject.toml
│   └── Dockerfile                 (for Cloud Run deployment)
│
├── dam-mcp/cloud_functions/
│   ├── meeting_notes_sync/    (existing, unchanged)
│   ├── document_processor/    (existing, minor update)
│   ├── drive_sync/            (existing, unchanged)
│   └── granola_sync/          (NEW)
│       ├── main.py
│       └── requirements.txt
```

---

## knowledge-mcp Server

### Tools

Three tools, moved from dam-mcp with identical signatures:

| Tool | Description |
|------|-------------|
| `query_knowledge_base` | Search by type, tags, meeting_series, date range, status |
| `get_document` | Fetch full document by Firestore ID |
| `search_knowledge_base_semantic` | Natural language vector search via Voyage AI |

### Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `GCP_PROJECT_ID` | Yes | GCP project |
| `FIRESTORE_DATABASE` | No | Default: `(default)` |
| `VOYAGE_API_KEY` | Yes | For semantic search query embeddings |
| `GOOGLE_APPLICATION_CREDENTIALS` | Yes | Service account key path |

### Dependencies

```
mcp[cli]>=1.12.0
google-cloud-firestore>=2.0.0
google-auth>=2.0.0
voyageai>=0.3.0
python-dotenv>=1.1.0
```

### Deployment

Runs as a standalone process (stdio transport for local, HTTP for Cloud Run). Same gateway pattern as dam-mcp if Cloud Run deployment is needed.

---

## Granola-Sync Cloud Function

### Source

Granola meeting notes are stored as Markdown files with YAML frontmatter in a Google Drive folder. The user syncs their local Granola export to Google Drive (manually or via backup tool).

### Frontmatter Schema (existing in Granola files)

```yaml
---
granola_id: 191afc82-014a-46ee-9e97-9fd1be3315cf
title: "Analytics Weekly"
created_at: 2026-02-25T07:45:04.128Z
updated_at: 2026-02-25T08:39:49.310Z
area: finance/analytics-weekly
tags: [pm-automatisierung, asana, granola, low-code]
participants: [Simon Heinken, Sophie, Dennis]
meeting-series: "Analytics Weekly"
---
```

### Sync Algorithm

1. List all `.md` files in the configured Drive folder via Drive API
2. For each file:
   a. Download raw file content (not export — these are Markdown, not Google Docs)
   b. Parse YAML frontmatter
   c. Check if `source_id == granola_id` already exists in Firestore → skip if yes
   d. Write to Firestore `knowledge_base`:

```
{
  type: "meeting_note",
  source: "granola",
  source_id: <granola_id>,
  source_url: null,
  title: <title from frontmatter>,
  content: <markdown body without frontmatter>,
  content_format: "markdown",
  meeting_series: <meeting-series from frontmatter>,
  meeting_date: <parsed from created_at>,
  participants: <participants from frontmatter>,
  tags: <tags from frontmatter>,
  area: <area from frontmatter>,
  sensitivity: "unreviewed",
  processing_status: "raw",
  owner_email: <from config or env var>,
  synced_at: <now>,
  created_at: SERVER_TIMESTAMP,
  updated_at: SERVER_TIMESTAMP,
}
```

3. Write sync metadata to `_sync_metadata/granola_sync`

### Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `GCP_PROJECT_ID` | Yes | Already configured |
| `GRANOLA_DRIVE_FOLDER_ID` | Yes | Google Drive folder containing Granola .md exports |
| `GRANOLA_OWNER_EMAIL` | No | Default owner email for synced docs |

### Schedule

Hourly via Cloud Scheduler (same pattern as meeting-notes-sync).

### Deduplication

Uses `granola_id` from frontmatter as `source_id`. The Firestore query `source == "granola" AND source_id == <granola_id>` prevents duplicates.

### File Format Handling

Granola files are raw Markdown uploaded to Drive (not Google Docs). The Drive API downloads them as-is using `files().get_media()` instead of `files().export()`. The YAML frontmatter is parsed with a simple split on `---` delimiters.

---

## Document-Processor Update

The existing document-processor Cloud Function needs one change: **preserve existing metadata from source-provided frontmatter** instead of overwriting.

### Current behavior

The LLM always generates tags, and they get merged with existing tags. But other fields (participants, meeting_date) are always overwritten by the processor's extraction.

### Updated behavior

```python
# For each field, only set if not already present from the sync source:
if not data.get("participants"):
    updates["participants"] = extracted_participants

if not data.get("meeting_date"):
    updates["meeting_date"] = parsed_date

# Tags are always merged (existing + LLM-generated)
updates["tags"] = list(dict.fromkeys(existing_tags + rule_tags + llm_tags))

# These fields are always set by LLM (Granola doesn't provide them):
updates["summary"] = llm_result.get("summary")
updates["action_items"] = llm_result.get("action_items")
updates["key_decisions"] = llm_result.get("key_decisions")
updates["meeting_type"] = llm_result.get("meeting_type")
updates["language"] = llm_result.get("language")
updates["sensitivity"] = llm_result.get("sensitivity")
```

This ensures Granola's rich frontmatter data (participants, tags, meeting-series, area) is preserved while the LLM adds what's missing (summary, action items, decisions, sensitivity).

---

## dam-mcp Cleanup

### Files to delete

- `dam_mcp/core/tools_query_kb.py`
- `dam_mcp/core/tools_get_document.py`
- `dam_mcp/core/tools_semantic_search.py`
- `tests/test_query_kb.py`
- `tests/test_get_document.py`
- `tests/test_semantic_search.py`

### Files to modify

- `dam_mcp/core/__init__.py` — remove imports of deleted tools
- `dam_mcp/core/firestore.py` — keep as-is (used by sync_status and internal tools)

### Note

The `firestore.py` in dam-mcp and knowledge-mcp will be independent copies. They share the same code but evolve independently. No shared package needed at this scale.

---

## Schema Addition

One new field for Granola-sourced documents:

| Field | Type | Description |
|-------|------|-------------|
| `area` | string | Granola organizational area (e.g. "finance/analytics-weekly", "engineering/erp") |

This field is optional and only populated for Granola-sourced documents. It provides an additional organizational dimension beyond tags and meeting_series.

---

## Deployment

### Granola-Sync Cloud Function

```bash
gcloud functions deploy granola-sync \
  --gen2 \
  --runtime=python312 \
  --region=europe-west3 \
  --source=dam-mcp/cloud_functions/granola_sync/ \
  --entry-point=sync_handler \
  --service-account=dam-mcp@gold-blueprint-357814.iam.gserviceaccount.com \
  --set-env-vars=GCP_PROJECT_ID=gold-blueprint-357814,GRANOLA_DRIVE_FOLDER_ID=<folder-id> \
  --trigger-http \
  --no-allow-unauthenticated \
  --timeout=300 \
  --memory=256Mi
```

### Cloud Scheduler

```bash
gcloud scheduler jobs create http granola-sync-hourly \
  --location=europe-west3 \
  --schedule="0 * * * *" \
  --uri=<function-url> \
  --oidc-service-account-email=dam-mcp@gold-blueprint-357814.iam.gserviceaccount.com \
  --http-method=POST
```

### knowledge-mcp (local)

```bash
cd knowledge-mcp
pip install -e .
python -m knowledge_mcp  # stdio transport
```

---

## Testing

### Unit Tests

- **knowledge-mcp tools:** Mock Firestore, verify query construction, result formatting. Same tests as current dam-mcp knowledge tool tests, moved to new location.
- **Granola-Sync:** Mock Drive API and Firestore. Verify: frontmatter parsed correctly, granola_id used for dedup, markdown body extracted without frontmatter, correct fields written to Firestore.
- **Document-Processor update:** Verify existing metadata preserved (participants, tags), LLM fields always written (summary, action_items).

### Integration Tests

- Upload a test Granola .md file to Drive → trigger sync → verify document in Firestore with correct frontmatter fields → verify processor enriches with summary/action_items while preserving tags/participants.

---

## Files to Create/Modify Summary

**New:**
- `knowledge-mcp/` — entire new server directory
- `cloud_functions/granola_sync/main.py` + `requirements.txt`

**Modified:**
- `cloud_functions/document_processor/main.py` — preserve existing metadata logic
- `dam-mcp/dam_mcp/core/__init__.py` — remove knowledge tool imports

**Deleted:**
- `dam-mcp/dam_mcp/core/tools_query_kb.py`
- `dam-mcp/dam_mcp/core/tools_get_document.py`
- `dam-mcp/dam_mcp/core/tools_semantic_search.py`
- `dam-mcp/tests/test_query_kb.py`
- `dam-mcp/tests/test_get_document.py`
- `dam-mcp/tests/test_semantic_search.py`
