"""Shared test fixtures for Knowledge MCP tests."""

import pytest
from knowledge_mcp.core.config import config


@pytest.fixture(autouse=True)
def mock_config():
    """Set env vars so KnowledgeConfig.validate() passes in all tests."""
    old_project = config.gcp_project_id
    old_user_email = getattr(config, "_user_email", None)
    config.gcp_project_id = "test-project"
    config._user_email = "test@ryzon.net"
    yield config
    config.gcp_project_id = old_project
    config._user_email = old_user_email
