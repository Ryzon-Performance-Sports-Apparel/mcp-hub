# Knowledge MCP Server + Granola Sync — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a standalone `knowledge-mcp` server for querying the Firestore knowledge base, add a Granola-Sync Cloud Function, update the document-processor to preserve source metadata, and remove knowledge tools from dam-mcp.

**Architecture:** New `knowledge-mcp/` directory in the monorepo with FastMCP server. Tools are copies of the existing dam-mcp knowledge tools (query, get, semantic search) with their own Firestore client. Granola-Sync is a new Cloud Function that reads Markdown files with YAML frontmatter from Google Drive and writes them to Firestore. The existing document-processor is updated to preserve metadata already provided by source systems.

**Tech Stack:** Python 3.12, FastMCP, Google Cloud Firestore, Voyage AI, functions-framework, PyYAML

**Spec:** `docs/superpowers/specs/2026-04-08-knowledge-mcp-design.md`

**Granola Drive Folder ID:** `1GEbGQEnvu6x4EU-xhEa5PZB-4KV4TZfW`

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `knowledge-mcp/knowledge_mcp/__init__.py` | Create | Package init, version, entrypoint |
| `knowledge-mcp/knowledge_mcp/core/__init__.py` | Create | Tool registration imports |
| `knowledge-mcp/knowledge_mcp/core/server.py` | Create | FastMCP("knowledge"), CLI |
| `knowledge-mcp/knowledge_mcp/core/config.py` | Create | KnowledgeConfig singleton |
| `knowledge-mcp/knowledge_mcp/core/utils.py` | Create | Logger setup |
| `knowledge-mcp/knowledge_mcp/core/firestore.py` | Create | Firestore client (copy from dam-mcp) |
| `knowledge-mcp/knowledge_mcp/core/tools_query.py` | Create | query_knowledge_base tool |
| `knowledge-mcp/knowledge_mcp/core/tools_get.py` | Create | get_document tool |
| `knowledge-mcp/knowledge_mcp/core/tools_semantic.py` | Create | search_knowledge_base_semantic tool |
| `knowledge-mcp/pyproject.toml` | Create | Package config + dependencies |
| `knowledge-mcp/tests/conftest.py` | Create | Test fixtures |
| `knowledge-mcp/tests/test_tools.py` | Create | Tool tests |
| `dam-mcp/cloud_functions/granola_sync/main.py` | Create | Granola sync Cloud Function |
| `dam-mcp/cloud_functions/granola_sync/requirements.txt` | Create | Dependencies |
| `dam-mcp/cloud_functions/document_processor/main.py` | Modify | Preserve source metadata |
| `dam-mcp/dam_mcp/core/__init__.py` | Modify | Remove knowledge tool imports |
| `dam-mcp/tests/test_granola_sync.py` | Create | Granola sync tests |

**Files to delete from dam-mcp:**
- `dam_mcp/core/tools_query_kb.py`
- `dam_mcp/core/tools_get_document.py`
- `dam_mcp/core/tools_semantic_search.py`
- `tests/test_query_kb.py`
- `tests/test_get_document.py`
- `tests/test_semantic_search.py`

---

### Task 1: Scaffold knowledge-mcp server

**Files:**
- Create: `knowledge-mcp/knowledge_mcp/__init__.py`
- Create: `knowledge-mcp/knowledge_mcp/core/__init__.py`
- Create: `knowledge-mcp/knowledge_mcp/core/server.py`
- Create: `knowledge-mcp/knowledge_mcp/core/config.py`
- Create: `knowledge-mcp/knowledge_mcp/core/utils.py`
- Create: `knowledge-mcp/knowledge_mcp/core/firestore.py`
- Create: `knowledge-mcp/pyproject.toml`

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p knowledge-mcp/knowledge_mcp/core knowledge-mcp/tests
```

- [ ] **Step 2: Create `knowledge-mcp/pyproject.toml`**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "knowledge-mcp"
version = "0.1.0"
description = "Knowledge Base MCP server — search and retrieve documents from the central Firestore knowledge base"
readme = "README.md"
requires-python = ">=3.10"

dependencies = [
    "mcp[cli]>=1.12.0",
    "google-cloud-firestore>=2.0.0",
    "google-auth>=2.0.0",
    "voyageai>=0.3.0",
    "python-dotenv>=1.1.0",
    "pytest>=8.4.1",
    "pytest-asyncio>=1.0.0",
]

[project.scripts]
knowledge-mcp = "knowledge_mcp:entrypoint"

[tool.hatch.build.targets.wheel]
packages = ["knowledge_mcp"]

[tool.pytest.ini_options]
markers = [
    "e2e: marks tests as end-to-end - excluded from default runs",
]
addopts = "-v --strict-markers -m 'not e2e'"
testpaths = ["tests"]
asyncio_mode = "auto"
```

