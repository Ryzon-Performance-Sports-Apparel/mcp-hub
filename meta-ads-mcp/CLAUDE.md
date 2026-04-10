# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Does

MCP (Model Context Protocol) server that enables LLMs to manage Meta (Facebook/Instagram) ad campaigns via the Meta Graph API v24.0. Uses the FastMCP framework and exposes 26+ tools for creating/editing campaigns, ad sets, ads, creatives, audiences, and pulling performance insights.

## Commands

```bash
# Install dependencies
pip install -e .

# Run the server (stdio transport, for local MCP clients)
python -m meta_ads_mcp

# Run the server (HTTP transport, for remote/cloud use)
python -m meta_ads_mcp --transport streamable-http --port 8080

# Run all unit tests (e2e excluded by default)
pytest tests/ -v

# Run a single test file
pytest tests/test_campaign_objective_filter.py -v

# Run e2e tests (requires running server)
pytest tests/ -v -m e2e

# Build wheel
python -m build
```

## Architecture

### Entry Point Flow
`meta_ads_mcp/__init__.py::entrypoint()` → `core/server.py::main()` → FastMCP server starts with registered tools.

### Core Modules
- **`core/server.py`** — CLI arg parsing, FastMCP server init, transport selection (stdio vs streamable-http)
- **`core/api.py`** — HTTP wrapper around Meta Graph API with rate limiting and error handling; all API calls go through here
- **`core/auth.py`** — OAuth flow, token caching, local callback server for browser-based login
- **`core/ads.py`** — Largest module (~2,600 lines); handles ad and creative creation, image upload/download, all creative formats
- **`core/campaigns.py`**, **`core/adsets.py`** — CRUD for campaigns and ad sets
- **`core/targeting.py`** — Interest/behavior/location/demographic search against Meta's targeting API
- **`core/insights.py`** — Performance metrics retrieval
- **`core/duplication.py`** — Campaign/ad set/ad cloning logic

### How MCP Tools Are Registered
Each module decorates its functions with `@mcp_server.tool()`. The `mcp_server` instance is created in `server.py` and passed/imported across modules.

### Transport
- **stdio**: For local MCP clients (Claude Desktop, Claude Code)

### Authentication
- **Direct token**: `META_ACCESS_TOKEN` env var (primary, set via `install.sh`)

### Testing
- Tests in `tests/` use `pytest-asyncio` (asyncio_mode=auto)
- Unit tests mock Meta API calls; e2e tests (`@pytest.mark.e2e`) require a live server
- `tests/conftest.py` contains shared fixtures
- e2e server URL configurable via `MCP_TEST_SERVER_URL` env var (default: `http://localhost:8080`)

## Ryzon Client Customization

### RYZON_MODE
Set `RYZON_MODE=1` environment variable to activate Ryzon-specific defaults. When active, creation functions auto-apply:
- Account ID, Page ID, Instagram Actor ID, Pixel ID
- DSA Beneficiary/Payor: "Ryzon GmbH"
- Status: always PAUSED
- creative_features_spec: all Advantage+ optimizations OPT_OUT
- Standard tracking specs (pixel, commerce, app events)
- UTM parameters with Klar integration
- Excluded audiences (F0_Negative_Audience)
- Advantage Audience: always enabled

Configuration: `core/ryzon_config.py` (constants) + `core/ryzon_defaults.py` (injection helpers)

### Ryzon Agents (`.claude/agents/`)
- **ryzon-create** — Orchestrator for full ad creation flow (6-step guided questionnaire)
- **ryzon-campaign** — Campaign selection/creation expert
- **ryzon-adset** — Ad set creation with targeting templates
- **ryzon-creative** — Creative building (image/video/catalog)
- **ryzon-ad** — Ad assembly with tracking and confirmation

Reference: `project_context/20260330_meta_ads_mcp_ryzon.pdf`

## Cloud Run Deployment

The server runs on Google Cloud Run behind a Node.js HTTP/OAuth gateway (`gateway/`).

```bash
# Deploy to Cloud Run
bash scripts/deploy.sh

# Update Meta token without redeploying
gcloud run services update meta-ads-mcp \
  --project=gold-blueprint-357814 \
  --region=europe-west3 \
  --update-env-vars META_ACCESS_TOKEN=<new_token>
```

The gateway spawns `python -m meta_ads_mcp` as a stdio subprocess per session. OAuth restricts access to specific authorized Google accounts (configured via `OAUTH_ALLOWED_EMAILS` env var).

Service URL: `https://meta-ads-mcp-k43m4vhxuq-ey.a.run.app/mcp`

## Release Process

Version must be bumped in three places simultaneously:
1. `pyproject.toml`
2. `meta_ads_mcp/__init__.py`
3. `server.json`

Then commit, push, and create a GitHub release — PyPI publishing is automated via trusted publishing (OIDC, no secrets needed).
