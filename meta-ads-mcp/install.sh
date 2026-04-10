#!/bin/bash
set -e

echo ""
echo "=== Meta Ads MCP Setup ==="
echo ""

# 1. Install uv (handles Python automatically, no Xcode or Homebrew needed)
if ! command -v uv &> /dev/null; then
    echo "Installing uv package manager..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
    echo "✅ uv installed"
else
    echo "✅ uv already installed"
fi

UVX_PATH="$HOME/.local/bin/uvx"

# 2. Install meta-ads-mcp
echo "Installing meta-ads-mcp..."
"$HOME/.local/bin/uv" tool install meta-ads-mcp --force
echo "✅ meta-ads-mcp installed"

# 3. Ask for the token
echo ""
echo "Please paste the Meta Ads access token (input is hidden):"
read -rs META_TOKEN < /dev/tty
echo ""

if [ -z "$META_TOKEN" ]; then
    echo "❌ No token provided. Exiting."
    exit 1
fi

# 4. Write Claude Desktop config
CONFIG_DIR="$HOME/Library/Application Support/Claude"
CONFIG_FILE="$CONFIG_DIR/claude_desktop_config.json"
mkdir -p "$CONFIG_DIR"

if [ -f "$CONFIG_FILE" ]; then
    cp "$CONFIG_FILE" "$CONFIG_FILE.backup"
    echo "⚠️  Backed up existing config to claude_desktop_config.json.backup"
fi

cat > "$CONFIG_FILE" << EOF
{
  "mcpServers": {
    "meta-ads": {
      "command": "$UVX_PATH",
      "args": ["meta-ads-mcp"],
      "env": {
        "META_ACCESS_TOKEN": "$META_TOKEN"
      }
    }
  }
}
EOF

echo "✅ Claude Desktop configured"
echo ""
echo "=== Done! Please restart Claude Desktop. ==="
echo ""