- [ ] **Step 3: Create `knowledge-mcp/knowledge_mcp/__init__.py`**

```python
"""
Knowledge MCP - Knowledge Base MCP Server

Search and retrieve documents from the central Firestore knowledge base.
"""

from knowledge_mcp.core.server import main

__version__ = "0.1.0"


def entrypoint():
    """Main entry point for the package."""
    return main()
```

- [ ] **Step 4: Create `knowledge-mcp/knowledge_mcp/core/utils.py`**

```python
"""Utilities for the Knowledge MCP server."""

import logging
import pathlib
import platform
import os


def _get_log_dir() -> pathlib.Path:
    if platform.system() == "Darwin":
        base = pathlib.Path.home() / "Library" / "Application Support"
    elif platform.system() == "Windows":
        base = pathlib.Path(os.environ.get("APPDATA", pathlib.Path.home()))
    else:
        base = pathlib.Path.home() / ".config"
    log_dir = base / "knowledge-mcp"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def _setup_logger() -> logging.Logger:
    _logger = logging.getLogger("knowledge_mcp")
    _logger.setLevel(logging.DEBUG)
    try:
        log_path = _get_log_dir() / "knowledge_mcp_debug.log"
        handler = logging.FileHandler(str(log_path), encoding="utf-8")
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        _logger.addHandler(handler)
    except Exception:
        pass
    return _logger


logger = _setup_logger()
```

- [ ] **Step 5: Create `knowledge-mcp/knowledge_mcp/core/config.py`**

```python
"""Configuration for the Knowledge MCP server."""

import os
from dotenv import load_dotenv

load_dotenv()


class KnowledgeConfig:
    """Singleton configuration loaded from environment variables."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._loaded = False
        return cls._instance

    def __init__(self):
        if self._loaded:
            return
        self._loaded = True

        self.gcp_project_id = os.environ.get("GCP_PROJECT_ID", "")
        self.firestore_database = os.environ.get("FIRESTORE_DATABASE", "(default)")

    @property
    def is_configured(self) -> bool:
        return bool(self.gcp_project_id)

    def validate(self) -> str | None:
        """Returns an error message if required config is missing, else None."""
        if not self.gcp_project_id:
            return "Missing required environment variable: GCP_PROJECT_ID"
        return None


config = KnowledgeConfig()
```

- [ ] **Step 6: Create `knowledge-mcp/knowledge_mcp/core/server.py`**

```python
"""MCP server configuration for Knowledge Base."""

import argparse
import sys

from mcp.server.fastmcp import FastMCP

from .utils import logger

mcp_server = FastMCP("knowledge")


def main():
    """Main entry point for the Knowledge MCP server."""
    logger.info("Knowledge MCP server starting")

    parser = argparse.ArgumentParser(
        description="Knowledge MCP Server - Knowledge Base via Model Context Protocol"
    )
    parser.add_argument("--version", action="store_true", help="Show version")

    args = parser.parse_args()

    if args.version:
        from knowledge_mcp import __version__
        print(f"Knowledge MCP v{__version__}")
        return 0

    logger.info("Starting MCP server with stdio transport")
    mcp_server.run(transport="stdio")
```

- [ ] **Step 7: Create `knowledge-mcp/knowledge_mcp/core/firestore.py`**

Copy the full contents of `dam-mcp/dam_mcp/core/firestore.py` but change the import:

