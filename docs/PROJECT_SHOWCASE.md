# Ryzon AI Platform — Project Overview

> Making advertising, creative assets, and team knowledge accessible to AI — so your team can focus on strategy, not manual work.

---

## What Is This?

This platform connects **AI assistants** (like Claude) to the tools your team already uses: **Meta Ads**, **Google Ads**, **Google Drive**, **Figma**, and **meeting notes**. Instead of clicking through ad dashboards or digging through shared folders, you simply _ask_ the AI to do it for you.

```
You:    "Create a new Meta ad campaign for our summer collection,
         use the hero image from the DAM, target cycling enthusiasts
         in Germany, and set a daily budget of €50."

Claude: Done. Campaign "Summer Collection 2026" is live.
        Used hero-1080x1080.png from the Summer-2026 folder.
        Targeting 1.2M cycling enthusiasts in DE.
        Daily budget: €50. Here's the preview link: ...
```

No dashboards. No manual uploads. No copy-pasting between tools.

---

## The Big Picture

```mermaid
graph TB
    subgraph "People"
        User["Team Member"]
        Designer["Designer"]
    end

    subgraph "AI Layer"
        Claude["Claude AI Assistant"]
    end

    subgraph "MCP Servers — the bridges between AI and your tools"
        META["Meta Ads Server"]
        GADS["Google Ads Server"]
        DAM["Digital Asset Manager"]
    end

    subgraph "External Platforms"
        FB["Meta / Facebook / Instagram"]
        GOOGLE["Google Ads"]
        DRIVE["Google Drive"]
        FIGMA["Figma"]
        FIRESTORE["Knowledge Base"]
    end

    User -->|"talks to"| Claude
    Designer -->|"uploads to"| DRIVE
    Designer -->|"designs in"| FIGMA

    Claude -->|"manages ads"| META
    Claude -->|"manages ads"| GADS
    Claude -->|"finds assets & knowledge"| DAM

    META -->|"creates & edits"| FB
    GADS -->|"creates & edits"| GOOGLE
    DAM -->|"syncs from"| DRIVE
    DAM -->|"exports from"| FIGMA
    DAM -->|"stores & searches"| FIRESTORE

    style Claude fill:#8B5CF6,color:#fff
    style META fill:#1877F2,color:#fff
    style GADS fill:#4285F4,color:#fff
    style DAM fill:#10B981,color:#fff
```

**How it works:** Claude talks to three specialized servers. Each server is an expert in one domain — ads, assets, or knowledge. The servers handle all the technical details (APIs, authentication, data formats) so Claude can focus on understanding your intent.

---

## The Three Servers

### 1. Meta Ads Server

> Everything you need to run Facebook and Instagram advertising — from campaign creation to performance reporting.

```mermaid
graph LR
    subgraph "What you can do"
        A["Create campaigns"]
        B["Build ad creatives"]
        C["Define audiences"]
        D["Check performance"]
        E["Duplicate & edit"]
    end

    subgraph "36 tools including"
        T1["create_campaign"]
        T2["create_ad_creative"]
        T3["get_insights"]
        T4["search_interests"]
        T5["upload_ad_image"]
        T6["estimate_audience_size"]
    end

    A --> T1
    B --> T2
    C --> T4
    D --> T3
    E --> T5

    style A fill:#1877F2,color:#fff
    style B fill:#1877F2,color:#fff
    style C fill:#1877F2,color:#fff
    style D fill:#1877F2,color:#fff
    style E fill:#1877F2,color:#fff
```

**Key capabilities:**
- Full campaign lifecycle — create, edit, pause, duplicate, delete
- All creative formats — single image, carousel, video, dynamic ads
- Audience targeting — interests, behaviors, demographics, locations, lookalikes
- Performance insights — spend, impressions, clicks, conversions, ROAS
- Image management — upload, manage, and use images in ads
- Ryzon-specific defaults — pre-configured tracking, UTM parameters, and DSA compliance

---

### 2. Google Ads Server

> Manage Google search and display advertising through natural conversation.

**Key capabilities:**
- Campaign and ad group management
- Keyword and audience targeting
- Performance reporting via GAQL queries
- Budget and bid management

---

### 3. Digital Asset Manager (DAM)

> Your creative assets and team knowledge — organized, searchable, and ready for AI.

