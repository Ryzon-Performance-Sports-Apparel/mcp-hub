"""Shared test fixtures for Knowledge MCP tests."""

import pytest
from knowledge_mcp.core.config import config


@pytest.fixture(autouse=True)
def mock_config():
    """Set env vars so KnowledgeConfig.validate() passes in all tests."""
    old_project = config.gcp_project_id
    config.gcp_project_id = "test-project"
    yield config
    config.gcp_project_id = old_project
