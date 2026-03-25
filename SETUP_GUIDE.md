# MCP Servers Setup Guide

This guide walks you through setting up Meta Ads and/or Google Ads MCP servers for Claude Desktop on a Mac.

---

## What You Need Before Starting

Your admin should have sent you the following. If you don't have these, ask them.

**For Meta Ads MCP:**
- A Meta Ads access token

**For Google Ads MCP:**
- Google Ads Developer Token
- Google Cloud Project ID
- Google OAuth Client ID
- Google OAuth Client Secret

---

## Setup Steps

### Step 1: Open Terminal

Press `Cmd + Space`, type **Terminal**, and press Enter.

### Step 2: Run the install script

Copy-paste this entire line into Terminal and press Enter:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/<your-repo>/main/install.sh)"
```

### Step 3: Follow the prompts

The script will ask you:

1. **Which servers to install** — type `1` for Meta Ads, `2` for Google Ads, or `3` for both
2. **Your credentials** — paste the values your admin gave you when prompted
3. **Google login** (Google Ads only) — a browser window will open. Log in with the Google account that has access to your Google Ads data, and approve the permissions

The script handles everything else automatically (installing tools, configuring Claude Desktop).

### Step 4: Restart Claude Desktop

1. Right-click the Claude icon in your Dock
2. Click **Quit**
3. Open Claude Desktop again

### Step 5: Verify it works

In a new Claude conversation, try one of these prompts:

- **Meta Ads:** "What ad accounts do I have access to?"
- **Google Ads:** "What customers do I have access to?"

You should see Claude use the MCP tools to fetch your data.

---

## Troubleshooting

### Claude Desktop doesn't show the MCP tools (no hammer icon)
- Make sure you fully quit and reopened Claude Desktop (not just closed the window)
- Check the config was written:
  ```bash
  cat ~/Library/Application\ Support/Claude/claude_desktop_config.json
  ```

### "Command not found: uv"
Close Terminal, reopen it, and run the install script again.

### Google Ads: authentication errors
Re-run the install script and choose Google Ads. When prompted about existing credentials, choose `n` to re-authenticate.

### Meta Ads: "token expired" errors
Meta access tokens expire. Ask your admin for a new token, then re-run the install script.

### I had other settings in Claude Desktop
The script creates a backup at `claude_desktop_config.json.backup` in the same folder. Ask your admin to help merge settings if needed.
