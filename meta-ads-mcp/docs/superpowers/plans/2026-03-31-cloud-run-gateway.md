# Cloud Run Gateway Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deploy meta-ads-mcp to Cloud Run behind a Node.js HTTP/OAuth gateway so team members can use it as a remote MCP server on claude.ai and Claude Desktop without any local installation.

**Architecture:** Node.js Express gateway spawns `python -m meta_ads_mcp` as a stdio subprocess per session. The gateway handles OAuth (Google, `@ryzon.net` only) and bridges HTTP ↔ stdio using the MCP SDK's transport interfaces. Single Docker container deployed to Cloud Run.

**Tech Stack:** Node.js 22, TypeScript, Express 5, `@modelcontextprotocol/sdk`, Python 3.11, Docker, Google Cloud Run

**Reference implementation:** `/Users/simonheinken/Documents/projects/context/ai-enablement/projects/daily-briefing/mcp/ryzon-briefing/` — the daily-briefing MCP uses the same OAuth + Express + Cloud Run pattern. Copy auth.ts and index.ts structure from there, adapting for the stdio proxy pattern.

---

### Task 1: Scaffold the gateway Node.js project

**Files:**
- Create: `gateway/package.json`
- Create: `gateway/tsconfig.json`

- [ ] **Step 1: Create `gateway/package.json`**

```json
{
  "name": "@ryzon/meta-ads-gateway",
  "version": "1.0.0",
  "description": "HTTP/OAuth gateway for meta-ads-mcp",
  "type": "module",
  "main": "dist/index.js",
  "scripts": {
    "build": "tsc",
    "dev": "tsc --watch",
    "start": "node dist/index.js"
  },
  "dependencies": {
    "@modelcontextprotocol/sdk": "^1.12.1",
    "express": "^5.2.1"
  },
  "devDependencies": {
    "@types/express": "^5.0.6",
    "@types/node": "^22.15.3",
    "typescript": "^5.8.3"
  }
}
```

- [ ] **Step 2: Create `gateway/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ES2022",
    "moduleResolution": "bundler",
    "outDir": "dist",
    "rootDir": "src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "declaration": true,
    "sourceMap": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}
```

- [ ] **Step 3: Install dependencies**

Run: `cd gateway && npm install`
Expected: `node_modules/` created, `package-lock.json` generated

- [ ] **Step 4: Commit**

```bash
git add gateway/package.json gateway/package-lock.json gateway/tsconfig.json
git commit -m "feat: scaffold gateway Node.js project"
```

---

### Task 2: Implement OAuth provider

**Files:**
- Create: `gateway/src/auth.ts`

Reference: `/Users/simonheinken/Documents/projects/context/ai-enablement/projects/daily-briefing/mcp/ryzon-briefing/src/auth.ts`

- [ ] **Step 1: Create `gateway/src/auth.ts`**

Adapted from the daily-briefing auth.ts. Key changes: `ALLOWED_DOMAIN` defaults to `ryzon.net`, removed `ryzon.de` from the allowed list.

