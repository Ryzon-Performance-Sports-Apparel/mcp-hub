#!/bin/bash
set -e

echo ""
echo "=========================================="
echo "  MCP Servers Setup for Claude Desktop"
echo "=========================================="
echo ""

# ── 1. Install uv ──────────────────────────────────────────────────────────────
if ! command -v uv &> /dev/null; then
    echo "Installing uv package manager..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
    echo "  uv installed"
else
    echo "  uv already installed"
fi

UVX_PATH="$HOME/.local/bin/uvx"

# ── 2. Choose which servers to install ──────────────────────────────────────────
echo "Which MCP servers would you like to install?"
echo ""
echo "  1) Meta Ads MCP"
echo "  2) Google Ads MCP"
echo "  3) Both"
echo ""
read -rp "Enter choice [1/2/3]: " CHOICE < /dev/tty
echo ""

INSTALL_META=false
INSTALL_GOOGLE=false

case "$CHOICE" in
    1) INSTALL_META=true ;;
    2) INSTALL_GOOGLE=true ;;
    3) INSTALL_META=true; INSTALL_GOOGLE=true ;;
    *)
        echo "Invalid choice. Exiting."
        exit 1
        ;;
esac

# ── 3. Collect credentials ─────────────────────────────────────────────────────

# ── 3a. Meta Ads credentials ───────────────────────────────────────────────────
if $INSTALL_META; then
    echo "--- Meta Ads MCP ---"
    echo "Please paste your Meta Ads access token (input is hidden):"
    read -rs META_TOKEN < /dev/tty
    echo ""
    if [ -z "$META_TOKEN" ]; then
        echo "No token provided. Skipping Meta Ads MCP."
        INSTALL_META=false
    fi
fi

# ── 3b. Google Ads credentials + OAuth login ───────────────────────────────────
if $INSTALL_GOOGLE; then
    echo "--- Google Ads MCP ---"
    echo ""

    # Collect all Google credentials upfront
    read -rp "Google Ads Developer Token: " GOOGLE_DEV_TOKEN < /dev/tty
    read -rp "Google Cloud Project ID: " GOOGLE_PROJECT_ID < /dev/tty
    echo ""

    if [ -z "$GOOGLE_DEV_TOKEN" ] || [ -z "$GOOGLE_PROJECT_ID" ]; then
        echo "Missing Google Ads credentials. Skipping Google Ads MCP."
        INSTALL_GOOGLE=false
    fi
fi

if $INSTALL_GOOGLE; then
    # Check if Application Default Credentials already exist
    ADC_FILE="$HOME/.config/gcloud/application_default_credentials.json"

    if [ -f "$ADC_FILE" ]; then
        echo "  Google Application Default Credentials already exist at:"
        echo "  $ADC_FILE"
        echo ""
        read -rp "Use existing credentials? [y/n]: " USE_EXISTING < /dev/tty
        echo ""
        if [[ "$USE_EXISTING" =~ ^[Yy]$ ]]; then
            echo "  Using existing credentials."
            NEED_GOOGLE_LOGIN=false
        else
            NEED_GOOGLE_LOGIN=true
        fi
    else
        NEED_GOOGLE_LOGIN=true
    fi

    if $NEED_GOOGLE_LOGIN; then
        echo "We need to log you in to Google so the MCP server can access"
        echo "your Google Ads data. You'll need two values from your admin:"
        echo ""
        read -rp "Google OAuth Client ID: " GOOGLE_CLIENT_ID < /dev/tty
        read -rp "Google OAuth Client Secret: " GOOGLE_CLIENT_SECRET < /dev/tty
        echo ""

        if [ -z "$GOOGLE_CLIENT_ID" ] || [ -z "$GOOGLE_CLIENT_SECRET" ]; then
            echo "Missing OAuth credentials. Skipping Google Ads MCP."
            INSTALL_GOOGLE=false
        fi
    fi
fi

if $INSTALL_GOOGLE && ${NEED_GOOGLE_LOGIN:-false}; then
    # Install gcloud CLI if not present
    if ! command -v gcloud &> /dev/null; then
        # Also check common install locations not yet in PATH
        if [ -f "$HOME/google-cloud-sdk/bin/gcloud" ]; then
            export PATH="$HOME/google-cloud-sdk/bin:$PATH"
            echo "  gcloud CLI found at $HOME/google-cloud-sdk"
        elif [ -f "/usr/local/share/google-cloud-sdk/bin/gcloud" ]; then
            export PATH="/usr/local/share/google-cloud-sdk/bin:$PATH"
            echo "  gcloud CLI found at /usr/local/share/google-cloud-sdk"
        else
            echo "Installing Google Cloud CLI..."
            echo "(This may take a few minutes)"
            echo ""

            # Detect architecture for correct download
            ARCH=$(uname -m)
            if [ "$ARCH" = "arm64" ]; then
                GCLOUD_URL="https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-cli-darwin-arm.tar.gz"
            else
                GCLOUD_URL="https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-cli-darwin-x86_64.tar.gz"
            fi

            # Download and extract directly (no interactive installer)
            curl -sSL "$GCLOUD_URL" -o /tmp/google-cloud-sdk.tar.gz
            tar -xzf /tmp/google-cloud-sdk.tar.gz -C "$HOME"
            rm -f /tmp/google-cloud-sdk.tar.gz

            # Run install script non-interactively (adds to PATH in future shells)
            "$HOME/google-cloud-sdk/install.sh" --quiet --path-update true 2>/dev/null || true

            export PATH="$HOME/google-cloud-sdk/bin:$PATH"

            # Verify it worked
            if ! command -v gcloud &> /dev/null; then
                echo ""
                echo "Could not install gcloud automatically."
                echo "Please install it manually from: https://cloud.google.com/sdk/docs/install"
                echo "Then re-run this script."
                exit 1
            fi
            echo "  gcloud CLI installed"
        fi
    else
        echo "  gcloud CLI already installed"
    fi

    # Create a temporary OAuth client JSON file from the client ID and secret
    TEMP_CLIENT_JSON=$(mktemp /tmp/oauth_client_XXXXXX.json)
    cat > "$TEMP_CLIENT_JSON" << OAUTH_EOF
{
  "installed": {
    "client_id": "$GOOGLE_CLIENT_ID",
    "client_secret": "$GOOGLE_CLIENT_SECRET",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "redirect_uris": ["http://localhost"]
  }
}
OAUTH_EOF

    echo ""
    echo "A browser window will open. Please log in with the Google account"
    echo "that has access to your Google Ads data."
    echo ""
    read -rp "Press Enter to open the browser..." < /dev/tty

    # Run gcloud ADC login with the temporary client file
    gcloud auth application-default login \
        --scopes="https://www.googleapis.com/auth/adwords,https://www.googleapis.com/auth/cloud-platform" \
        --client-id-file="$TEMP_CLIENT_JSON"

    # Clean up the temporary file
    rm -f "$TEMP_CLIENT_JSON"

    echo "  Google authentication complete"
