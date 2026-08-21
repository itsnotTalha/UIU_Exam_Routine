from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

from models import Exam


APP_DIR = Path.home() / ".local" / "share" / "uiu-exam-widget"
CACHE_FILE = APP_DIR / "routine-cache.json"


def save_routine(mode: str, username: str, exams: List[Exam]) -> None:
    """Persist routine data locally. Passwords are never accepted or stored."""
    APP_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "mode": mode,
        "username": username,
        "fetched_at": datetime.now().isoformat(timespec="seconds"),
        "exams": [exam.fields for exam in exams],
    }
    temp_file = CACHE_FILE.with_suffix(".tmp")
    temp_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temp_file.replace(CACHE_FILE)


def load_routine() -> Optional[Tuple[str, str, str, List[Exam]]]:
    if not CACHE_FILE.exists():
        return None
    try:
        data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        exams = [Exam(fields=dict(fields)) for fields in data.get("exams", []) if isinstance(fields, dict)]
        if not exams:
            return None
        return (
            str(data.get("mode", "student")),
            str(data.get("username", "")),
            str(data.get("fetched_at", "")),
            exams,
        )
    except (OSError, ValueError, TypeError):
        return None


def clear_routine() -> None:
    try:
        CACHE_FILE.unlink()
    except FileNotFoundError:
        pass