```python
"""Firestore client wrapper for the Knowledge MCP server."""

import json as _json
from datetime import datetime, timezone
from typing import Any

from google.cloud import firestore
from google.cloud.firestore_v1.vector import Vector
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure

from .config import config
from .utils import logger

_client: firestore.Client | None = None

COLLECTION_GENERAL = "knowledge_base"
COLLECTION_RESTRICTED = "knowledge_base_restricted"


def get_client() -> firestore.Client:
    global _client
    if _client is None:
        _client = firestore.Client(
            project=config.gcp_project_id,
            database=config.firestore_database,
        )
        logger.info(
            f"Firestore client created for project {config.gcp_project_id}, "
            f"database {config.firestore_database}"
        )
    return _client


def get_document(
    document_id: str,
    collection: str = COLLECTION_GENERAL,
) -> dict[str, Any] | None:
    """Get a single document by ID. Returns None if not found."""
    client = get_client()
    doc = client.collection(collection).document(document_id).get()
    if not doc.exists:
        return None
    data = doc.to_dict()
    data["id"] = doc.id
    return data


def query_documents(
    collection: str = COLLECTION_GENERAL,
    doc_type: str | None = None,
    tags: list[str] | None = None,
    meeting_series: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    status: str | None = "processed",
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Query documents with optional filters."""
    client = get_client()
    query = client.collection(collection)

    if doc_type:
        query = query.where("type", "==", doc_type)
    if tags:
        if len(tags) == 1:
            query = query.where("tags", "array_contains", tags[0])
        else:
            query = query.where("tags", "array_contains_any", tags[:30])
    if meeting_series:
        query = query.where("meeting_series", "==", meeting_series)
    if status:
        query = query.where("processing_status", "==", status)
    if date_from:
        query = query.where("meeting_date", ">=", date_from)
    if date_to:
        query = query.where("meeting_date", "<=", date_to)

    query = query.order_by("created_at", direction=firestore.Query.DESCENDING)
    query = query.limit(limit)

    results = []
    for doc in query.stream():
        data = doc.to_dict()
        data["id"] = doc.id
        results.append(data)
    return results


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
        data.pop("embedding", None)
        results.append(data)
    return results


def _serialize_for_json(obj: Any) -> Any:
    """Convert Firestore types to JSON-serializable types."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _serialize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize_for_json(v) for v in obj]
    return obj


def document_to_json(doc: dict[str, Any], include_content: bool = True) -> dict:
    """Convert a Firestore document dict to a JSON-safe dict."""
    result = _serialize_for_json(doc)
    if not include_content and "content" in result:
        content = result["content"] or ""
        if len(content) > 500:
            result["content_preview"] = content[:500] + "..."
            del result["content"]
        else:
            result["content_preview"] = content
            del result["content"]
    return result
```

- [ ] **Step 8: Commit scaffold**

```bash
cd /Users/simonheinken/Documents/projects/meta/mcp
git add knowledge-mcp/
git commit -m "feat: scaffold knowledge-mcp server with Firestore client"
```

---

### Task 2: Add knowledge-mcp tools and tests

**Files:**
- Create: `knowledge-mcp/knowledge_mcp/core/tools_query.py`
- Create: `knowledge-mcp/knowledge_mcp/core/tools_get.py`
- Create: `knowledge-mcp/knowledge_mcp/core/tools_semantic.py`
- Create: `knowledge-mcp/knowledge_mcp/core/__init__.py`
- Create: `knowledge-mcp/tests/conftest.py`
- Create: `knowledge-mcp/tests/test_tools.py`

- [ ] **Step 1: Create `knowledge-mcp/knowledge_mcp/core/tools_query.py`**

```python
"""query_knowledge_base tool — search documents in the Firestore knowledge base."""

import json
from datetime import datetime, timezone
from typing import Optional

from .config import config
from .firestore import document_to_json, query_documents
from .server import mcp_server


@mcp_server.tool()
async def query_knowledge_base(
    type: Optional[str] = None,
    tags: Optional[list[str]] = None,
    meeting_series: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    status: Optional[str] = "processed",
    limit: int = 20,
) -> str:
    """Search documents in the knowledge base by type, tags, meeting series, or date range.

    Returns metadata and a content preview (first 500 chars) for each match.
    Use get_document to fetch the full content of a specific document.

    Args:
        type: Document type filter (e.g. "meeting_note")
        tags: Filter by tags (matches any of the provided tags)
        meeting_series: Filter by meeting series name (e.g. "weekly-standup")
        date_from: ISO date string, filter meeting_date >= this date
        date_to: ISO date string, filter meeting_date <= this date
        status: Filter by processing_status (default: "processed")
        limit: Maximum results to return (default: 20)
    """
    error = config.validate()
    if error:
        return json.dumps({"error": error}, indent=2)

    parsed_from = None
    parsed_to = None
    if date_from:
        try:
            parsed_from = datetime.fromisoformat(date_from).replace(tzinfo=timezone.utc)
        except ValueError:
            return json.dumps({"error": f"Invalid date_from format: {date_from}"}, indent=2)
    if date_to:
        try:
            parsed_to = datetime.fromisoformat(date_to).replace(tzinfo=timezone.utc)
        except ValueError:
            return json.dumps({"error": f"Invalid date_to format: {date_to}"}, indent=2)

    docs = query_documents(
        doc_type=type,
        tags=tags,
        meeting_series=meeting_series,
        date_from=parsed_from,
        date_to=parsed_to,
        status=status,
        limit=limit,
    )

    results = [document_to_json(doc, include_content=False) for doc in docs]
    return json.dumps({"documents": results, "count": len(results)}, indent=2)
```

- [ ] **Step 2: Create `knowledge-mcp/knowledge_mcp/core/tools_get.py`**