```typescript
import { ProxyOAuthServerProvider } from "@modelcontextprotocol/sdk/server/auth/providers/proxyProvider.js";
import { OAuthClientInformationFull } from "@modelcontextprotocol/sdk/shared/auth.js";
import { AuthInfo } from "@modelcontextprotocol/sdk/server/auth/types.js";

const GOOGLE_CLIENT_ID = process.env.OAUTH_CLIENT_ID!;
const GOOGLE_CLIENT_SECRET = process.env.OAUTH_CLIENT_SECRET!;
const ALLOWED_DOMAIN = process.env.OAUTH_ALLOWED_DOMAIN || "ryzon.net";

export function createGoogleOAuthProvider() {
  const provider = new ProxyOAuthServerProvider({
    endpoints: {
      authorizationUrl: "https://accounts.google.com/o/oauth2/v2/auth",
      tokenUrl: "https://oauth2.googleapis.com/token",
      revocationUrl: "https://oauth2.googleapis.com/revoke",
    },

    getClient: async (clientId: string) => {
      if (clientId !== GOOGLE_CLIENT_ID) return undefined;

      return {
        client_id: GOOGLE_CLIENT_ID,
        client_secret: GOOGLE_CLIENT_SECRET,
        client_id_issued_at: 0,
        redirect_uris: ["https://claude.ai/api/mcp/auth_callback"],
        grant_types: ["authorization_code", "refresh_token"],
        response_types: ["code"],
        token_endpoint_auth_method: "client_secret_post",
        scope: "openid email",
      } as OAuthClientInformationFull;
    },

    verifyAccessToken: async (token: string): Promise<AuthInfo> => {
      const res = await fetch(
        `https://oauth2.googleapis.com/tokeninfo?access_token=${token}`
      );

      if (!res.ok) {
        const body = await res.text();
        console.error("Google tokeninfo failed:", res.status, body);
        throw new Error("Invalid or expired Google access token");
      }

      const info = (await res.json()) as Record<string, string>;

      // Verify token was issued for our OAuth client
      if (info.aud !== GOOGLE_CLIENT_ID) {
        console.error(`aud mismatch: got ${info.aud}, expected ${GOOGLE_CLIENT_ID}`);
        throw new Error("Token was not issued for this application");
      }

      // Restrict to allowed domain
      const emailDomain = info.email?.split("@")[1];
      if (emailDomain && emailDomain !== ALLOWED_DOMAIN) {
        console.error(`domain rejected: ${emailDomain}`);
        throw new Error(`Access restricted to @${ALLOWED_DOMAIN} accounts`);
      }

      console.log(`Verified token for ${info.email}`);

      return {
        token,
        clientId: GOOGLE_CLIENT_ID,
        scopes: ["openid", "email"],
        expiresAt: Math.floor(Date.now() / 1000) + parseInt(info.expires_in || "3600", 10),
        extra: {
          email: info.email,
        },
      };
    },
  });

  // Override authorize to replace Claude.ai's "claudeai" scope with valid Google scopes
  const originalAuthorize = provider.authorize.bind(provider);
  provider.authorize = async (client, params, res) => {
    params.scopes = ["openid", "email"];
    return originalAuthorize(client, params, res);
  };

  return provider;
}
```

- [ ] **Step 2: Verify it compiles**

Run: `cd gateway && npx tsc --noEmit`
Expected: No errors (auth.ts compiles cleanly)

- [ ] **Step 3: Commit**

```bash
git add gateway/src/auth.ts
git commit -m "feat: add Google OAuth provider for gateway"
```

---

### Task 3: Implement the HTTP gateway with stdio proxy

**Files:**
- Create: `gateway/src/index.ts`

Reference: `/Users/simonheinken/Documents/projects/context/ai-enablement/projects/daily-briefing/mcp/ryzon-briefing/src/index.ts`

The key difference from daily-briefing: instead of `createMcpServer()` returning an in-process server, we spawn `python -m meta_ads_mcp` as a child process and bridge the transports.

- [ ] **Step 1: Create `gateway/src/index.ts`**

```typescript
#!/usr/bin/env node

import express from "express";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import { mcpAuthRouter } from "@modelcontextprotocol/sdk/server/auth/router.js";
import { requireBearerAuth } from "@modelcontextprotocol/sdk/server/auth/middleware/bearerAuth.js";
import { createGoogleOAuthProvider } from "./auth.js";
import { randomUUID } from "crypto";
import { JSONRPCMessage } from "@modelcontextprotocol/sdk/types.js";

const PORT = process.env.PORT ? parseInt(process.env.PORT, 10) : undefined;

interface Session {
  httpTransport: StreamableHTTPServerTransport;
  stdioTransport: StdioClientTransport;
}

function spawnPythonProcess(): StdioClientTransport {
  return new StdioClientTransport({
    command: "python",
    args: ["-m", "meta_ads_mcp"],
    env: {
      ...process.env as Record<string, string>,
    },
    stderr: "inherit",
  });
}

