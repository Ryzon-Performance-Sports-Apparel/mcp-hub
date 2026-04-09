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
COPY pyproject.toml README.md ./
COPY knowledge_mcp/ ./knowledge_mcp/
RUN pip install --break-system-packages .

ENV PORT=8080
EXPOSE 8080

CMD ["node", "gateway/dist/index.js"]
