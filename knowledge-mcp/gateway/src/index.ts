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
  userEmail: string;
}

function spawnPythonProcess(userEmail: string): StdioClientTransport {
  return new StdioClientTransport({
    command: "python",
    args: ["-m", "knowledge_mcp"],
    env: {
      ...process.env as Record<string, string>,
      KNOWLEDGE_USER_EMAIL: userEmail,
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

  app.use(
    mcpAuthRouter({
      provider,
      issuerUrl: baseUrl,
      baseUrl,
      serviceDocumentationUrl: new URL(
        "https://github.com/Ryzon-Performance-Sports-Apparel/mcp-hub"
      ),
    })
  );

  app.get("/health", (_req, res) => {
    res.json({ status: "ok" });
  });

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

    // Extract authenticated user email from OAuth context
    const userEmail = (req as any).auth?.extra?.email as string | undefined;
    if (!userEmail) {
      res.status(403).json({ error: "No email in auth context" });
      return;
    }

    const newSessionId = randomUUID();
    const httpTransport = new StreamableHTTPServerTransport({
      sessionIdGenerator: () => newSessionId,
    });

    const stdioTransport = spawnPythonProcess(userEmail);

    httpTransport.onmessage = async (message: JSONRPCMessage) => {
      await stdioTransport.send(message);
    };

    stdioTransport.onmessage = async (message: JSONRPCMessage) => {
      await httpTransport.send(message);
    };

    stdioTransport.onerror = (error) => {
      console.error(`[${newSessionId}] stdio error:`, error.message);
    };

    httpTransport.onclose = () => {
      console.log(`[${newSessionId}] session closed (user: ${userEmail})`);
      stdioTransport.close();
      sessions.delete(newSessionId);
    };

    stdioTransport.onclose = () => {
      console.log(`[${newSessionId}] Python process exited`);
      httpTransport.close();
      sessions.delete(newSessionId);
    };

    await stdioTransport.start();
    sessions.set(newSessionId, { httpTransport, stdioTransport, userEmail });

    console.log(`[${newSessionId}] new session for ${userEmail}`);
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

  app.use((err: Error, _req: express.Request, res: express.Response, _next: express.NextFunction) => {
    console.error("Express error:", err.message, err.stack);
    if (!res.headersSent) {
      res.status(500).json({ error: err.message });
    }
  });

  app.listen(port, "0.0.0.0", () => {
    console.log(`knowledge-mcp gateway listening on port ${port}`);
    console.log(`  MCP:    ${baseUrl.origin}/mcp`);
    console.log(`  Health: ${baseUrl.origin}/health`);
    console.log(`  OAuth:  ${baseUrl.origin}/.well-known/oauth-authorization-server`);
  });
}

async function main() {
  if (PORT) {
    await startHttpServer(PORT);
  } else {
    console.error("No PORT set — running in stdio passthrough mode");
    console.error("Use PORT=8080 for HTTP mode");
    process.exit(1);
  }
}

main().catch((err) => {
  console.error("Failed to start knowledge-mcp gateway:", err);
  process.exit(1);
});