```python
"""get_document tool — fetch a full document from the knowledge base."""

import json

from .config import config
from .firestore import document_to_json, get_document as fs_get_document
from .server import mcp_server


@mcp_server.tool()
async def get_document(document_id: str) -> str:
    """Get a full document from the knowledge base by its ID.

    Returns all fields including the complete content text.

    Args:
        document_id: Firestore document ID
    """
    error = config.validate()
    if error:
        return json.dumps({"error": error}, indent=2)

    doc = fs_get_document(document_id)
    if doc is None:
        return json.dumps({"error": f"Document not found: {document_id}"}, indent=2)

    return json.dumps(document_to_json(doc, include_content=True), indent=2)
```

- [ ] **Step 3: Create `knowledge-mcp/knowledge_mcp/core/tools_semantic.py`**

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
            texts=[query],
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

- [ ] **Step 4: Create `knowledge-mcp/knowledge_mcp/core/__init__.py`**

```python
"""Core functionality for Knowledge MCP server."""

from .server import mcp_server, main

# Import tool modules to trigger @mcp_server.tool() registration
from .tools_query import query_knowledge_base
from .tools_get import get_document
from .tools_semantic import search_knowledge_base_semantic
```

- [ ] **Step 5: Create `knowledge-mcp/tests/conftest.py`**

```python
"""Shared test fixtures for Knowledge MCP tests."""

import pytest
from knowledge_mcp.core.config import config


@pytest.fixture(autouse=True)
def mock_config():
    """Set env vars so KnowledgeConfig.validate() passes in all tests."""
    old_project = config.gcp_project_id
    config.gcp_project_id = "test-project"
    yield config
    config.gcp_project_id = old_project
```

- [ ] **Step 6: Create `knowledge-mcp/tests/test_tools.py`**

```python
"""Tests for Knowledge MCP tools."""

import json
import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

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
    mock_docs = [
        {
            "id": "doc1",
            "title": "Sprint Planning",
            "content": "We planned the sprint.",
            "tags": ["sprint"],
            "created_at": datetime(2026, 4, 7, tzinfo=timezone.utc),
        }
    ]
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
```

- [ ] **Step 7: Install and run tests**

```bash
cd /Users/simonheinken/Documents/projects/meta/mcp/knowledge-mcp
pip install -e .
python -m pytest tests/ -v
```
Expected: ALL PASSED

- [ ] **Step 8: Commit**

```bash
cd /Users/simonheinken/Documents/projects/meta/mcp
git add knowledge-mcp/
git commit -m "feat: add knowledge-mcp tools and tests"
```

---

### Task 3: Create Granola-Sync Cloud Function

**Files:**
- Create: `dam-mcp/cloud_functions/granola_sync/main.py`
- Create: `dam-mcp/cloud_functions/granola_sync/requirements.txt`
- Create: `dam-mcp/tests/test_granola_sync.py`

- [ ] **Step 1: Create `dam-mcp/cloud_functions/granola_sync/requirements.txt`**

```
functions-framework==3.*
google-cloud-firestore>=2.0.0
google-api-python-client>=2.0.0
google-auth>=2.0.0
pyyaml>=6.0.0
```

- [ ] **Step 2: Create `dam-mcp/cloud_functions/granola_sync/main.py`**