async function startHttpServer(port: number) {
  const app = express();

  app.set("trust proxy", 1);

  const provider = createGoogleOAuthProvider();
  if (!process.env.BASE_URL) {
    console.error("BASE_URL env var is required in HTTP mode for OAuth metadata.");
    process.exit(1);
  }
  const baseUrl = new URL(process.env.BASE_URL);

  // OAuth endpoints
  app.use(
    mcpAuthRouter({
      provider,
      issuerUrl: baseUrl,
      baseUrl,
      serviceDocumentationUrl: new URL(
        "https://github.com/Awesimous/meta-ads-mcp-internal"
      ),
    })
  );

  // Health check (no auth)
  app.get("/health", (_req, res) => {
    res.json({ status: "ok" });
  });

  // MCP endpoint — protected by OAuth bearer token
  const bearerAuth = requireBearerAuth({
    verifier: provider,
    resourceMetadataUrl: `${baseUrl.origin}/.well-known/oauth-protected-resource`,
  });

  const sessions = new Map<string, Session>();

  app.post("/mcp", bearerAuth, async (req, res) => {
    const sessionId = req.headers["mcp-session-id"] as string | undefined;
    let session = sessionId ? sessions.get(sessionId) : undefined;

    if (session) {
      await session.httpTransport.handleRequest(req, res);
      return;
    }

    // New session: spawn Python process and create transports
    const newSessionId = randomUUID();
    const httpTransport = new StreamableHTTPServerTransport({
      sessionIdGenerator: () => newSessionId,
    });

    const stdioTransport = spawnPythonProcess();

    // Bridge: HTTP → Python stdio
    httpTransport.onmessage = async (message: JSONRPCMessage) => {
      await stdioTransport.send(message);
    };

    // Bridge: Python stdio → HTTP
    stdioTransport.onmessage = async (message: JSONRPCMessage) => {
      await httpTransport.send(message);
    };

    // Error handling
    stdioTransport.onerror = (error) => {
      console.error(`[${newSessionId}] stdio error:`, error.message);
    };

    // Cleanup on session close
    httpTransport.onclose = () => {
      console.log(`[${newSessionId}] session closed`);
      stdioTransport.close();
      sessions.delete(newSessionId);
    };

    stdioTransport.onclose = () => {
      console.log(`[${newSessionId}] Python process exited`);
      httpTransport.close();
      sessions.delete(newSessionId);
    };

    await stdioTransport.start();
    sessions.set(newSessionId, { httpTransport, stdioTransport });

    await httpTransport.handleRequest(req, res);
  });

  app.get("/mcp", bearerAuth, async (req, res) => {
    const sessionId = req.headers["mcp-session-id"] as string | undefined;
    if (!sessionId || !sessions.has(sessionId)) {
      res.status(400).json({ error: "Invalid or missing session ID" });
      return;
    }
    await sessions.get(sessionId)!.httpTransport.handleRequest(req, res);
  });

  app.delete("/mcp", bearerAuth, async (req, res) => {
    const sessionId = req.headers["mcp-session-id"] as string | undefined;
    if (!sessionId || !sessions.has(sessionId)) {
      res.status(400).json({ error: "Invalid or missing session ID" });
      return;
    }
    const session = sessions.get(sessionId)!;
    await session.httpTransport.handleRequest(req, res);
    await session.stdioTransport.close();
    sessions.delete(sessionId);
  });

  // Error handler
  app.use((err: Error, _req: express.Request, res: express.Response, _next: express.NextFunction) => {
    console.error("Express error:", err.message, err.stack);
    if (!res.headersSent) {
      res.status(500).json({ error: err.message });
    }
  });

  app.listen(port, "0.0.0.0", () => {
    console.log(`meta-ads MCP gateway listening on port ${port}`);
    console.log(`  MCP:    ${baseUrl.origin}/mcp`);
    console.log(`  Health: ${baseUrl.origin}/health`);
    console.log(`  OAuth:  ${baseUrl.origin}/.well-known/oauth-authorization-server`);
  });
}

async function main() {
  if (PORT) {
    await startHttpServer(PORT);
  } else {
    // Stdio passthrough mode for local dev
    console.error("No PORT set — running in stdio passthrough mode");
    console.error("Use PORT=8080 for HTTP mode");
    process.exit(1);
  }
}

main().catch((err) => {
  console.error("Failed to start meta-ads MCP gateway:", err);
  process.exit(1);
});
```

- [ ] **Step 2: Verify it compiles**

Run: `cd gateway && npx tsc`
Expected: `dist/` directory created with `index.js` and `auth.js`

- [ ] **Step 3: Commit**

```bash
git add gateway/src/index.ts
git commit -m "feat: add HTTP gateway with stdio proxy to Python MCP server"
```

---

### Task 4: Create the Dockerfile

**Files:**
- Modify: `Dockerfile` (replace existing)

- [ ] **Step 1: Replace the existing `Dockerfile`**

The new Dockerfile is a multi-stage build: compile TypeScript in stage 1, then create a runtime image with both Node.js and Python.

```dockerfile
# Stage 1: Build the Node.js gateway
FROM node:22-alpine AS gateway-builder
WORKDIR /app/gateway
COPY gateway/package*.json ./
RUN npm ci
COPY gateway/tsconfig.json ./
COPY gateway/src/ src/
RUN npx tsc

