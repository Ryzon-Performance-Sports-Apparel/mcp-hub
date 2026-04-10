"""Authentication tool for Meta Ads API."""

import json
import os
from typing import Optional
from .server import mcp_server

# Only register the login link tool if not explicitly disabled
ENABLE_LOGIN_LINK = not bool(os.environ.get("META_ADS_DISABLE_LOGIN_LINK", ""))


async def get_login_link(access_token: Optional[str] = None) -> str:
    """
    Get authentication status and instructions for Meta Ads.

    Args:
        access_token: Meta API access token (optional - will use cached token if not provided)

    Returns:
        Authentication status and instructions
    """
    env_token = os.environ.get("META_ACCESS_TOKEN")

    if access_token or env_token:
        token = access_token or env_token
        return json.dumps({
            "message": "Already Authenticated",
            "status": "You're authenticated with Meta Ads!",
            "token_info": f"Token preview: {token[:10]}...",
            "ready_to_use": "You can now use all Meta Ads MCP tools."
        }, indent=2)

    return json.dumps({
        "message": "Authentication Required",
        "instructions": "Set the META_ACCESS_TOKEN environment variable with your Meta access token.",
        "how_to_get_token": [
            "Go to https://developers.facebook.com/tools/explorer/",
            "Select your app and generate an access token",
            "Set it as META_ACCESS_TOKEN in your environment or Claude Desktop config"
        ]
    }, indent=2)


if ENABLE_LOGIN_LINK:
    get_login_link = mcp_server.tool()(get_login_link)
