"""
Knowledge MCP - Knowledge Base MCP Server

Search and retrieve documents from the central Firestore knowledge base.
"""

from knowledge_mcp.core.server import main

__version__ = "0.1.0"


def entrypoint():
    """Main entry point for the package."""
    return main()
