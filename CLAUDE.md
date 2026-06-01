# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

**`mcp-hub` is the public distribution repo** for Ryzon's MCP (Model Context Protocol) setup. It hosts the installer, the Knowledge Ops plugin, team-rollout scripts, and docs. It is intentionally public so the installer and rollout scripts can be fetched via raw GitHub URLs by non-technical colleagues.

**The MCP server source code lives in the private repo [`Ryzon-Performance-Sports-Apparel/mcp-servers`](https://github.com/Ryzon-Performance-Sports-Apparel/mcp-servers)** — `meta-ads-mcp`, `google-ads-mcp`, `dam-mcp`, `knowledge-mcp`. Edit code there, not here.

What's in this repo:

- **`install.sh`** + **`SETUP_GUIDE.md`** — one-click installer that configures the MCP servers for Claude Desktop on macOS. Installed via:
  `bash -c "$(curl -fsSL https://raw.githubusercontent.com/Ryzon-Performance-Sports-Apparel/mcp-hub/main/install.sh)"`
- **`install-meta-ads.sh`** — standalone Meta Ads installer.
- **`scripts/`** — team-rollout scripts (`install-team-setup.sh` is fetched by raw URL — keep it working).
- **`plugins/ryzon-knowledge-ops/`** — the Knowledge Ops Claude Code plugin (commands, agents).
- **`docs/`** — Knowledge Ops rollout docs (`knowledge-setup/`) and internal/working docs.

## How the servers are distributed

- **google-ads** — published to PyPI as **`ryzon-google-ads-mcp`** (a Ryzon fork of `googleads/google-ads-mcp`, with hardened `search` argument handling). `install.sh` runs `uv tool install ryzon-google-ads-mcp`; the executable is named `google-ads-mcp`. Source + the trusted-publishing workflow live in `mcp-servers`.
- **meta-ads** — installed from the upstream PyPI `meta-ads-mcp`. The Ryzon fork (with `RYZON_MODE` defaults) is in `mcp-servers` and is **deprecated** — superseded by the official Meta Ads MCP connector.
- **dam / knowledge** — internal servers, run from local checkouts of `mcp-servers`; not distributed via this repo.

## Credentials gotchas (google-ads)

The Google Ads client authenticates via per-user **gcloud ADC** (`~/.config/gcloud/application_default_credentials.json`), not the `GOOGLE_PROJECT_ID` env (which the server does **not** read). Two recurring failure modes the installer guards against:

- `403 ACCESS_TOKEN_SCOPE_INSUFFICIENT` — ADC was created without the AdWords scope. Fix: `gcloud auth application-default login --scopes=https://www.googleapis.com/auth/adwords,https://www.googleapis.com/auth/cloud-platform`.
- `403 SERVICE_DISABLED` — the ADC **quota project** points at a project where the Google Ads API is disabled. The installer pins it: `gcloud auth application-default set-quota-project <PROJECT_ID>`.

## Editing the servers

Clone `mcp-servers` and work there. For `google-ads-mcp` dev:

```bash
cd google-ads-mcp
uv venv && uv pip install -e .          # editable install
python -m unittest discover -s tests -p "*_test.py"
```

Note: do not point Claude Desktop at a venv under `~/Documents` (macOS TCC blocks it — the server fails to start). Use `uv tool install` so the runtime lives under `~/.local`.
