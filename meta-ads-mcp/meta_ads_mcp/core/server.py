"""MCP server configuration for Meta Ads API."""

from mcp.server.fastmcp import FastMCP
import argparse
import os
import sys
from .resources import list_resources, get_resource
from .utils import logger

# Initialize FastMCP server
mcp_server = FastMCP("meta-ads")

# Register resource URIs
mcp_server.resource(uri="meta-ads://resources")(list_resources)
mcp_server.resource(uri="meta-ads://images/{resource_id}")(get_resource)


def main():
    """Main entry point for the package"""
    logger.info("Meta Ads MCP server starting")
    logger.debug(f"Python version: {sys.version}")
    logger.debug(f"Args: {sys.argv}")

    parser = argparse.ArgumentParser(
        description="Meta Ads MCP Server - Model Context Protocol server for Meta Ads API"
    )
    parser.add_argument("--app-id", type=str, help="Meta App ID (Client ID) for authentication")
    parser.add_argument("--version", action="store_true", help="Show the version of the package")

    args = parser.parse_args()

    # Update app ID if provided as environment variable or command line arg
    from .auth import auth_manager, meta_config

    env_app_id = os.environ.get("META_APP_ID")
    if args.app_id:
        auth_manager.app_id = args.app_id
        meta_config.set_app_id(args.app_id)
    elif env_app_id:
        auth_manager.app_id = env_app_id
        meta_config.set_app_id(env_app_id)

    # Show version if requested
    if args.version:
        from meta_ads_mcp import __version__
        print(f"Meta Ads MCP v{__version__}")
        return 0

    # Start stdio transport
    logger.info("Starting MCP server with stdio transport")
    mcp_server.run(transport='stdio')
