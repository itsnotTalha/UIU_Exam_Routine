from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, QTimer, Qt, Signal
from PySide6.QtGui import QAction, QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from models import Exam


class WindowsTrayController(QObject):
    """Native Windows system-tray controller for the UIU Exam Widget."""

    request_open = Signal()
    request_tiles = Signal()
    request_quit = Signal()

    def __init__(self, window, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.window = window
        self.tray = QSystemTrayIcon(self)
        self.tray.setToolTip("UIU Exam Widget")

        self.menu = QMenu()
        self.status_action = QAction("UIU Exam Widget")
        self.status_action.setEnabled(False)
        self.menu.addAction(self.status_action)

        self.detail_action = QAction("No saved routine")
        self.detail_action.setEnabled(False)
        self.menu.addAction(self.detail_action)

        self.menu.addSeparator()
        open_action = self.menu.addAction("Open Routine")
        open_action.triggered.connect(self.request_open.emit)

        tiles_action = self.menu.addAction("Show Desktop Tiles")
        tiles_action.triggered.connect(self.request_tiles.emit)

        self.menu.addSeparator()
        quit_action = self.menu.addAction("Exit")
        quit_action.triggered.connect(self.request_quit.emit)

        self.tray.setContextMenu(self.menu)
        self.tray.activated.connect(self._activated)

        self.timer = QTimer(self)
        self.timer.setInterval(30_000)
        self.timer.timeout.connect(self.refresh)
        self.timer.start()
        self.refresh()

    def show(self):
        self.tray.show()
        self.refresh()

    def hide(self):
        self.tray.hide()

    def _activated(self, reason):
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.request_open.emit()

    @staticmethod
    def _icon(accent: str, glyph: str = "U") -> QIcon:
        size = 64
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(accent))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(5, 5, 54, 54, 15, 15)
        painter.setPen(QColor("#ffffff"))
        font = QFont("Segoe UI", 28, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, glyph)
        painter.end()
        return QIcon(pix)

    @staticmethod
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

    @staticmethod
    def _next_exam(exams: list[Exam], now: datetime):
        live = []
        upcoming = []
        for exam in exams:
            start = exam.start_datetime()
            end = exam.end_datetime()
            if start is None:
                continue
            if start <= now and (end is None or now <= end):
                live.append((start, exam))
            elif start > now:
                upcoming.append((start, exam))
        if live:
            return min(live, key=lambda item: item[0])[1], "live"
        if upcoming:
            return min(upcoming, key=lambda item: item[0])[1], "upcoming"
        return None, "done"

    @staticmethod
    def _accent(exam: Optional[Exam], state: str, now: datetime) -> str:
        if exam is None:
            return "#22c55e" if state == "done" else "#64748b"
        if state == "live":
            return "#ff334f"
        start = exam.start_datetime()
        if start is None:
            return "#64748b"
        seconds = max(0, (start - now).total_seconds())
        if seconds <= 3600:
            return "#ff334f"
        if seconds <= 6 * 3600:
            return "#ef4444"
        if seconds <= 24 * 3600:
            return "#f97316"
        if seconds <= 3 * 86400:
            return "#f59e0b"
        return "#3b82f6"

    def refresh(self):
        now = datetime.now()
        exams = list(getattr(self.window, "exams", []) or [])

        if not exams:
            self.tray.setIcon(self._icon("#64748b"))
            self.tray.setToolTip("UIU Exam Widget\nNo saved routine — click to fetch")
            self.status_action.setText("No saved routine")
            self.detail_action.setText("Click the tray icon to open UIU Exam Widget")
            return

        exam, state = self._next_exam(exams, now)
        accent = self._accent(exam, state, now)
        glyph = "✓" if state == "done" else "U"
        self.tray.setIcon(self._icon(accent, glyph))

        if state == "done" or exam is None:
            title = "✓ You're good now"
            details = "All saved exams are over."
            tooltip = f"UIU Exam Widget\n{title}"
        else:
            room = exam.assigned_room(self.window.username.text().strip()) if self.window.selected_mode() == "student" else exam.room
            start = exam.start_datetime()
            end = exam.end_datetime()
            if state == "live":
                left = self._duration((end - now).total_seconds()) if end else "in progress"
                title = f"{exam.course_code} · LIVE"
                details = f"Room {room or '—'} · {left} left"
            else:
                until = self._duration((start - now).total_seconds()) if start else "Time unavailable"
                title = f"{exam.course_code} · {until}"
                details = f"Room {room or '—'} · {start.strftime('%a %d %b, %I:%M %p').lstrip('0') if start else ''}"
            tooltip = f"UIU Exam Widget\n{title}\n{details}"

        self.tray.setToolTip(tooltip)
        self.status_action.setText(title)
        self.detail_action.setText(details)
