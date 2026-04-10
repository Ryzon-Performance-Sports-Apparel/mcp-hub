# Meta Ads MCP — Cloud Run Gateway Design

Deploy the existing Python meta-ads-mcp server to Google Cloud Run behind a Node.js/TypeScript HTTP + OAuth gateway, making it accessible as a remote MCP server for claude.ai and Claude Desktop/Code.

## Context

The meta-ads-mcp server currently runs locally via stdio transport. To make it accessible to non-technical team members without local installs, we deploy it to Cloud Run with OAuth protecting access. This reuses the same architecture proven in the daily-briefing MCP (`/Users/simonheinken/Documents/projects/context/ai-enablement/projects/daily-briefing/mcp/ryzon-briefing/`).

## Architecture

### Overview

```
claude.ai / Claude Desktop
        │
        ▼ (HTTPS + OAuth bearer token)
┌──────────────────────────┐
│  Node.js Gateway         │  Cloud Run (europe-west3)
│  ├─ Express server       │
│  ├─ OAuth (Google)       │
│  └─ Streamable HTTP      │
│        │                 │
│        ▼ (stdio)         │
│  Python meta_ads_mcp     │
│  (spawned as subprocess) │
└──────────────────────────┘
        │
        ▼ (HTTPS)
   Meta Graph API v24.0
```

Single Docker container. Node.js is the entrypoint and spawns `python -m meta_ads_mcp` as a stdio child process per MCP session.

### Repository Structure

```
meta-ads-mcp/
├── meta_ads_mcp/              # Existing Python MCP server (untouched)
├── gateway/                   # New Node.js HTTP/OAuth proxy
│   ├── src/
│   │   ├── index.ts           # Express server, stdio proxy, session mgmt
│   │   └── auth.ts            # Google OAuth provider (@ryzon.net)
│   ├── package.json
│   └── tsconfig.json
├── Dockerfile                 # Multi-stage: Node.js build + Python runtime
├── scripts/
│   └── deploy.sh              # Cloud Run deployment
├── pyproject.toml             # Existing (untouched)
└── ...
```

## Gateway (`gateway/`)

### `src/auth.ts` — Google OAuth Provider

Reuses the `ProxyOAuthServerProvider` pattern from the daily-briefing MCP:

- Proxies OAuth through Google's authorization and token endpoints
- Validates access tokens via `https://oauth2.googleapis.com/tokeninfo`
- Verifies the token was issued for our OAuth client (audience check)
- Restricts access to `@ryzon.net` Google accounts only
- Credentials come from env vars: `OAUTH_CLIENT_ID`, `OAUTH_CLIENT_SECRET`

### `src/index.ts` — Express Server + Stdio Proxy

Two modes, selected by presence of `PORT` env var:

**HTTP mode (Cloud Run):**
- Express server on `0.0.0.0:PORT`
- `/.well-known/*`, `/authorize`, `/token`, `/register`, `/revoke` — OAuth endpoints via `mcpAuthRouter`
- `GET /health` — unauthenticated health check for Cloud Run
- `POST /mcp` — OAuth-protected MCP endpoint
- `GET /mcp` — SSE streaming for open sessions
- `DELETE /mcp` — session cleanup

Per-session flow:
1. New request arrives at `POST /mcp` with valid OAuth bearer token
2. Gateway spawns `python -m meta_ads_mcp` as a child process
3. Creates `StreamableHTTPServerTransport` (session) and bridges to Python's stdio
4. Subsequent requests with the same `mcp-session-id` reuse the existing transport + Python process
5. On session close or disconnect, Python process is killed

**Stdio mode (local dev):**
- No `PORT` set — spawns Python process and bridges stdin/stdout directly
- Useful for local testing without OAuth

### Dependencies

```json
{
  "@modelcontextprotocol/sdk": "latest",
  "express": "^4.x",
  "typescript": "^5.x"
}
```

## Dockerfile

Multi-stage build:

1. **Stage 1 — Build gateway:** Node 22 alpine, `npm ci`, `npm run build` (TypeScript → JS)
2. **Stage 2 — Runtime:** Node 22 alpine + Python 3.10 (via apk), copy compiled JS from stage 1, copy `meta_ads_mcp/` Python package, `pip install` Python dependencies from `pyproject.toml`, set entrypoint to `node dist/index.js`

The Node.js process is PID 1. Python processes are spawned as children.

## Cloud Run Deployment

### Configuration

- **GCP Project:** `gold-blueprint-357814`
- **Service name:** `meta-ads-mcp`
- **Region:** `europe-west3`
- **Memory:** 256Mi
- **CPU:** 1
- **Instances:** 0-1 (scales to zero when idle)
- **Timeout:** 300s
- **Auth:** `--allow-unauthenticated` (OAuth handles auth at the application level)

### Environment Variables

| Variable | Source | Description |
|----------|--------|-------------|
| `PORT` | Cloud Run (auto) | HTTP listen port |
| `BASE_URL` | deploy.sh | Cloud Run service URL |
| `OAUTH_CLIENT_ID` | GCP console | New OAuth 2.0 client ID |
| `OAUTH_CLIENT_SECRET` | GCP console | New OAuth 2.0 client secret |
| `OAUTH_ALLOWED_DOMAIN` | hardcoded | `ryzon.net` |
| `META_ACCESS_TOKEN` | deploy.sh | Shared Meta API token |
| `RYZON_MODE` | deploy.sh | `1` — enables Ryzon defaults |

### `scripts/deploy.sh`

Mirrors the daily-briefing deploy script:
- Builds and deploys from source via `gcloud run deploy --source=.`
- Writes env vars to a temp YAML file (handles secrets without shell escaping issues)
- Prints connection instructions for both claude.ai and Claude Desktop/Code after deploy

### Token Updates

When the Meta access token expires, update without redeploying:
```bash
gcloud run services update meta-ads-mcp \
  --project=gold-blueprint-357814 \
  --region=europe-west3 \
  --update-env-vars META_ACCESS_TOKEN=<new_token>
```

## Client Setup

### claude.ai (browser)

Add as remote MCP server in Settings → MCP Servers:
- **Server URL:** `https://<service-url>/mcp`
- Authenticates via Google OAuth popup (must be `@ryzon.net` account)

### Claude Desktop / Claude Code

Add to MCP config:
```json
{
  "mcpServers": {
    "meta-ads": {
      "type": "url",
      "url": "https://<service-url>/mcp"
    }
  }
}
```

## Performance

- **Cold start:** 5-10 seconds (container start + Node boot + Python spawn). Acceptable for interactive LLM tool calls.
- **Warm requests:** Sub-second. Python process stays alive for the duration of the MCP session.
- **Scale to zero:** No cost when idle. First request after idle incurs cold start.

## What's NOT Changing

- The Python `meta_ads_mcp` package — zero modifications
- `pyproject.toml` — no new dependencies
- All existing MCP tools — they work unchanged over stdio
- Local stdio usage — still works by running `python -m meta_ads_mcp` directly