# Stage 2: Runtime with Node.js + Python
FROM node:22-alpine
RUN apk add --no-cache python3 py3-pip

WORKDIR /app

# Install gateway production deps
COPY gateway/package*.json ./gateway/
RUN cd gateway && npm ci --omit=dev

# Copy compiled gateway JS
COPY --from=gateway-builder /app/gateway/dist ./gateway/dist/

# Install Python MCP server
COPY requirements.txt ./
RUN pip install --break-system-packages -r requirements.txt

COPY meta_ads_mcp/ ./meta_ads_mcp/
COPY pyproject.toml ./
RUN pip install --break-system-packages -e .

ENV PORT=8080
EXPOSE 8080

CMD ["node", "gateway/dist/index.js"]
```

- [ ] **Step 2: Build the Docker image locally to verify**

Run: `docker build -t meta-ads-mcp-gateway .`
Expected: Image builds successfully. Final image has both Node.js and Python.

- [ ] **Step 3: Quick smoke test**

Run:
```bash
docker run --rm -e PORT=8080 -e BASE_URL=http://localhost:8080 \
  -e OAUTH_CLIENT_ID=test -e OAUTH_CLIENT_SECRET=test \
  -e META_ACCESS_TOKEN=test -e RYZON_MODE=1 \
  -p 8080:8080 meta-ads-mcp-gateway &

sleep 3
curl -s http://localhost:8080/health
```
Expected: `{"status":"ok"}`

Then stop the container.

- [ ] **Step 4: Commit**

```bash
git add Dockerfile
git commit -m "feat: multi-stage Dockerfile for Node.js gateway + Python MCP server"
```

---

### Task 5: Create the deploy script

**Files:**
- Create: `scripts/deploy.sh`

Reference: `/Users/simonheinken/Documents/projects/context/ai-enablement/projects/daily-briefing/mcp/ryzon-briefing/scripts/deploy.sh`

- [ ] **Step 1: Ask user for OAuth credentials**

Before writing the script, ask the user for:
- The new OAuth 2.0 Client ID (from GCP console)
- The new OAuth 2.0 Client Secret (from GCP console)
- The current Meta access token

These will be embedded in the deploy script (same pattern as daily-briefing).

- [ ] **Step 2: Create `scripts/deploy.sh`**

```bash
#!/bin/bash
# Deploy meta-ads-mcp to Google Cloud Run

set -e

PROJECT_ID="gold-blueprint-357814"
SERVICE_NAME="meta-ads-mcp"
REGION="europe-west3"

# Get existing service URL (if redeploying)
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --project=$PROJECT_ID --region=$REGION --format='value(status.url)' 2>/dev/null || echo "")

# For first deploy, Cloud Run URLs are deterministic
if [ -z "$SERVICE_URL" ]; then
  PROJECT_HASH=$(gcloud run services list --project=$PROJECT_ID --region=$REGION --format='value(status.url)' --limit=1 2>/dev/null | grep -oP '(?<=-)\w+(?=-ew\.a\.run\.app)' || echo "")
  if [ -n "$PROJECT_HASH" ]; then
    SERVICE_URL="https://${SERVICE_NAME}-${PROJECT_HASH}-ew.a.run.app"
  else
    SERVICE_URL="https://${SERVICE_NAME}-k43m4vhxuq-ew.a.run.app"
  fi
fi

# OAuth credentials (from GCP Console)
OAUTH_CLIENT_ID="<TO_BE_PROVIDED>"
OAUTH_CLIENT_SECRET="<TO_BE_PROVIDED>"

# Meta access token
META_ACCESS_TOKEN="<TO_BE_PROVIDED>"