```mermaid
graph TB
    subgraph "Asset Sources"
        DRIVE["Google Drive\n(designer uploads)"]
        FIGMA["Figma\n(design exports)"]
        DIRECT["Direct Upload\n(programmatic)"]
    end

    subgraph "Knowledge Sources"
        GMEET["Google Meet Notes"]
        SHEET["Config Sheet\n(folder registry)"]
    end

    subgraph "DAM Server — 12 tools"
        direction TB
        SYNC["Sync Engine"]
        ASSETS["Asset Tools\n• list, search, get\n• upload, tag\n• download URL"]
        KB["Knowledge Tools\n• query by tags/dates\n• semantic search\n• get full document"]
    end

    subgraph "Storage"
        GCS["Cloud Storage\n(images & files)"]
        FS["Firestore\n(knowledge base)"]
    end

    DRIVE -->|"hourly sync"| SYNC
    FIGMA -->|"export frames"| SYNC
    DIRECT --> ASSETS
    GMEET -->|"hourly sync"| SYNC
    SHEET -->|"tells sync\nwhat to watch"| SYNC

    SYNC --> GCS
    SYNC --> FS
    ASSETS --> GCS
    KB --> FS

    style SYNC fill:#10B981,color:#fff
    style ASSETS fill:#10B981,color:#fff
    style KB fill:#10B981,color:#fff
```

**Asset management tools:**
| Tool | What it does |
|------|-------------|
| `list_assets` | Browse assets by campaign or folder |
| `search_assets` | Find assets by name, tags, format, or dimensions |
| `get_asset` | Get full metadata for a specific asset |
| `get_asset_download_url` | Generate a secure download link (expires in 60 min) |
| `upload_asset` | Upload a new image or file |
| `tag_asset` | Add or update tags and metadata |
| `export_figma_frames` | Export frames from Figma directly to the DAM |
| `trigger_sync` | Manually start a Drive-to-DAM sync |
| `sync_status` | Check when the last sync ran |

**Knowledge base tools:**
| Tool | What it does |
|------|-------------|
| `query_knowledge_base` | Search meeting notes by tags, date, series, or type |
| `get_document` | Retrieve the full content of a specific document |
| `search_knowledge_base_semantic` | Find documents using natural language (AI-powered) |

---

## The Knowledge Base — How Meeting Notes Become Searchable

One of the most powerful features: your team's meeting notes are automatically collected, enriched by AI, and made searchable.

```mermaid
sequenceDiagram
    participant Team as Team Member
    participant Drive as Google Drive
    participant Sheet as Config Sheet
    participant Sync as Sync Engine
    participant LLM as Claude Haiku AI
    participant Voyage as Voyage AI
    participant DB as Knowledge Base

    Team->>Drive: Takes meeting notes (Google Docs)
    Team->>Sheet: Registers folder (one-time setup)

    loop Every hour
        Sync->>Sheet: Read registered folders
        Sync->>Drive: Check for new documents
        Sync->>DB: Save new documents
    end

    Note over LLM,DB: Automatic enrichment (triggered instantly)

    DB->>LLM: New document arrives
    LLM->>LLM: Analyze content
    LLM->>DB: Add summary, tags, action items,<br/>decisions, meeting type, language
    DB->>Voyage: Generate semantic embedding
    Voyage->>DB: Store vector for search

    Note over LLM,DB: PII check
    LLM-->>DB: If personal data detected,<br/>move to restricted collection
```

### What the AI extracts from each meeting note

| Field | Example |
|-------|---------|
| **Summary** | "Team reviewed Q2 roadmap priorities and decided to focus on mobile-first approach" |
| **Tags** | `q2-roadmap`, `mobile`, `product-strategy` |
| **Action items** | "Simon to draft mobile spec by April 14" |
| **Key decisions** | "Mobile-first approach for Q2", "Postpone desktop redesign" |
| **Meeting type** | Planning, Standup, Review, Retro, 1:1, Demo, etc. |
| **Language** | German, English, etc. |
| **Sensitivity** | Safe or Contains PII (personal data) |

### Two types of search

**Tag-based search** — fast, exact matching:
> "Show me all planning meetings tagged with 'erp-selection' from March"

**Semantic search** — AI-powered, finds related content by meaning:
> "What did we discuss about customer onboarding?"
> _(Finds notes even if they never mention "onboarding" — maybe they talked about "new customer setup" or "Kundeneinrichtung")_

---

## How Designers Fit In

Designers don't need to change anything about how they work.

```mermaid
graph LR
    subgraph "Designer's workflow (unchanged)"
        D1["Design in Figma"]
        D2["Export to Google Drive"]
    end

    subgraph "What happens automatically"
        D3["Sync picks up new files"]
        D4["Assets appear in the DAM"]
        D5["AI can use them in ads"]
    end

    D1 -->|"or export directly"| D4
    D2 --> D3 --> D4 --> D5

    style D1 fill:#F24E1E,color:#fff
    style D2 fill:#4285F4,color:#fff
    style D3 fill:#10B981,color:#fff
    style D4 fill:#10B981,color:#fff
    style D5 fill:#8B5CF6,color:#fff
```

