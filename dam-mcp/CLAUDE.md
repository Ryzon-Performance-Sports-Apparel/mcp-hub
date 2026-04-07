# CLAUDE.md — dam-mcp

## Overview

Standalone MCP server for Digital Asset Management. Provides tools to search, upload, tag, and serve creative assets from Google Cloud Storage, primarily for use by ad platform MCP servers (meta-ads-mcp, google-ads-mcp) and other AI applications.

## Commands

```bash
pip install -e .                    # Install in dev mode
python -m dam_mcp                   # Run server (stdio)
python -m dam_mcp --version         # Show version
pytest tests/ -v                    # Run unit tests
```

## Architecture

Entry point: `dam_mcp/__init__.py:entrypoint()` -> `core/server.py:main()` -> FastMCP("dam")

Key modules in `dam_mcp/core/`:
- `server.py` — FastMCP init, CLI args
- `config.py` — Environment variable loading (DamConfig singleton)
- `gcs.py` — GCS client wrapper (all GCS operations go through here)
- `firestore.py` — Firestore client wrapper (knowledge base operations)
- `tools_*.py` — One file per MCP tool

Tools are registered via `@mcp_server.tool()` decorators, triggered by imports in `core/__init__.py`.

## Environment Variables

- `GCP_PROJECT_ID` — GCP project (required)
- `GCS_BUCKET_NAME` — Cloud Storage bucket (required)
- `GOOGLE_APPLICATION_CREDENTIALS` — Service account JSON path (required)
- `SIGNED_URL_EXPIRY_MINUTES` — Signed URL lifetime (default: 60)
- `GDRIVE_FOLDER_ID` — Drive folder for asset sync
- `FIRESTORE_DATABASE` — Firestore database name (default: `(default)`)
- `CONFIG_SHEET_ID` — Google Sheet ID for meeting notes sync config
- `CONFIG_SHEET_NAME` — Sheet tab name (default: `Sheet1`)

## Version

Must be kept in sync across:
1. `pyproject.toml`
2. `dam_mcp/__init__.py`
3. `server.json`