# Write env vars to temp YAML file
ENV_FILE=$(mktemp /tmp/meta-ads-mcp-env.XXXXXX.yaml)
cat > "$ENV_FILE" <<EOF
BASE_URL: '${SERVICE_URL}'
OAUTH_CLIENT_ID: '${OAUTH_CLIENT_ID}'
OAUTH_CLIENT_SECRET: '${OAUTH_CLIENT_SECRET}'
OAUTH_ALLOWED_DOMAIN: 'ryzon.net'
META_ACCESS_TOKEN: '${META_ACCESS_TOKEN}'
RYZON_MODE: '1'
EOF

echo "Building and deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
  --project=$PROJECT_ID \
  --region=$REGION \
  --source=. \
  --env-vars-file="$ENV_FILE" \
  --allow-unauthenticated \
  --memory=256Mi \
  --cpu=1 \
  --min-instances=0 \
  --max-instances=1 \
  --timeout=300

rm -f "$ENV_FILE"

SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --project=$PROJECT_ID --region=$REGION --format='value(status.url)')

echo ""
echo "========================================="
echo "Deployed! Service URL: $SERVICE_URL"
echo "========================================="
echo ""
echo "For claude.ai — Add as remote MCP server:"
echo "  Server URL: ${SERVICE_URL}/mcp"
echo ""
echo "For Claude Desktop / Claude Code — add to MCP config:"
cat <<JSONEOF

{
  "mcpServers": {
    "meta-ads": {
      "type": "url",
      "url": "${SERVICE_URL}/mcp"
    }
  }
}

JSONEOF
echo "Access restricted to @ryzon.net Google accounts."
```

- [ ] **Step 3: Make executable**

Run: `chmod +x scripts/deploy.sh`

- [ ] **Step 4: Commit**

```bash
git add scripts/deploy.sh
git commit -m "feat: add Cloud Run deployment script"
```

---

### Task 6: Deploy to Cloud Run

- [ ] **Step 1: Fill in OAuth credentials in `scripts/deploy.sh`**

Replace the `<TO_BE_PROVIDED>` placeholders with the actual values from the user.

- [ ] **Step 2: Run the deploy script**

Run: `cd /Users/simonheinken/Documents/projects/meta/mcp/meta-ads-mcp && bash scripts/deploy.sh`
Expected: Builds Docker image via Cloud Build, deploys to Cloud Run, prints service URL.

- [ ] **Step 3: Verify health endpoint**

Run: `curl -s https://<service-url>/health`
Expected: `{"status":"ok"}`

- [ ] **Step 4: Verify OAuth metadata endpoint**

Run: `curl -s https://<service-url>/.well-known/oauth-authorization-server`
Expected: JSON with authorization_endpoint, token_endpoint, etc.

- [ ] **Step 5: Test from claude.ai**

Add the server URL as a remote MCP in claude.ai Settings → MCP Servers. Authenticate with a `@ryzon.net` Google account. Ask "What ad accounts do I have access to?" — verify the tool call works.

- [ ] **Step 6: Test from Claude Desktop**

Add to `claude_desktop_config.json`:
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
Restart Claude Desktop. Ask "What ad accounts do I have access to?" — verify the tool call works.

- [ ] **Step 7: Commit deploy script with actual credentials (do NOT push — contains secrets)**

```bash
git add scripts/deploy.sh
git commit -m "chore: fill in deploy credentials"
```

Note: `scripts/deploy.sh` contains OAuth secrets and the Meta token. Add it to `.gitignore` if pushing to a shared repo, or keep it local-only.

---

### Task 7: Add deploy script to .gitignore and update docs

**Files:**
- Modify: `.gitignore` (if it exists, or the repo-level one)
- Modify: `CLAUDE.md`

- [ ] **Step 1: Add `scripts/deploy.sh` to `.gitignore`**

Since `deploy.sh` contains secrets (OAuth client secret, Meta token), ensure it's not pushed to the remote.

Add to the repo's `.gitignore`:
```
scripts/deploy.sh
```

- [ ] **Step 2: Update `CLAUDE.md` with Cloud Run deployment info**

Add a section to `meta-ads-mcp/CLAUDE.md`:

```markdown
### Cloud Run Deployment

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

The gateway spawns `python -m meta_ads_mcp` as a stdio subprocess per session. OAuth restricts access to `@ryzon.net` Google accounts.
```

- [ ] **Step 3: Commit**

```bash
git add .gitignore CLAUDE.md
git commit -m "docs: add Cloud Run deployment info and gitignore deploy secrets"
```