```python
"""Cloud Function entry point for scheduled Granola meeting notes sync from Google Drive to Firestore."""

import json
import os
import re
import time
from datetime import datetime, timezone

import functions_framework
import yaml
from google.cloud import firestore
from google.oauth2 import service_account
from googleapiclient.discovery import build

DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
COLLECTION = "knowledge_base"
SYNC_METADATA_COLLECTION = "_sync_metadata"
SYNC_METADATA_DOC = "granola_sync"
FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _get_config():
    return {
        "project_id": os.environ["GCP_PROJECT_ID"],
        "folder_id": os.environ["GRANOLA_DRIVE_FOLDER_ID"],
        "owner_email": os.environ.get("GRANOLA_OWNER_EMAIL", ""),
        "firestore_database": os.environ.get("FIRESTORE_DATABASE", "(default)"),
    }


def _get_credentials():
    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if creds_path:
        return service_account.Credentials.from_service_account_file(
            creds_path, scopes=DRIVE_SCOPES
        )
    import google.auth
    credentials, _ = google.auth.default(scopes=DRIVE_SCOPES)
    return credentials


def _get_drive_service(credentials):
    return build("drive", "v3", credentials=credentials)


def _get_firestore_client(cfg):
    return firestore.Client(project=cfg["project_id"], database=cfg["firestore_database"])


def _list_markdown_files(drive_service, folder_id):
    """List all .md files in a Drive folder."""
    results = []
    page_token = None
    while True:
        resp = drive_service.files().list(
            q=f"'{folder_id}' in parents and trashed = false and name contains '.md'",
            fields="nextPageToken, files(id, name)",
            pageSize=1000,
            pageToken=page_token,
        ).execute()
        results.extend(resp.get("files", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return results


def _download_file(drive_service, file_id):
    """Download raw file content from Drive."""
    return drive_service.files().get_media(fileId=file_id).execute().decode("utf-8")


def _parse_frontmatter(content):
    """Parse YAML frontmatter from markdown content. Returns (metadata_dict, body)."""
    match = FRONTMATTER_PATTERN.match(content)
    if not match:
        return {}, content
    try:
        metadata = yaml.safe_load(match.group(1))
        body = content[match.end():]
        return metadata or {}, body
    except yaml.YAMLError:
        return {}, content


def _document_exists(fs_client, granola_id):
    """Check if a document with this granola_id already exists."""
    docs = (
        fs_client.collection(COLLECTION)
        .where("source", "==", "granola")
        .where("source_id", "==", str(granola_id))
        .limit(1)
        .get()
    )
    return len(docs) > 0


def _parse_date(date_value):
    """Parse a date from frontmatter (could be string or datetime)."""
    if isinstance(date_value, datetime):
        return date_value.replace(tzinfo=timezone.utc) if date_value.tzinfo is None else date_value
    if isinstance(date_value, str):
        try:
            dt = datetime.fromisoformat(date_value.replace("Z", "+00:00"))
            return dt
        except ValueError:
            return None
    return None


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


@functions_framework.http
def sync_handler(request):
    """HTTP Cloud Function entry point for Granola notes sync."""
    start = time.time()
    cfg = _get_config()
    credentials = _get_credentials()
    drive_service = _get_drive_service(credentials)
    fs_client = _get_firestore_client(cfg)

    total_new = 0
    total_skipped = 0
    errors = []

    try:
        files = _list_markdown_files(drive_service, cfg["folder_id"])
    except Exception as e:
        return json.dumps({"status": "error", "error": f"Failed to list Drive files: {e}"}), 500

    for f in files:
        try:
            content = _download_file(drive_service, f["id"])
            metadata, body = _parse_frontmatter(content)

            granola_id = metadata.get("granola_id")
            if not granola_id:
                errors.append(f"{f['name']}: no granola_id in frontmatter")
                continue

            if _document_exists(fs_client, granola_id):
                total_skipped += 1
                continue

            tags = metadata.get("tags", [])
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(",") if t.strip()]

            participants = metadata.get("participants", [])
            if isinstance(participants, str):
                participants = [p.strip() for p in participants.split(",") if p.strip()]

            firestore_doc = {
                "type": "meeting_note",
                "source": "granola",
                "source_id": str(granola_id),
                "source_url": None,
                "title": metadata.get("title", f["name"].replace(".md", "").replace("_", " ")),
                "content": body.strip(),
                "content_format": "markdown",
                "meeting_series": metadata.get("meeting-series"),
                "meeting_date": _parse_date(metadata.get("created_at")),
                "participants": participants if participants else None,
                "tags": tags,
                "area": metadata.get("area"),
                "sensitivity": "unreviewed",
                "processing_status": "raw",
                "owner_email": cfg["owner_email"],
                "synced_at": _now_iso(),
                "created_at": firestore.SERVER_TIMESTAMP,
                "updated_at": firestore.SERVER_TIMESTAMP,
            }

            fs_client.collection(COLLECTION).add(firestore_doc)
            total_new += 1
        except Exception as e:
            errors.append(f"{f['name']}: {e}")

    duration = round(time.time() - start, 1)

    sync_state = {
        "last_sync_at": _now_iso(),
        "files_found": len(files),
        "new_docs_synced": total_new,
        "skipped_existing": total_skipped,
        "errors": errors,
        "duration_seconds": duration,
    }
    try:
        fs_client.collection(SYNC_METADATA_COLLECTION).document(SYNC_METADATA_DOC).set(sync_state)
    except Exception:
        pass

    return json.dumps({
        "status": "completed",
        "files_found": len(files),
        "new_docs_synced": total_new,
        "skipped_existing": total_skipped,
        "errors": errors,
        "duration_seconds": duration,
    }), 200
```

- [ ] **Step 3: Create tests `dam-mcp/tests/test_granola_sync.py`**

