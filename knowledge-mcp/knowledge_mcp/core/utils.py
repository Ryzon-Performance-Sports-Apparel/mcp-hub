"""Utilities for the Knowledge MCP server."""

import logging
import pathlib
import platform
import os


def _get_log_dir() -> pathlib.Path:
    if platform.system() == "Darwin":
        base = pathlib.Path.home() / "Library" / "Application Support"
    elif platform.system() == "Windows":
        base = pathlib.Path(os.environ.get("APPDATA", pathlib.Path.home()))
    else:
        base = pathlib.Path.home() / ".config"
    log_dir = base / "knowledge-mcp"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def _setup_logger() -> logging.Logger:
    _logger = logging.getLogger("knowledge_mcp")
    _logger.setLevel(logging.DEBUG)
    try:
        log_path = _get_log_dir() / "knowledge_mcp_debug.log"
        handler = logging.FileHandler(str(log_path), encoding="utf-8")
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        _logger.addHandler(handler)
    except Exception:
        pass
    return _logger


logger = _setup_logger()
