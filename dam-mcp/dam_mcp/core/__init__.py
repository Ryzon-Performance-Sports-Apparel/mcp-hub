"""Core functionality for DAM MCP server."""

from .server import mcp_server, main

# Import tool modules to trigger @mcp_server.tool() registration
from .tools_list import list_assets
from .tools_get import get_asset
from .tools_download_url import get_asset_download_url
from .tools_upload import upload_asset
from .tools_tag import tag_asset
from .tools_search import search_assets
from .tools_sync import sync_status
from .tools_trigger_sync import trigger_sync
from .tools_figma_export import export_figma_frames
from .tools_query_kb import query_knowledge_base
from .tools_get_document import get_document