```python
"""Tests for Granola sync Cloud Function."""

import json
import os
import sys
import pytest
from unittest.mock import MagicMock, patch


def _make_module():
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "cloud_functions", "granola_sync"))
    if "main" in sys.modules:
        del sys.modules["main"]
    import main
    sys.path.pop(0)
    return main


class TestParseFrontmatter:
    def test_parses_yaml_frontmatter(self):
        mod = _make_module()
        content = '---\ngranola_id: abc123\ntitle: "Test"\ntags: [a, b]\n---\n\n# Body\nHello'
        meta, body = mod._parse_frontmatter(content)
        assert meta["granola_id"] == "abc123"
        assert meta["title"] == "Test"
        assert meta["tags"] == ["a", "b"]
        assert body.strip() == "# Body\nHello"

    def test_no_frontmatter(self):
        mod = _make_module()
        content = "# Just markdown\nNo frontmatter here"
        meta, body = mod._parse_frontmatter(content)
        assert meta == {}
        assert body == content

    def test_invalid_yaml(self):
        mod = _make_module()
        content = "---\n: invalid: yaml: [[\n---\n\nBody"
        meta, body = mod._parse_frontmatter(content)
        assert meta == {}


class TestParseDate:
    def test_iso_string(self):
        mod = _make_module()
        result = mod._parse_date("2026-02-25T07:45:04.128Z")
        assert result.year == 2026
        assert result.month == 2

    def test_none_input(self):
        mod = _make_module()
        assert mod._parse_date(None) is None

    def test_invalid_string(self):
        mod = _make_module()
        assert mod._parse_date("not-a-date") is None


class TestSyncHandler:
    @patch.dict("os.environ", {
        "GCP_PROJECT_ID": "test-project",
        "GRANOLA_DRIVE_FOLDER_ID": "folder1",
    })
    def test_syncs_new_granola_note(self):
        mod = _make_module()

        mock_request = MagicMock()
        mock_drive = MagicMock()
        mock_fs = MagicMock()
        mock_creds = MagicMock()

        drive_files = [{"id": "file1", "name": "Test_Meeting.md"}]
        file_content = '---\ngranola_id: abc123\ntitle: "Test Meeting"\ntags: [erp, planning]\nparticipants: [Simon, Moritz]\nmeeting-series: "Weekly"\ncreated_at: "2026-03-17T08:31:28.028Z"\narea: engineering/erp\n---\n\n# Meeting Notes\nWe discussed ERP.'

        mock_fs.collection.return_value.where.return_value.where.return_value.limit.return_value.get.return_value = []

        with patch.object(mod, "_get_credentials", return_value=mock_creds), \
             patch.object(mod, "_get_drive_service", return_value=mock_drive), \
             patch.object(mod, "_get_firestore_client", return_value=mock_fs), \
             patch.object(mod, "_list_markdown_files", return_value=drive_files), \
             patch.object(mod, "_download_file", return_value=file_content), \
             patch.object(mod, "_document_exists", return_value=False):
            result, status = mod.sync_handler(mock_request)
            data = json.loads(result)
            assert status == 200
            assert data["new_docs_synced"] == 1

            call_args = mock_fs.collection.return_value.add.call_args[0][0]
            assert call_args["source"] == "granola"
            assert call_args["source_id"] == "abc123"
            assert call_args["tags"] == ["erp", "planning"]
            assert call_args["participants"] == ["Simon", "Moritz"]
            assert call_args["meeting_series"] == "Weekly"
            assert call_args["area"] == "engineering/erp"
            assert "We discussed ERP." in call_args["content"]

    @patch.dict("os.environ", {
        "GCP_PROJECT_ID": "test-project",
        "GRANOLA_DRIVE_FOLDER_ID": "folder1",
    })
    def test_skips_existing_note(self):
        mod = _make_module()
        mock_request = MagicMock()

        with patch.object(mod, "_get_credentials", return_value=MagicMock()), \
             patch.object(mod, "_get_drive_service", return_value=MagicMock()), \
             patch.object(mod, "_get_firestore_client", return_value=MagicMock()), \
             patch.object(mod, "_list_markdown_files", return_value=[{"id": "f1", "name": "test.md"}]), \
             patch.object(mod, "_download_file", return_value='---\ngranola_id: abc\n---\nBody'), \
             patch.object(mod, "_document_exists", return_value=True):
            result, status = mod.sync_handler(mock_request)
            data = json.loads(result)
            assert data["skipped_existing"] == 1
            assert data["new_docs_synced"] == 0

    @patch.dict("os.environ", {
        "GCP_PROJECT_ID": "test-project",
        "GRANOLA_DRIVE_FOLDER_ID": "folder1",
    })
    def test_skips_file_without_granola_id(self):
        mod = _make_module()
        mock_request = MagicMock()

        with patch.object(mod, "_get_credentials", return_value=MagicMock()), \
             patch.object(mod, "_get_drive_service", return_value=MagicMock()), \
             patch.object(mod, "_get_firestore_client", return_value=MagicMock()), \
             patch.object(mod, "_list_markdown_files", return_value=[{"id": "f1", "name": "no_id.md"}]), \
             patch.object(mod, "_download_file", return_value='---\ntitle: No ID\n---\nBody'):
            result, status = mod.sync_handler(mock_request)
            data = json.loads(result)
            assert data["new_docs_synced"] == 0
            assert len(data["errors"]) == 1
```

