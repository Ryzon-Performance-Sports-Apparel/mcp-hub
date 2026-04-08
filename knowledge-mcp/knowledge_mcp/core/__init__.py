"""Core functionality for Knowledge MCP server."""

from .server import mcp_server, main

# Import tool modules to trigger @mcp_server.tool() registration
from .tools_query import query_knowledge_base
from .tools_get import get_document
from .tools_semantic import search_knowledge_base_semantic
