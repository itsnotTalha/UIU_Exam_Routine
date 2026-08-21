from __future__ import annotations

import os
import sys
from pathlib import Path


def app_data_dir() -> Path:
    """Return the platform-native per-user data directory."""
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        if base:
            return Path(base) / "UIU Exam Widget"
        return Path.home() / "AppData" / "Local" / "UIU Exam Widget"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "UIU Exam Widget"
    return Path.home() / ".local" / "share" / "uiu-exam-widget"


APP_DIR = app_data_dir()
CACHE_FILE = APP_DIR / "routine-cache.json"
PANEL_CACHE_FILE = APP_DIR / "panel-cache.json"
