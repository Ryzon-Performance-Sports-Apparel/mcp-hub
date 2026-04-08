"""Configuration for the Knowledge MCP server."""

import os
from dotenv import load_dotenv

load_dotenv()


class KnowledgeConfig:
    """Singleton configuration loaded from environment variables."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._loaded = False
        return cls._instance

    def __init__(self):
        if self._loaded:
            return
        self._loaded = True
        self.gcp_project_id = os.environ.get("GCP_PROJECT_ID", "")
        self.firestore_database = os.environ.get("FIRESTORE_DATABASE", "(default)")

    @property
    def is_configured(self) -> bool:
        return bool(self.gcp_project_id)

    def validate(self) -> str | None:
        if not self.gcp_project_id:
            return "Missing required environment variable: GCP_PROJECT_ID"
        return None


config = KnowledgeConfig()