fi

# ── 3c. Pin the ADC quota project ────────────────────────────────────────────────
# The Google Ads client bills/quotas API calls against the ADC "quota project"
# (the x-goog-user-project header). If that points at a project where the Google
# Ads API is disabled, every call fails with 403 SERVICE_DISABLED — regardless of
# which account you query. The login above does NOT set this, so we set it
# explicitly to the project the user provided. (The GOOGLE_PROJECT_ID env var is
# NOT read by the server; the quota project is the real lever.)
if $INSTALL_GOOGLE; then
    # gcloud may not be on PATH on the "use existing credentials" path.
    if ! command -v gcloud &> /dev/null; then
        for GCLOUD_DIR in "$HOME/google-cloud-sdk/bin" "/usr/local/share/google-cloud-sdk/bin"; do
            [ -f "$GCLOUD_DIR/gcloud" ] && export PATH="$GCLOUD_DIR:$PATH" && break
        done
    fi

    if command -v gcloud &> /dev/null; then
        if gcloud auth application-default set-quota-project "$GOOGLE_PROJECT_ID" 2>/dev/null; then
            echo "  ADC quota project set to $GOOGLE_PROJECT_ID"
        else
            echo "  WARNING: could not set the ADC quota project. After install, run:"
            echo "    gcloud auth application-default set-quota-project $GOOGLE_PROJECT_ID"
        fi
    else
        echo "  WARNING: gcloud not found. After install, run:"
        echo "    gcloud auth application-default set-quota-project $GOOGLE_PROJECT_ID"
    fi
fi

if ! $INSTALL_META && ! $INSTALL_GOOGLE; then
    echo "Nothing to install. Exiting."
    exit 1
fi

# ── 4. Install packages ────────────────────────────────────────────────────────
echo ""
if $INSTALL_META; then
    echo "Installing meta-ads-mcp..."
    "$HOME/.local/bin/uv" tool install meta-ads-mcp --force
    echo "  meta-ads-mcp installed"
fi

if $INSTALL_GOOGLE; then
    echo "Installing google-ads-mcp..."
    # Migration: older installs used the upstream package (tool name
    # "google-ads-mcp", installed from git). It owns the same `google-ads-mcp`
    # executable as our PyPI package, so uninstall it first to avoid an
    # "executable already exists" conflict on re-runs.
    "$HOME/.local/bin/uv" tool uninstall google-ads-mcp >/dev/null 2>&1 || true
    "$HOME/.local/bin/uv" tool install ryzon-google-ads-mcp --force
    echo "  google-ads-mcp installed"
fi

# ── 5. Build Claude Desktop config ─────────────────────────────────────────────
CONFIG_DIR="$HOME/Library/Application Support/Claude"
CONFIG_FILE="$CONFIG_DIR/claude_desktop_config.json"
mkdir -p "$CONFIG_DIR"

# Back up existing config
if [ -f "$CONFIG_FILE" ]; then
    cp "$CONFIG_FILE" "$CONFIG_FILE.backup"
    echo "  Backed up existing config to claude_desktop_config.json.backup"
fi

# Start building the mcpServers JSON
SERVERS=""

if $INSTALL_META; then
    SERVERS="$SERVERS
    \"meta-ads\": {
      \"command\": \"$UVX_PATH\",
      \"args\": [\"meta-ads-mcp\"],
      \"env\": {
        \"META_ACCESS_TOKEN\": \"$META_TOKEN\"
      }
    }"
fi

if $INSTALL_GOOGLE; then
    if [ -n "$SERVERS" ]; then
        SERVERS="$SERVERS,"
    fi
    SERVERS="$SERVERS
    \"google-ads-mcp\": {
      \"command\": \"$UVX_PATH\",
      \"args\": [\"--from\", \"ryzon-google-ads-mcp\", \"google-ads-mcp\"],
      \"env\": {
        \"GOOGLE_ADS_DEVELOPER_TOKEN\": \"$GOOGLE_DEV_TOKEN\"
      }
    }"
fi

cat > "$CONFIG_FILE" << EOF
{
  "mcpServers": {$SERVERS
  }
}
EOF

echo "  Claude Desktop configured"
echo ""
echo "=========================================="
echo "  Done! Please restart Claude Desktop."
echo "=========================================="
echo ""
