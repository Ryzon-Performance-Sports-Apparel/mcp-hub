# Firestore Knowledge Base — Meeting Notes Sync Design

**Date:** 2026-04-07
**Status:** Draft — awaiting review

---

## Problem

Meeting notes from Google Meet are scattered across individual Google Drive folders. There is no centralized, structured store that LLMs, MCP tools, and other AI services can query. As AI use cases grow (beyond meeting notes to project briefs, brand guidelines, etc.), we need a foundational data layer that is:

- Queryable by tags, type, date, and series
- Access-controlled (PII-sensitive vs. general content)
- Extensible to new data types without schema changes
- Maintained by automated agents (tagging, flagging)

## Solution

Firestore as the canonical AI knowledge base, starting with Google Meeting Notes as the first data type. A Cloud Function pipeline syncs Google Docs from Drive folders (registered via a Google Sheet config) into Firestore. A separate Firestore-triggered agent processes each document (tagging, flagging). The dam-mcp server gets new query tools for LLM access.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Google Sheet (Config Registry)                             │
│  Columns: folder_id, owner_email, meeting_series,           │
│           sync_frequency, tags, sharing_confirmed            │
└────────────────────┬────────────────────────────────────────┘
                     │ reads config (Sheets API)
                     v
┌─────────────────────────────────────────────────────────────┐
│  Cloud Function: meeting-notes-sync (scheduled hourly)      │
│  1. Read Sheet → get registered folders                      │
│  2. Verify Drive access per folder (update sharing_confirmed)│
│  3. List Google Docs in each folder                          │
│  4. Deduplicate via source_id check in Firestore             │
│  5. Export new docs as plain text via Drive API              │
│  6. Write to Firestore knowledge_base (status: "raw")       │
│  7. Write sync metadata to Firestore                         │
└────────────────────┬────────────────────────────────────────┘
                     │ Firestore onCreate trigger
                     v
┌─────────────────────────────────────────────────────────────┐
│  Cloud Function: document-processor (Firestore trigger)     │
│  1. Triggered on new doc in knowledge_base                   │
│  2. Rule-based extraction: topics, participants, dates       │
│  3. Flag sensitivity (v1: all "unreviewed")                  │
│  4. Update processing_status → "processed"                   │
│  5. (Future: LLM-based tagging, PII filtering, reclassify   │
│     to knowledge_base_restricted)                            │
└─────────────────────────────────────────────────────────────┘
                     │
                     v
