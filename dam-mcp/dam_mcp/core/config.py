"""Configuration for the DAM MCP server."""

import os

from dotenv import load_dotenv

load_dotenv()


class DamConfig:
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
        self.gcs_bucket_name = os.environ.get("GCS_BUCKET_NAME", "")
        self.gdrive_folder_id = os.environ.get("GDRIVE_FOLDER_ID", "")
        self.signed_url_expiry_minutes = int(
            os.environ.get("SIGNED_URL_EXPIRY_MINUTES", "60")
        )
        self.firestore_database = os.environ.get("FIRESTORE_DATABASE", "(default)")
        self.config_sheet_id = os.environ.get("CONFIG_SHEET_ID", "")
        self.config_sheet_name = os.environ.get("CONFIG_SHEET_NAME", "Sheet1")

    @property
    def is_configured(self) -> bool:
        return bool(self.gcp_project_id and self.gcs_bucket_name)

    def validate(self) -> str | None:
        """Returns an error message if required config is missing, else None."""
        missing = []
        if not self.gcp_project_id:
            missing.append("GCP_PROJECT_ID")
        if not self.gcs_bucket_name:
            missing.append("GCS_BUCKET_NAME")
        if missing:
            return f"Missing required environment variables: {', '.join(missing)}"
        return None


config = DamConfig()
