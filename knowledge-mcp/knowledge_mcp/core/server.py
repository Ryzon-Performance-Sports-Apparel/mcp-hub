"""MCP server configuration for Knowledge Base."""

import argparse
import sys

from mcp.server.fastmcp import FastMCP

from .utils import logger

mcp_server = FastMCP("knowledge")


def main():
    """Main entry point for the Knowledge MCP server."""
    logger.info("Knowledge MCP server starting")

    parser = argparse.ArgumentParser(
        description="Knowledge MCP Server - Knowledge Base via Model Context Protocol"
    )
    parser.add_argument("--version", action="store_true", help="Show version")
    args = parser.parse_args()

    if args.version:
        from knowledge_mcp import __version__
        print(f"Knowledge MCP v{__version__}")
        return 0

    logger.info("Starting MCP server with stdio transport")
    mcp_server.run(transport="stdio")