┌─────────────────────────────────────────────────────────────┐
│  dam-mcp (new Firestore query tools)                        │
│  - query_knowledge_base: search by tags, type, series, date │
│  - get_document: fetch full content by ID                    │
│  (Other consumers — LLMs, agents — also query Firestore)    │
└─────────────────────────────────────────────────────────────┘
```

---

## Firestore Schema

### Collections

Two top-level collections split by access sensitivity, sharing the same document schema:

- **`knowledge_base`** — general documents (default destination)
- **`knowledge_base_restricted`** — PII-containing or sensitive documents (future: agent moves docs here after PII detection)

### Document Schema

```
knowledge_base/{auto_id}
├── type: string                            // "meeting_note" (discriminator for future types)
├── source: string                          // "google_drive" (origin system)
├── source_id: string                       // Google Drive file ID (dedup key)
├── source_url: string                      // link back to original Google Doc
├── title: string                           // document title
├── content: string                         // full extracted plain text
├── content_format: string                  // "plain_text" (or "markdown" for future sources)
│
├── meeting_series: string | null           // from Sheet config; null for one-time meetings
├── meeting_date: Timestamp | null          // parsed from doc title/metadata
├── participants: string[] | null           // extracted by agent
│
├── tags: string[]                          // agent-assigned + default tags from Sheet
├── sensitivity: string                     // "unreviewed" | "safe" | "contains_pii"
├── processing_status: string               // "raw" | "processing" | "processed" | "failed"
│
├── owner_email: string                     // from Sheet config
├── synced_at: Timestamp                    // when sync job wrote this
├── processed_at: Timestamp | null          // when agent finished processing
├── created_at: Timestamp                   // Firestore server timestamp
└── updated_at: Timestamp                   // Firestore server timestamp
```

### Composite Indexes

| Fields | Purpose |
|--------|---------|
| `type` + `tags` (array-contains) + `created_at` desc | Tag-based queries sorted by date |
| `type` + `meeting_series` + `meeting_date` desc | Series-based chronological lookup |
| `processing_status` + `created_at` asc | Find unprocessed documents |
| `source` + `source_id` | Deduplication check during sync |

### Design Decisions

- **`source_id` as dedup key:** Same Drive file ID is never synced twice. Sync checks Firestore before writing.
- **`tags` as array:** Enables Firestore's `array-contains` and `array-contains-any` queries.
- **`meeting_series` for clustering:** Recurring meetings share a series identifier; one-time meetings have `null`.
- **Full content stored:** 1MB Firestore doc limit is more than sufficient for meeting notes text. Enables direct LLM context retrieval without round-tripping to Drive.
- **Type-agnostic schema:** Future data types (brand briefs, project docs, Granola notes) use the same structure with a different `type` value. No new collections needed unless a new access tier is required.

---

## Google Sheet Config

A Google Sheet serves as the human-friendly registry of Drive folders to sync. Non-technical team members can onboard by adding a row and sharing their folder with the service account.

### Columns

| Column | Type | Example | Description |
|--------|------|---------|-------------|
| `folder_id` | string | `1a2b3c4d` | Google Drive folder ID |
| `owner_email` | string | `simon@company.com` | Folder owner's email |
| `meeting_series` | string | `weekly-standup` | Series name for recurring meetings; blank for one-time |
| `sync_frequency` | string | `hourly` | How often to check (v1: all treated as hourly) |
| `tags` | string | `engineering, product` | Comma-separated default tags for all docs in folder |
| `sharing_confirmed` | boolean | `TRUE` | Auto-updated by sync job; confirms service account access |

### Onboarding Flow

1. User shares their Drive meeting notes folder with `dam-mcp@gold-blueprint-357814.iam.gserviceaccount.com` (Viewer access)
2. User adds a row to the config Sheet with folder_id, their email, and optional series/tags
3. Next sync run verifies access and sets `sharing_confirmed` to TRUE
4. Meeting notes start appearing in Firestore within the hour

---

## Sync Logic (Cloud Function: `meeting-notes-sync`)

### Algorithm

1. Read all rows from the config Sheet via Google Sheets API
2. For each row:
   a. If `sharing_confirmed` is empty: attempt to list folder, update Sheet cell to TRUE/FALSE
   b. If `sharing_confirmed` is FALSE: skip this folder, log warning
   c. List all Google Docs in the folder via Drive API (filter by mimeType `application/vnd.google-apps.document`)
   d. For each doc:
      - Query Firestore: does a document with `source_id` == drive_file_id exist?
      - If yes: skip (already synced)
      - If no: export Google Doc as plain text via Drive API, write to Firestore `knowledge_base` with:
        - `type`: "meeting_note"
        - `source`: "google_drive"
        - `source_id`: Drive file ID
        - `source_url`: Google Docs URL
        - `title`: doc title from Drive
        - `content`: exported plain text
        - `content_format`: "plain_text"
        - `meeting_series`: from Sheet row (or null)
        - `tags`: default tags from Sheet row
        - `owner_email`: from Sheet row
        - `processing_status`: "raw"
        - `sensitivity`: "unreviewed"
        - `synced_at`: current timestamp
        - `created_at`: server timestamp
        - `updated_at`: server timestamp
3. Write sync metadata to `_sync_metadata/meeting_notes_sync` document in Firestore:
   ```json
   {
     "last_sync_at": "2026-04-07T14:00:00Z",
     "folders_checked": 5,
     "new_docs_synced": 3,
     "skipped_existing": 42,
     "errors": [],
     "duration_seconds": 8.2
   }
   ```
4. Per-folder errors don't stop the overall sync — they're logged and included in the errors array.

### Deduplication

Simple equality query: `source` == "google_drive" AND `source_id` == drive_file_id. This is indexed and fast. No need for in-memory scans.

### Deletions

Not handled (same as Drive → GCS sync). If a doc is removed from Drive, it persists in Firestore. Firestore is the archive.

---

## Agent Processing (Cloud Function: `document-processor`)

### Trigger

Firestore `onCreate` on `knowledge_base/{docId}`.

### Algorithm (v1 — rule-based)

1. Read the new document
2. Set `processing_status` → "processing"
3. Extract participants: regex for email addresses in content
4. Extract meeting date: parse from title (common patterns like "YYYY-MM-DD", "April 7, 2026", etc.)
5. Extract topics for tags: keyword matching against a configurable topic list (e.g., "sprint", "roadmap", "hiring" → add matching tags)
6. Merge extracted tags with existing tags from the Sheet config (no duplicates)
7. Update document:
   - `participants`: extracted emails
   - `meeting_date`: parsed date (or null if unparsable)
   - `tags`: merged tag array
   - `sensitivity`: "unreviewed" (v1 — no PII detection)
   - `processing_status`: "processed"
   - `processed_at`: current timestamp
   - `updated_at`: current timestamp
8. On failure: set `processing_status` → "failed", log error

### Future Evolution

- **v2:** LLM-based tagging — call Claude API for intelligent topic extraction, summarization, and participant identification
- **v2:** PII detection — LLM flags personal content, agent moves document to `knowledge_base_restricted`
- **v3:** Content filtering — LLM removes off-topic personal discussions from meeting notes before making them queryable

---

## MCP Tools (dam-mcp)

### `query_knowledge_base`

```python
query_knowledge_base(
    type: Optional[str] = None,           # e.g., "meeting_note"
    tags: Optional[list[str]] = None,      # filter by tags (array-contains-any)
    meeting_series: Optional[str] = None,  # filter by series
    date_from: Optional[str] = None,       # ISO date, filter meeting_date >=
    date_to: Optional[str] = None,         # ISO date, filter meeting_date <=
    status: Optional[str] = "processed",   # filter by processing_status
    limit: Optional[int] = 20             # max results
) -> str  # JSON array of document metadata (no full content)
```

Returns metadata + truncated content preview (first 500 chars) for each match. Full content available via `get_document`.

### `get_document`

```python
get_document(
    document_id: str                       # Firestore document ID
) -> str  # JSON with full document including content
```

Returns all fields including complete content text.

### Note on Full-Text Search

Firestore does not natively support full-text content search. For v1, filtering by tags + series + date range covers most LLM use cases (the LLM can read full documents and reason about relevance). Future options:
- Firestore full-text search extension (Algolia/Typesense)
- Vector search via Firestore vector embeddings
- LLM-based retrieval: agent reads summaries, picks relevant docs

---

## Infrastructure & Deployment

### GCP Resources (project: `gold-blueprint-357814`)

| Resource | Type | Region | Details |
|----------|------|--------|---------|
| Firestore database | Native mode | europe-west3 | New — needs to be created |
| `meeting-notes-sync` | Cloud Function (gen2) | europe-west3 | HTTP-triggered, hourly via Cloud Scheduler |
| `document-processor` | Cloud Function (gen2) | europe-west3 | Firestore onCreate trigger |
| Cloud Scheduler job | `meeting-notes-sync-hourly` | europe-west3 | `0 * * * *` (hourly) |
| Google Sheet | N/A | N/A | Manually created, shared with service account |

### Service Account Permissions

Existing service account: `dam-mcp@gold-blueprint-357814.iam.gserviceaccount.com`

**New permissions needed:**
- `roles/datastore.user` — Firestore read/write
- Google Sheets API enabled on the project
- Service account needs Viewer access to the config Google Sheet

**Already configured:**
- Drive API access (from Drive → GCS sync)
- `roles/storage.objectAdmin` on GCS (unchanged)

### New Python Dependencies

- `google-cloud-firestore>=2.0.0` — Firestore client library
- `gspread>=6.0.0` — Google Sheets client (lightweight, uses service account auth)

### Directory Structure

```
dam-mcp/
  cloud_functions/
    drive_sync/                 # existing
    meeting_notes_sync/         # NEW
      main.py                   #   sync function entry point
      requirements.txt          #   google-cloud-firestore, gspread, google-api-python-client
    document_processor/         # NEW
      main.py                   #   Firestore trigger entry point
      requirements.txt          #   google-cloud-firestore
  dam_mcp/core/
    firestore.py                # NEW — Firestore client abstraction (shared by MCP tools)
    tools_query_kb.py           # NEW — query_knowledge_base MCP tool
    tools_get_document.py       # NEW — get_document MCP tool
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GCP_PROJECT_ID` | Yes | Already configured |
| `GOOGLE_APPLICATION_CREDENTIALS` | Yes | Already configured |
| `FIRESTORE_DATABASE` | No | Default: `(default)` — use default Firestore database |
| `CONFIG_SHEET_ID` | Yes (for sync) | Google Sheet ID for the config registry |
| `CONFIG_SHEET_NAME` | No | Sheet tab name (default: "Sheet1") |

### Deployment Commands

**Firestore:**
```bash
gcloud firestore databases create --location=europe-west3 --project=gold-blueprint-357814
```

**meeting-notes-sync Cloud Function:**
```bash
gcloud functions deploy meeting-notes-sync \
  --gen2 \
  --runtime=python312 \
  --region=europe-west3 \
  --source=dam-mcp/cloud_functions/meeting_notes_sync/ \
  --entry-point=sync_handler \
  --service-account=dam-mcp@gold-blueprint-357814.iam.gserviceaccount.com \
  --set-env-vars=GCP_PROJECT_ID=gold-blueprint-357814,CONFIG_SHEET_ID=<sheet-id> \
  --trigger-http \
  --no-allow-unauthenticated \
  --timeout=300 \
  --memory=256Mi