- [ ] **Step 4: Install pyyaml and run tests**

```bash
cd /Users/simonheinken/Documents/projects/meta/mcp/dam-mcp
pip install pyyaml
python -m pytest tests/test_granola_sync.py -v
```
Expected: ALL PASSED

- [ ] **Step 5: Commit**

```bash
cd /Users/simonheinken/Documents/projects/meta/mcp
git add dam-mcp/cloud_functions/granola_sync/ dam-mcp/tests/test_granola_sync.py
git commit -m "feat: add Granola sync Cloud Function with frontmatter parsing"
```

---

### Task 4: Update document-processor to preserve source metadata

**Files:**
- Modify: `dam-mcp/cloud_functions/document_processor/main.py`
- Modify: `dam-mcp/tests/test_document_processor.py`

- [ ] **Step 1: Add test for metadata preservation**

Add to `dam-mcp/tests/test_document_processor.py`:

```python
class TestMetadataPreservation:
    @patch.dict("os.environ", {
        "GCP_PROJECT_ID": "test-project",
        "ANTHROPIC_API_KEY": "test-key",
    })
    def test_preserves_existing_participants_and_date(self):
        """Granola-sourced docs already have participants and meeting_date from frontmatter."""
        mod = _make_processor_module()

        mock_fs = MagicMock()
        mock_doc_ref = MagicMock()
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "title": "ERP Weekly 2026-03-17",
            "content": "We discussed ERP selection.",
            "tags": ["erp-selection", "odoo"],
            "participants": ["Simon Heinken", "Moritz Barmann"],
            "meeting_date": "2026-03-17T08:31:28+00:00",
            "processing_status": "raw",
        }
        mock_doc_ref.get.return_value = mock_doc
        mock_fs.collection.return_value.document.return_value = mock_doc_ref

        llm_result = {
            "tags": ["vendor-evaluation"],
            "summary": "ERP selection discussed.",
            "sensitivity": "safe",
            "action_items": [],
            "key_decisions": ["Odoo shortlisted"],
            "meeting_type": "sync",
            "language": "de",
        }

        cloud_event = MagicMock()
        cloud_event.__getitem__ = lambda self, key: "documents/knowledge_base/granola1" if key == "subject" else None

        with patch.object(mod, "_get_firestore_client", return_value=mock_fs), \
             patch.object(mod, "_get_anthropic_client", return_value=MagicMock()), \
             patch.object(mod, "_get_voyage_client", return_value=None), \
             patch.object(mod, "_extract_with_llm", return_value=llm_result):
            mod.process_document(cloud_event)

        final_update = mock_doc_ref.update.call_args_list[-1][0][0]
        # Participants from source preserved (not overwritten by email regex)
        assert final_update["participants"] == ["Simon Heinken", "Moritz Barmann"]
        # Meeting date from source preserved (not overwritten by title parser)
        assert final_update["meeting_date"] == "2026-03-17T08:31:28+00:00"
        # Tags merged: source + LLM
        assert "erp-selection" in final_update["tags"]
        assert "vendor-evaluation" in final_update["tags"]
        # LLM fields always set
        assert final_update["summary"] == "ERP selection discussed."
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/simonheinken/Documents/projects/meta/mcp/dam-mcp
python -m pytest tests/test_document_processor.py::TestMetadataPreservation -v
```
Expected: FAIL (participants and meeting_date get overwritten)

- [ ] **Step 3: Update process_document to preserve source metadata**

In `dam-mcp/cloud_functions/document_processor/main.py`, change the updates block in `process_document` from:

```python
        updates = {
            "participants": participants if participants else None,
            "meeting_date": meeting_date,
```

to:

```python
        updates = {
            "participants": data.get("participants") or (participants if participants else None),
            "meeting_date": data.get("meeting_date") or meeting_date,
```

This preserves participants and meeting_date if they were already set by the sync source (Granola frontmatter), and only falls back to rule-based extraction if they're missing.

- [ ] **Step 4: Run all tests**

```bash
cd /Users/simonheinken/Documents/projects/meta/mcp/dam-mcp
python -m pytest tests/test_document_processor.py -v
```
Expected: ALL PASSED

- [ ] **Step 5: Commit**

```bash
cd /Users/simonheinken/Documents/projects/meta/mcp
git add dam-mcp/cloud_functions/document_processor/main.py dam-mcp/tests/test_document_processor.py
git commit -m "fix: preserve source metadata in document processor (Granola support)"
```

---

### Task 5: Remove knowledge tools from dam-mcp

