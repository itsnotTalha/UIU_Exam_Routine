from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import objc
from AppKit import (
    NSApplication,
    NSApplicationActivationPolicyAccessory,
    NSStatusBar,
    NSVariableStatusItemLength,
)
from Foundation import NSObject, NSTimer
from PyObjCTools import AppHelper

from paths import PANEL_CACHE_FILE


RUNTIME_DIR = Path(__file__).resolve().parent
APP_BUNDLE = Path.home() / "Applications" / "UIU Exam Widget.app"


def _parse_iso(value: Any) -> Optional[datetime]:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value))
        if dt.tzinfo is None:
            return dt.astimezone()
        return dt
    except (ValueError, TypeError):
        return None


def _duration(seconds: float) -> str:
    seconds = max(0, int(seconds))
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes = rem // 60

    if days:
        return f"{days}d {hours}h"
    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m"
    return "<1m"


def _room_suffix(room: Any) -> str:
    room = str(room or "").strip()
    return f" · R{room}" if room and room != "—" else ""


def _read_payload() -> Optional[dict[str, Any]]:
    try:
        if not PANEL_CACHE_FILE.exists():
            return None
        data = json.loads(PANEL_CACHE_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (OSError, ValueError, TypeError):
        return None


def _indicator_state(now: Optional[datetime] = None) -> tuple[str, str]:
    now = now or datetime.now().astimezone()
    payload = _read_payload()

    if not payload:
        return "UIU · Fetch routine", "No saved routine. Click to open UIU Exam Widget."

    exams = payload.get("exams")
    if not isinstance(exams, list) or not exams:
        return "UIU · Fetch routine", "No saved routine. Click to open UIU Exam Widget."

    live: list[tuple[datetime, dict[str, Any], Optional[datetime]]] = []
    upcoming: list[tuple[datetime, dict[str, Any], Optional[datetime]]] = []

    for raw in exams:
        if not isinstance(raw, dict):
            continue
        start = _parse_iso(raw.get("start"))
        end = _parse_iso(raw.get("end"))
        if start is None:
            continue

        # Compare everything in the current local timezone.
        local_start = start.astimezone(now.tzinfo)
        local_end = end.astimezone(now.tzinfo) if end is not None else None

        if local_start <= now and (local_end is None or now <= local_end):
            live.append((local_start, raw, local_end))
        elif local_start > now:
            upcoming.append((local_start, raw, local_end))

    if live:
        start, exam, end = min(live, key=lambda item: item[0])
        course = str(exam.get("course_code") or "Exam").strip()
        room = _room_suffix(exam.get("room"))
        if end is not None:
            remaining = _duration((end - now).total_seconds())
            title = f"{course} · LIVE {remaining}{room}"
            tooltip = f"{course} is in progress · {remaining} left{room}"
        else:
            title = f"{course} · LIVE{room}"
            tooltip = f"{course} is in progress{room}"
        return title, tooltip

    if upcoming:
        start, exam, end = min(upcoming, key=lambda item: item[0])
        course = str(exam.get("course_code") or "Exam").strip()
        room = _room_suffix(exam.get("room"))
        remaining = _duration((start - now).total_seconds())
        title = f"{course} · {remaining}{room}"
        tooltip = (
            f"Next exam: {course} · {start.strftime('%a, %d %b at %I:%M %p').replace(' 0', ' ')}"
            f"{room} · Click to open full routine"
        )
        return title, tooltip

    return "✓ You're good now", "All saved exams are over. Click to open the full routine."


class MenuBarController(NSObject):
    def init(self):
        self = objc.super(MenuBarController, self).init()
        if self is None:
            return None

        self.status_item = NSStatusBar.systemStatusBar().statusItemWithLength_(NSVariableStatusItemLength)
        button = self.status_item.button()
        button.setTarget_(self)
        button.setAction_("openMain:")

        self.timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            15.0,
            self,
            "timerFired:",
            None,
            True,
        )
        self.refresh()
        return self

    @objc.IBAction
    def openMain_(self, sender):
        try:
            if APP_BUNDLE.exists():
                subprocess.Popen(
                    ["open", str(APP_BUNDLE)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
            else:
                subprocess.Popen(
                    [sys.executable, str(RUNTIME_DIR / "main.py")],
                    cwd=str(RUNTIME_DIR),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
        except OSError:
            pass

    def timerFired_(self, timer):
        self.refresh()

    def refresh(self):
        title, tooltip = _indicator_state()
        button = self.status_item.button()
        button.setTitle_(title)
        button.setToolTip_(tooltip)


def main() -> None:
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)

    # Keep a strong reference for the lifetime of the process.
    controller = MenuBarController.alloc().init()
    globals()["_controller"] = controller
    AppHelper.runEventLoop()


if __name__ == "__main__":
    main()