- Designers keep uploading to Google Drive as usual
- The DAM automatically syncs new files every hour
- Figma frames can be exported directly into the DAM
- Assets get tagged and become searchable instantly

---

## Onboarding — For Everyone

### For team members (meeting notes)

1. **Share** your meeting notes Drive folder with the service account
2. **Add a row** to the config spreadsheet (folder ID + your email)
3. **Done** — your notes will sync within the hour

### For Claude Desktop users

Run one command in Terminal:

```bash
curl -fsSL https://raw.githubusercontent.com/.../install.sh | bash
```

The installer handles everything:
- Checks for Python and required tools
- Installs the MCP servers
- Configures Claude Desktop
- Sets up API credentials
- Provides a step-by-step guide for any manual steps

---

## Infrastructure — Where Things Run

```mermaid
graph TB
    subgraph "Google Cloud Platform (europe-west3)"
        subgraph "Always Running"
            CR["Cloud Run\n(DAM Server)"]
        end

        subgraph "Runs on Schedule"
            CF1["Meeting Notes Sync\n(every hour)"]
            CF2["Drive Asset Sync\n(every hour)"]
        end

        subgraph "Runs on Events"
            CF3["Document Processor\n(when new doc arrives)"]
        end

        subgraph "Storage"
            GCS["Cloud Storage\n(images & files)"]
            FS["Firestore\n(knowledge base)"]
        end
    end

    subgraph "External APIs"
        META_API["Meta Graph API"]
        CLAUDE_API["Claude AI API"]
        VOYAGE_API["Voyage AI API"]
        DRIVE_API["Google Drive API"]
        SHEETS_API["Google Sheets API"]
    end

    CF1 --> FS
    CF1 --> DRIVE_API
    CF1 --> SHEETS_API
    CF2 --> GCS
    CF2 --> DRIVE_API
    CF3 --> FS
    CF3 --> CLAUDE_API
    CF3 --> VOYAGE_API
    CR --> GCS
    CR --> FS

    style CR fill:#4285F4,color:#fff
    style CF1 fill:#34A853,color:#fff
    style CF2 fill:#34A853,color:#fff
    style CF3 fill:#FBBC04,color:#000
    style GCS fill:#4285F4,color:#fff
    style FS fill:#FF6F00,color:#fff
```

**Cost:** Minimal. Cloud Functions are pay-per-use. Firestore and Cloud Storage cost cents per month at current scale. LLM processing costs ~$0.001 per meeting note.

---

## Data Privacy & Security

```mermaid
graph TB
    subgraph "General Access"
        KB["Knowledge Base\n(safe documents)"]
    end

    subgraph "Restricted Access"
        KBR["Restricted Collection\n(PII-flagged documents)"]
    end

    DOC["New Meeting Note"] --> AI["AI Privacy Check"]
    AI -->|"No personal data"| KB
    AI -->|"Contains personal data\n(salary, health, etc.)"| KBR

    style KB fill:#10B981,color:#fff
    style KBR fill:#EF4444,color:#fff
    style AI fill:#8B5CF6,color:#fff
```

- AI automatically scans every document for personal data
- Documents with sensitive content are moved to a restricted collection
- Business emails and professional names are **not** flagged (only truly personal data)
- Different access levels can be applied to each collection
- All data stays in the EU (europe-west3 region)

---

## What's Next

| Phase | Status | What it adds |
|-------|--------|-------------|
| **Phase 1** — Asset management | Done | Drive sync, asset search, Figma export |
| **Phase 2** — AI enrichment | Done | LLM tagging, summaries, vector search, PII detection |
| **Phase 3** — More sources | Planned | Granola.ai notes, brand guidelines, project briefs |
| **Phase 4** — Workflows | Planned | Approval flows, versioning, cross-type knowledge graph |

---

## Quick Reference

| Server | Tools | Purpose |
|--------|-------|---------|
| Meta Ads MCP | 36 | Create, manage, and analyze Facebook/Instagram ads |
| Google Ads MCP | 10+ | Create, manage, and analyze Google ads |
| DAM MCP | 12 | Manage creative assets and team knowledge |

| Automation | Frequency | What it does |
|-----------|-----------|-------------|
| Drive Asset Sync | Hourly | Copies new images from Drive to the DAM |
| Meeting Notes Sync | Hourly | Copies new meeting notes to the knowledge base |
| Document Processor | Instant | AI-enriches new documents (tags, summary, embeddings) |

---

*Built by the Ryzon team. Powered by Claude, Meta APIs, Google APIs, Figma, and a lot of automation.*