**Files:**
- Delete: `dam-mcp/dam_mcp/core/tools_query_kb.py`
- Delete: `dam-mcp/dam_mcp/core/tools_get_document.py`
- Delete: `dam-mcp/dam_mcp/core/tools_semantic_search.py`
- Delete: `dam-mcp/tests/test_query_kb.py`
- Delete: `dam-mcp/tests/test_get_document.py`
- Delete: `dam-mcp/tests/test_semantic_search.py`
- Modify: `dam-mcp/dam_mcp/core/__init__.py`

- [ ] **Step 1: Remove imports from `dam-mcp/dam_mcp/core/__init__.py`**

Change from:
```python
from .tools_sync import sync_status
from .tools_trigger_sync import trigger_sync
from .tools_figma_export import export_figma_frames
from .tools_query_kb import query_knowledge_base
from .tools_get_document import get_document
from .tools_semantic_search import search_knowledge_base_semantic
```

to:
```python
from .tools_sync import sync_status
from .tools_trigger_sync import trigger_sync
from .tools_figma_export import export_figma_frames
```

- [ ] **Step 2: Delete tool files and test files**

```bash
cd /Users/simonheinken/Documents/projects/meta/mcp/dam-mcp
rm dam_mcp/core/tools_query_kb.py
rm dam_mcp/core/tools_get_document.py
rm dam_mcp/core/tools_semantic_search.py
rm tests/test_query_kb.py
rm tests/test_get_document.py
rm tests/test_semantic_search.py
```

- [ ] **Step 3: Run dam-mcp tests to verify nothing breaks**

```bash
cd /Users/simonheinken/Documents/projects/meta/mcp/dam-mcp
python -m pytest tests/ -v
```
Expected: ALL PASSED (knowledge tool tests gone, remaining tests still pass)

- [ ] **Step 4: Commit**

```bash
cd /Users/simonheinken/Documents/projects/meta/mcp
git add dam-mcp/
git commit -m "refactor: remove knowledge tools from dam-mcp (moved to knowledge-mcp)"
```

---

### Task 6: Deploy Granola-Sync and test end-to-end

**Files:** None (infrastructure only)

- [ ] **Step 1: Deploy Granola-Sync Cloud Function**

```bash
cd /Users/simonheinken/Documents/projects/meta/mcp
gcloud functions deploy granola-sync \
  --gen2 \
  --runtime=python312 \
  --region=europe-west3 \
  --source=dam-mcp/cloud_functions/granola_sync/ \
  --entry-point=sync_handler \
  --service-account=dam-mcp@gold-blueprint-357814.iam.gserviceaccount.com \
  --set-env-vars=GCP_PROJECT_ID=gold-blueprint-357814,GRANOLA_DRIVE_FOLDER_ID=1GEbGQEnvu6x4EU-xhEa5PZB-4KV4TZfW \
  --trigger-http \
  --no-allow-unauthenticated \
  --timeout=300 \
  --memory=256Mi \
  --project=gold-blueprint-357814
```

- [ ] **Step 2: Create Cloud Scheduler job**

```bash
gcloud scheduler jobs create http granola-sync-hourly \
  --location=europe-west3 \
  --schedule="30 * * * *" \
  --uri=<granola-sync-function-url> \
  --oidc-service-account-email=dam-mcp@gold-blueprint-357814.iam.gserviceaccount.com \
  --http-method=POST \
  --project=gold-blueprint-357814
```

- [ ] **Step 3: Trigger sync and verify**

```bash
curl -s -X POST \
  https://europe-west3-gold-blueprint-357814.cloudfunctions.net/granola-sync \
  -H "Authorization: bearer $(gcloud auth print-identity-token)"
```

Then verify documents in Firestore:
```bash
python3 -c "
from google.cloud import firestore
client = firestore.Client(project='gold-blueprint-357814')
docs = client.collection('knowledge_base').where('source', '==', 'granola').limit(5).get()
print(f'Granola docs: {len(docs)}')
for doc in docs:
    d = doc.to_dict()
    print(f'  {d.get(\"title\")[:60]}')
    print(f'    tags: {d.get(\"tags\")}')
    print(f'    participants: {d.get(\"participants\")}')
    print(f'    series: {d.get(\"meeting_series\")}')
    print(f'    area: {d.get(\"area\")}')
    print(f'    status: {d.get(\"processing_status\")}')
    print(f'    llm_enriched: {d.get(\"llm_enriched\")}')
    print()
"
```

- [ ] **Step 4: Redeploy document-processor with metadata preservation fix**

```bash
cd /Users/simonheinken/Documents/projects/meta/mcp
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

- [ ] **Step 5: Final commit and push**

```bash
cd /Users/simonheinken/Documents/projects/meta/mcp
git add -A
git commit -m "deploy: knowledge-mcp server + Granola sync + document-processor update"
git push origin main
```
