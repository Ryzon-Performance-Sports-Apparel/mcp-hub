"""Authentication related functionality for Meta Ads API."""

from typing import Any, Dict, Optional
import time
import platform
import pathlib
import os
import json
from .utils import logger

# Auth constants
AUTH_SCOPE = "business_management,public_profile,pages_show_list,pages_read_engagement"
AUTH_REDIRECT_URI = "http://localhost:8888/callback"
AUTH_RESPONSE_TYPE = "token"

logger.info("Authentication module initialized")

# Global flag for authentication state
needs_authentication = False


class MetaConfig:
    """Meta configuration singleton"""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MetaConfig, cls).__new__(cls)
            cls._instance.app_id = os.environ.get("META_APP_ID", "779761636818489")
        return cls._instance

    def set_app_id(self, app_id):
        self.app_id = app_id
        os.environ["META_APP_ID"] = app_id

    def get_app_id(self):
        if hasattr(self, 'app_id') and self.app_id:
            return self.app_id
        env_app_id = os.environ.get("META_APP_ID", "")
        if env_app_id:
            self.app_id = env_app_id
            return env_app_id
        return ""

    def is_configured(self):
        return bool(self.get_app_id())


meta_config = MetaConfig()


class TokenInfo:
    """Stores token information including expiration"""
    def __init__(self, access_token: str, expires_in: Optional[int] = None, user_id: Optional[str] = None):
        self.access_token = access_token
        self.expires_in = expires_in
        self.user_id = user_id
        self.created_at = int(time.time())

    def is_expired(self) -> bool:
        if not self.expires_in:
            return False
        return int(time.time()) > (self.created_at + self.expires_in)

    def serialize(self) -> Dict[str, Any]:
        return {
            "access_token": self.access_token,
            "expires_in": self.expires_in,
            "user_id": self.user_id,
            "created_at": self.created_at
        }

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> 'TokenInfo':
        token = cls(
            access_token=data.get("access_token", ""),
            expires_in=data.get("expires_in"),
            user_id=data.get("user_id")
        )
        token.created_at = data.get("created_at", int(time.time()))
        return token


class AuthManager:
    """Manages authentication with Meta APIs via cached tokens."""
    def __init__(self, app_id: str, redirect_uri: str = AUTH_REDIRECT_URI):
        self.app_id = app_id
        self.redirect_uri = redirect_uri
        self.token_info = None
        self._load_cached_token()

    def _get_token_cache_path(self) -> pathlib.Path:
        if platform.system() == "Windows":
            base_path = pathlib.Path(os.environ.get("APPDATA", ""))
        elif platform.system() == "Darwin":
            base_path = pathlib.Path.home() / "Library" / "Application Support"
        else:
            base_path = pathlib.Path.home() / ".config"
        cache_dir = base_path / "meta-ads-mcp"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir / "token_cache.json"

    def _load_cached_token(self) -> bool:
        cache_path = self._get_token_cache_path()
        if not cache_path.exists():
            return False
        try:
            with open(cache_path, "r") as f:
                data = json.load(f)
                required_fields = ["access_token", "created_at"]
                if not all(field in data for field in required_fields):
                    return False
                if not data.get("access_token") or len(data["access_token"]) < 20:
                    return False
                self.token_info = TokenInfo.deserialize(data)
                if self.token_info.is_expired():
                    try:
                        cache_path.unlink()
                    except Exception:
                        pass
                    self.token_info = None
                    return False
                # Reject tokens older than 60 days
                if self.token_info.created_at and (int(time.time()) - self.token_info.created_at) > (60 * 24 * 3600):
                    try:
                        cache_path.unlink()
                    except Exception:
                        pass
                    self.token_info = None
                    return False
                return True
        except Exception:
            try:
                cache_path.unlink()
            except Exception:
                pass
            return False

    def _save_token_to_cache(self) -> None:
        if not self.token_info:
            return
        cache_path = self._get_token_cache_path()
        try:
            with open(cache_path, "w") as f:
                json.dump(self.token_info.serialize(), f)
        except Exception as e:
            logger.error(f"Error saving token to cache: {e}")

    def get_auth_url(self) -> str:
        return (
            f"https://www.facebook.com/v24.0/dialog/oauth?"
            f"client_id={self.app_id}&"
            f"redirect_uri={self.redirect_uri}&"
            f"scope={AUTH_SCOPE}&"
            f"response_type={AUTH_RESPONSE_TYPE}"
        )

    def authenticate(self, force_refresh: bool = False) -> Optional[str]:
        if not force_refresh and self.token_info and not self.token_info.is_expired():
            return self.token_info.access_token
        return None

    def get_access_token(self) -> Optional[str]:
        if not self.token_info or self.token_info.is_expired():
            return None
        return self.token_info.access_token

    def invalidate_token(self) -> None:
        if self.token_info:
            logger.info(f"Invalidating token: {self.token_info.access_token[:10]}...")
            self.token_info = None
            global needs_authentication
            needs_authentication = True
            try:
                cache_path = self._get_token_cache_path()
                if cache_path.exists():
                    os.remove(cache_path)
            except Exception as e:
                logger.error(f"Error removing cached token file: {e}")

    def clear_token(self) -> None:
        self.invalidate_token()


async def get_current_access_token() -> Optional[str]:
    """Get the current access token, prioritizing META_ACCESS_TOKEN env var."""
    env_token = os.environ.get("META_ACCESS_TOKEN")
    if env_token:
        if len(env_token) < 20:
            logger.error("TOKEN VALIDATION FAILED: Token from environment variable appears malformed")
            return None
        return env_token

    global auth_manager
    try:
        token = auth_manager.get_access_token()
        if token:
            if len(token) < 20:
                logger.error("TOKEN VALIDATION FAILED: Token appears malformed")
                auth_manager.invalidate_token()
                return None
            return token
        else:
            logger.warning("No valid access token available. Set META_ACCESS_TOKEN environment variable.")
            return None
    except Exception as e:
        logger.error(f"Error getting access token: {str(e)}")
        return None


def login():
    """Start the login flow — placeholder for direct token auth."""
    print("Direct token authentication is used.")
    print("Set the META_ACCESS_TOKEN environment variable with your Meta access token.")


# Initialize auth manager
META_APP_ID = os.environ.get("META_APP_ID", "YOUR_META_APP_ID")
auth_manager = AuthManager(META_APP_ID)
