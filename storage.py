from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

from models import Exam


APP_DIR = Path.home() / ".local" / "share" / "uiu-exam-widget"
CACHE_FILE = APP_DIR / "routine-cache.json"
PANEL_CACHE_FILE = APP_DIR / "panel-cache.json"


def _iso_local(dt):
    if dt is None:
        return None
    # Include the local UTC offset so the GNOME extension can compare times safely.
    return dt.astimezone().isoformat(timespec="seconds")


def write_panel_cache(mode: str, username: str, exams: List[Exam]) -> None:
    """Write a small, normalized cache consumed by the GNOME Shell extension."""
    APP_DIR.mkdir(parents=True, exist_ok=True)
    panel_exams = []

    for exam in exams:
        start = exam.start_datetime()
        end = exam.end_datetime()
        room = exam.assigned_room(username) if mode == "student" else exam.room

        panel_exams.append({
            "course_code": exam.course_code,
            "course_name": exam.course_name,
            "section": exam.section,
            "room": room,
            "start": _iso_local(start),
            "end": _iso_local(end),
        })

    payload = {
        "version": 1,
        "mode": mode,
        "username": username,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "exams": panel_exams,
    }

    temp_file = PANEL_CACHE_FILE.with_suffix(".tmp")
    temp_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temp_file.replace(PANEL_CACHE_FILE)


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
    write_panel_cache(mode, username, exams)


def load_routine() -> Optional[Tuple[str, str, str, List[Exam]]]:
    if not CACHE_FILE.exists():
        return None
    try:
        data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        exams = [Exam(fields=dict(fields)) for fields in data.get("exams", []) if isinstance(fields, dict)]
        if not exams:
            return None

        mode = str(data.get("mode", "student"))
        username = str(data.get("username", ""))
        fetched_at = str(data.get("fetched_at", ""))

        # Automatically migrate older cached routines so the panel extension works
        # without forcing another ExamCon login.
        try:
            write_panel_cache(mode, username, exams)
        except OSError:
            pass

        return mode, username, fetched_at, exams
    except (OSError, ValueError, TypeError):
        return None


def clear_routine() -> None:
    for path in (CACHE_FILE, PANEL_CACHE_FILE):
        try:
            path.unlink()
        except FileNotFoundError:
            pass