```

**document-processor Cloud Function:**
```bash
gcloud functions deploy document-processor \
  --gen2 \
  --runtime=python312 \
  --region=europe-west3 \
  --source=dam-mcp/cloud_functions/document_processor/ \
  --entry-point=process_document \
  --service-account=dam-mcp@gold-blueprint-357814.iam.gserviceaccount.com \
  --set-env-vars=GCP_PROJECT_ID=gold-blueprint-357814 \
  --trigger-event-filters="type=google.cloud.firestore.document.v1.created" \
  --trigger-event-filters="database=(default)" \
  --trigger-event-filters-path-pattern="document=knowledge_base/{docId}" \
  --no-allow-unauthenticated \
  --timeout=60 \
  --memory=256Mi
```

**Cloud Scheduler:**
```bash
gcloud scheduler jobs create http meeting-notes-sync-hourly \
  --location=europe-west3 \
  --schedule="0 * * * *" \
  --uri=<meeting-notes-sync-function-url> \
  --oidc-service-account-email=dam-mcp@gold-blueprint-357814.iam.gserviceaccount.com \
  --http-method=POST
```

---

## Testing

### Unit Tests

- **Sync function:** Mock Sheets API, Drive API, and Firestore. Verify: new docs synced, existing docs skipped, Sheet `sharing_confirmed` updated, sync metadata written.
- **Document processor:** Mock Firestore. Verify: participants extracted, dates parsed, tags merged, processing_status transitions.
- **MCP tools:** Mock Firestore queries. Verify: correct query construction, result formatting, parameter validation.

### Integration Tests (e2e)

- Create a test Google Sheet + test Drive folder with known Google Docs
- Run sync function → verify documents appear in Firestore with correct schema
- Verify document-processor trigger fires and processes the documents
- Query via MCP tools → verify results match expected data

---

## Scope & Future Roadmap

### v1 (this spec)
- Google Sheet config registry
- Drive → Firestore sync Cloud Function (hourly)
- Rule-based document processor (tags, participants, dates)
- Two Firestore query tools in dam-mcp
- Two collections: `knowledge_base` + `knowledge_base_restricted`

### v2
- Granola.ai sync (from GitHub as source)
- LLM-based tagging and summarization
- PII detection and automatic reclassification to `knowledge_base_restricted`
- Vector embeddings for semantic search

### v3
- Personal content filtering from meeting notes
- Cross-type search and knowledge graph
- Approval workflows for sensitive content
- Additional data types (brand guidelines, project briefs, customer feedback)
