from __future__ import annotations

import re
import sys
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from PySide6.QtCore import QObject, QThread, Signal, Qt, QPoint, QSettings, QTimer
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtGui import QMouseEvent, QCloseEvent
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QMessageBox,
    QScrollArea,
    QFrame,
    QComboBox,
    QSizeGrip,
    QSizePolicy,
)

from examcon import fetch_exam_routine
from models import Exam
from storage import save_routine, load_routine, clear_routine


APP_QSS = """
QWidget {
    color: #eef2f7;
    font-family: "SF Pro Text", "Helvetica Neue", Arial, Sans-Serif;
    font-size: 14px;
}
QWidget#appWindow, QWidget#resultsWidget, QScrollArea {
    background: #0b0f19;
}
QLabel { background: transparent; border: none; }
QFrame#toolbar {
    background: #111827;
    border: 1px solid #263249;
    border-radius: 16px;
}
QLineEdit, QComboBox {
    background: #0d1422;
    border: 1px solid #2a3852;
    border-radius: 10px;
    padding: 10px 12px;
    min-height: 20px;
    selection-background-color: #5773ff;
}
QLineEdit:focus, QComboBox:focus { border: 1px solid #7187ff; }
QComboBox::drop-down { border: none; width: 26px; }
QPushButton {
    background: #5570f6;
    border: none;
    border-radius: 10px;
    padding: 10px 16px;
    font-weight: 700;
}
QPushButton:hover { background: #657df8; }
QPushButton:pressed { background: #465ed6; }
QPushButton:disabled { background: #222d40; color: #68758c; }
QPushButton#secondaryButton {
    background: #141d2e;
    border: 1px solid #2a3852;
    color: #cbd5e1;
}
QPushButton#secondaryButton:hover { background: #1b263a; }
QPushButton#dangerButton {
    background: transparent;
    border: 1px solid #51323e;
    color: #d8aab8;
}
QPushButton#dangerButton:hover { background: #21151b; }
QPushButton#closeTileButton {
    background: transparent;
    border: none;
    color: #8d9ab0;
    padding: 2px;
    border-radius: 7px;
    font-size: 18px;
}
QPushButton#closeTileButton:hover { background: #202b3e; color: white; }
QFrame#routineCard, QFrame#nextRoutineCard, QFrame#liveRoutineCard {
    background: #111827;
    border: 1px solid #27334a;
    border-radius: 17px;
}
QFrame#nextRoutineCard { border: 2px solid #657df8; }
QFrame#liveRoutineCard { border: 2px solid #34d399; }
QFrame#datePanel, QFrame#timePanel {
    background: #0d1422;
    border: 1px solid #26344d;
    border-radius: 13px;
}
QFrame#roomPanel {
    background: #17213a;
    border: 1px solid #6078f0;
    border-radius: 13px;
}
QFrame#stickyCard, QFrame#stickyFeatured, QFrame#stickyLive {
    background: #111827;
    border: 1px solid #334158;
    border-radius: 17px;
}
QFrame#stickyFeatured { border: 2px solid #657df8; }
QFrame#stickyLive { border: 2px solid #34d399; }
QLabel#pageTitle { color: #ffffff; font-size: 22px; font-weight: 800; }
QLabel#pageSubtitle, QLabel#muted { color: #8f9bb0; }
QLabel#clock { color: #aeb8ca; font-size: 12px; }
QLabel#courseCode { color: #ffffff; font-size: 21px; font-weight: 800; }
QLabel#courseName { color: #b7c2d2; font-size: 13px; }
QLabel#dateDay { color: #ffffff; font-size: 27px; font-weight: 800; }
QLabel#dateMonth { color: #9eabbe; font-size: 12px; font-weight: 800; }
QLabel#weekday { color: #77869d; font-size: 11px; }
QLabel#metricCaption { color: #8fa0bd; font-size: 10px; font-weight: 800; }
QLabel#timeValue { color: #ffffff; font-size: 17px; font-weight: 800; }
QLabel#timeSecondary { color: #b9c3d5; font-size: 14px; font-weight: 700; }
QLabel#roomLabel { color: #9eaef5; font-size: 10px; font-weight: 800; }
QLabel#roomValue { color: #ffffff; font-size: 30px; font-weight: 900; }
QLabel#nextBadge {
    background: #182130;
    color: #dbe7ff;
    border: 1px solid #31415a;
    border-radius: 7px;
    padding: 4px 8px;
    font-size: 10px;
    font-weight: 800;
}
QLabel#liveBadge {
    background: #32151b;
    color: #ff7387;
    border: 1px solid #a92e42;
    border-radius: 7px;
    padding: 4px 8px;
    font-size: 10px;
    font-weight: 800;
}
QLabel#sectionBadge {
    background: #172137;
    color: #b7c2d6;
    border: 1px solid #31405a;
    border-radius: 8px;
    padding: 3px 7px;
    font-size: 10px;
}
QLabel#statusUpcoming {
    color: #aebaff;
    background: #17203a;
    border-radius: 7px;
    padding: 4px 8px;
    font-size: 11px;
    font-weight: 800;
}
QLabel#statusLive {
    color: #8df0cb;
    background: #123c32;
    border-radius: 7px;
    padding: 4px 8px;
    font-size: 11px;
    font-weight: 800;
}
QLabel#statusCompleted {
    color: #8895a8;
    background: #151b27;
    border-radius: 7px;
    padding: 4px 8px;
    font-size: 11px;
    font-weight: 700;
}
QLabel#savedBadge {
    color: #9fb0ff;
    background: #151f39;
    border-radius: 7px;
    padding: 4px 7px;
    font-size: 11px;
}
QScrollArea { border: none; }
QSizeGrip { background: transparent; width: 16px; height: 16px; }
"""


class FetchWorker(QObject):
    finished = Signal(list)
    failed = Signal(str)

    def __init__(self, username: str, password: str, mode: str):
        super().__init__()
        self.username = username
        self.password = password
        self.mode = mode

    def run(self):
        try:
            exams = fetch_exam_routine(self.username, self.password, self.mode)
            self.finished.emit(exams)
        except Exception as exc:
            self.failed.emit(str(exc))


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    r, g, b = [max(0, min(255, int(v))) for v in rgb]
    return f"#{r:02x}{g:02x}{b:02x}"


def _mix(color_a: str, color_b: str, ratio: float) -> str:
    ratio = max(0.0, min(1.0, ratio))
    ar, ag, ab = _hex_to_rgb(color_a)
    br, bg, bb = _hex_to_rgb(color_b)
    return _rgb_to_hex((
        round(ar + (br - ar) * ratio),
        round(ag + (bg - ag) * ratio),
        round(ab + (bb - ab) * ratio),
    ))


def _brighten(color: str, amount: float) -> str:
    return _mix(color, "#ffffff", amount)


def _darken(color: str, amount: float) -> str:
    return _mix(color, "#000000", amount)


def urgency_theme(exam: Exam, now: Optional[datetime] = None) -> dict[str, str]:
    """Neutral modern surfaces with urgency only in accents.

    Far exams stay cool/clean. The accent becomes warmer and brighter as the
    exam approaches, avoiding full-card pink/purple washes.
    """
    now = now or datetime.now()
    start = exam.start_datetime()
    _, state = exam_state(exam, now)

    if state == "completed":
        accent = "#64748b"
        status = "#94a3b8"
    elif state == "live":
        accent = "#ff334d"
        status = "#ff667a"
    elif start is None:
        accent = "#4f7cff"
        status = "#7ea2ff"
    else:
        seconds_until = max(0.0, (start - now).total_seconds())

        # Deliberately avoid blue->red interpolation, which passes through purple.
        if seconds_until > 7 * 86400:
            accent, status = "#3b82f6", "#7db0ff"
        elif seconds_until > 3 * 86400:
            accent, status = "#4f8cff", "#8bb7ff"
        elif seconds_until > 24 * 3600:
            accent, status = "#f59e0b", "#fbbf24"
        elif seconds_until > 6 * 3600:
            accent, status = "#f97316", "#fb923c"
        elif seconds_until > 60 * 60:
            accent, status = "#ef4444", "#ff6262"
        else:
            accent, status = "#ff2d2d", "#ff6b6b"

    return {
        "accent": accent,
        "accent_soft": _mix("#101722", accent, 0.16),
        "accent_softer": _mix("#0f1622", accent, 0.08),
        "status_fg": status,
        "card_bg": "#111722",
        "card_bg_alt": "#0f151f",
        "card_border": "#253043",
        "panel_bg": "#0d131d",
        "panel_border": "#202b3b",
        "room_bg": "#0d131d",
        "text": "#f8fafc",
        "subtext": "#aab6c8",
        "muted": "#7f8ca3",
        "section_bg": "#151d2a",
        "section_border": "#2a3649",
        "section_fg": "#9eabc0",
    }


def routine_card_styles(main_selector: str, theme: dict[str, str]) -> str:
    return f"""
{main_selector} {{
    background: {theme['card_bg']};
    border: 1px solid {theme['card_border']};
    border-radius: 18px;
}}
QFrame#datePanel, QFrame#timePanel {{
    background: {theme['panel_bg']};
    border: 1px solid {theme['panel_border']};
    border-radius: 12px;
}}
QFrame#roomPanel {{
    background: {theme['room_bg']};
    border: 1px solid {theme['accent']};
    border-radius: 12px;
}}
QLabel#courseCode {{
    color: {theme['text']};
    background: transparent;
}}
QLabel#courseName {{
    color: {theme['subtext']};
    background: transparent;
}}
QLabel#roomLabel {{
    color: {theme['status_fg']};
    background: transparent;
}}
QLabel#roomValue {{
    color: {theme['text']};
    background: transparent;
}}
QLabel#metricCaption, QLabel#dateMonth, QLabel#weekday {{
    color: {theme['muted']};
    background: transparent;
}}
QLabel#dateDay, QLabel#timeValue, QLabel#timeSecondary {{
    color: {theme['text']};
    background: transparent;
}}
QLabel#sectionBadge {{
    background: {theme['section_bg']};
    color: {theme['section_fg']};
    border: 1px solid {theme['section_border']};
    border-radius: 7px;
    padding: 3px 7px;
}}
QLabel#statusUpcoming, QLabel#statusLive {{
    color: {theme['status_fg']};
    background: {theme['accent_soft']};
    border: 1px solid {theme['accent']};
    border-radius: 8px;
    padding: 4px 8px;
    font-size: 11px;
    font-weight: 800;
}}
QLabel#statusCompleted {{
    color: #8b98ac;
    background: #151b25;
    border: 1px solid #263141;
    border-radius: 8px;
    padding: 4px 8px;
    font-size: 11px;
    font-weight: 700;
}}
"""



def _duration_text(seconds: float, suffix: str = "") -> str:
    seconds = max(0, int(seconds))
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes = rem // 60

    if days:
        text = f"{days}d {hours}h {minutes}m"
    elif hours:
        text = f"{hours}h {minutes}m"
    elif minutes:
        text = f"{minutes}m"
    else:
        text = "<1m"
    return f"{text}{suffix}"


def exam_state(exam: Exam, now: Optional[datetime] = None) -> Tuple[str, str]:
    """Return (human text, state) using the full start/end interval."""
    now = now or datetime.now()
    start = exam.start_datetime()
    end = exam.end_datetime()

    if start is None:
        return "Time unavailable", "completed"

    if now < start:
        return f"Starts in {_duration_text((start - now).total_seconds())}", "upcoming"

    if end is not None:
        if now <= end:
            return f"IN PROGRESS · {_duration_text((end - now).total_seconds(), ' left')}", "live"
        elapsed = (now - end).total_seconds()
        if elapsed < 12 * 3600:
            return f"Ended {_duration_text(elapsed)} ago", "completed"
        return "Completed", "completed"

    # Fallback when ExamCon supplies only a start time.
    elapsed = (now - start).total_seconds()
    if elapsed <= 4 * 3600:
        return f"Started {_duration_text(elapsed)} ago", "live"
    return "Completed", "completed"


def choose_next_exam_index(exams: List[Exam], now: Optional[datetime] = None) -> Optional[int]:
    now = now or datetime.now()

    # An exam currently in progress takes priority.
    live = []
    upcoming = []
    for idx, exam in enumerate(exams):
        start = exam.start_datetime()
        end = exam.end_datetime()
        if start is None:
            continue
        if start <= now and (end is None or now <= end):
            live.append((start, idx))
        elif start > now:
            upcoming.append((start, idx))

    if live:
        return min(live)[1]
    if upcoming:
        return min(upcoming)[1]
    return None


def sorted_exams(exams: List[Exam], now: Optional[datetime] = None) -> List[Exam]:
    now = now or datetime.now()
    decorated = []
    for original_index, exam in enumerate(exams):
        start = exam.start_datetime()
        end = exam.end_datetime()
        if start is None:
            key = (3, datetime.max, original_index)
        elif start <= now and (end is None or now <= end):
            key = (0, start, original_index)
        elif start > now:
            key = (1, start, original_index)
        else:
            key = (2, start, original_index)
        decorated.append((key, exam))
    return [exam for _, exam in sorted(decorated, key=lambda x: x[0])]


def date_parts(exam: Exam):
    dt = exam.start_datetime()
    if dt:
        return dt.strftime("%d"), dt.strftime("%b").upper(), dt.strftime("%A")

    raw = exam.date or "—"
    m = re.search(r"\b(\d{1,2})[-/ ]([A-Za-z]{3,9})", raw)
    if m:
        return m.group(1).zfill(2), m.group(2)[:3].upper(), exam.day or ""
    return raw, "", exam.day or ""


def clean_single_time(hour: str, minute: str, meridiem: str) -> str:
    h = str(int(hour)) if hour.isdigit() else hour
    suffix = f" {meridiem.upper()}" if meridiem else ""
    return f"{h}:{minute}{suffix}"


def split_time_display(value: str) -> Tuple[str, str]:
    text = re.sub(r"\s+", " ", value or "—").strip().upper().replace(".", "")
    matches = re.findall(r"\b(\d{1,2}):(\d{2})\s*(AM|PM)?\b", text, re.I)
    if not matches:
        return text, ""
    first = clean_single_time(*matches[0])
    second = clean_single_time(*matches[1]) if len(matches) > 1 else ""
    return first, second


def clean_time(value: str) -> str:
    start, end = split_time_display(value)
    return f"{start} – {end}" if end else start


class LiveStatusLabel(QLabel):
    def __init__(self, exam: Exam):
        super().__init__()
        self.exam = exam
        self.refresh()

    def refresh(self, now: Optional[datetime] = None):
        text, state = exam_state(self.exam, now)
        object_name = {
            "upcoming": "statusUpcoming",
            "live": "statusLive",
            "completed": "statusCompleted",
        }[state]
        if self.objectName() != object_name:
            self.setObjectName(object_name)
            self.style().unpolish(self)
            self.style().polish(self)
        self.setText(text)


class DatePanel(QFrame):
    def __init__(self, exam: Exam, compact: bool = False):
        super().__init__()
        self.setObjectName("datePanel")
        self.setFixedSize(82 if compact else 90, 90 if compact else 98)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 7, 8, 7)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        day, month, weekday = date_parts(exam)
        day_label = QLabel(day)
        day_label.setObjectName("dateDay")
        day_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(day_label)

        if month:
            month_label = QLabel(month)
            month_label.setObjectName("dateMonth")
            month_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(month_label)

        if weekday:
            week = QLabel(weekday)
            week.setObjectName("weekday")
            week.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(week)


class TimePanel(QFrame):
    def __init__(self, exam: Exam, compact: bool = False):
        super().__init__()
        self.setObjectName("timePanel")
        self.setMinimumWidth(142 if compact else 170)
        self.setFixedHeight(90 if compact else 98)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 9, 12, 9)
        layout.setSpacing(2)

        caption = QLabel("TIME")
        caption.setObjectName("metricCaption")
        layout.addWidget(caption)

        start, end = split_time_display(exam.time)
        start_label = QLabel(start)
        start_label.setObjectName("timeValue")
        start_label.setWordWrap(False)
        layout.addWidget(start_label)

        if end:
            end_label = QLabel(f"to {end}")
            end_label.setObjectName("timeSecondary")
            end_label.setWordWrap(False)
            layout.addWidget(end_label)

        layout.addStretch(1)


class RoomPanel(QFrame):
    def __init__(self, room: str, compact: bool = False):
        super().__init__()
        self.setObjectName("roomPanel")
        self.setFixedSize(102 if compact else 118, 90 if compact else 98)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(1)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        label = QLabel("YOUR ROOM")
        label.setObjectName("roomLabel")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)

        value = QLabel(room or "—")
        value.setObjectName("roomValue")
        value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        value.setWordWrap(False)
        layout.addWidget(value)


class RoutineCard(QFrame):
    def __init__(self, exam: Exam, student_id: str, mode: str, is_next: bool = False):
        super().__init__()
        self.exam = exam
        self.is_next = is_next
        self._last_theme_key = None
        _, state = exam_state(exam)
        if state == "live":
            self.setObjectName("liveRoutineCard")
        elif is_next:
            self.setObjectName("nextRoutineCard")
        else:
            self.setObjectName("routineCard")
        self.setMinimumHeight(134)

        room = exam.assigned_room(student_id) if mode == "student" else exam.room

        root = QHBoxLayout(self)
        root.setContentsMargins(10, 14, 16, 14)
        root.setSpacing(12)

        self.urgency_bar = QFrame()
        self.urgency_bar.setFixedWidth(4)
        self.urgency_bar.setMinimumHeight(92)
        root.addWidget(self.urgency_bar, 0, Qt.AlignmentFlag.AlignVCenter)

        root.addWidget(DatePanel(exam), 0, Qt.AlignmentFlag.AlignVCenter)

        middle = QVBoxLayout()
        middle.setSpacing(5)

        top = QHBoxLayout()
        top.setSpacing(8)
        code = QLabel(exam.course_code)
        code.setObjectName("courseCode")
        top.addWidget(code)

        if exam.section:
            section = QLabel(f"SECTION {exam.section}")
            section.setObjectName("sectionBadge")
            top.addWidget(section)

        self.state_badge = QLabel("")
        self.state_badge.hide()
        top.addWidget(self.state_badge)

        top.addStretch(1)
        middle.addLayout(top)

        if exam.course_name:
            name = QLabel(exam.course_name)
            name.setObjectName("courseName")
            name.setWordWrap(True)
            name.setMaximumHeight(38)
            middle.addWidget(name)

        info_line = QHBoxLayout()
        time_value = QLabel(clean_time(exam.time))
        time_value.setObjectName("timeValue")
        time_value.setWordWrap(False)
        info_line.addWidget(time_value)

        self.status_label = LiveStatusLabel(exam)
        info_line.addWidget(self.status_label)
        info_line.addStretch(1)
        middle.addLayout(info_line)
        middle.addStretch(1)

        root.addLayout(middle, 1)
        root.addWidget(RoomPanel(room), 0, Qt.AlignmentFlag.AlignVCenter)
        self.refresh_time(datetime.now(), is_next)

    def apply_visual_theme(self, now: Optional[datetime] = None):
        now = now or datetime.now()
        theme = urgency_theme(self.exam, now)
        theme_key = (self.objectName(), tuple(sorted(theme.items())))
        if theme_key == self._last_theme_key:
            return
        self.setStyleSheet(routine_card_styles(f"QFrame#{self.objectName()}", theme))
        self.urgency_bar.setStyleSheet(
            f"background: {theme['accent']}; border: none; border-radius: 2px;"
        )
        self._last_theme_key = theme_key

    def refresh_time(self, now: Optional[datetime] = None, is_next: Optional[bool] = None):
        now = now or datetime.now()
        if is_next is not None:
            self.is_next = is_next
        self.status_label.refresh(now)
        _, state = exam_state(self.exam, now)

        if state == "live":
            self.setObjectName("liveRoutineCard")
            self.state_badge.setText("LIVE")
            self.state_badge.setObjectName("liveBadge")
            self.state_badge.show()
        elif self.is_next:
            self.setObjectName("nextRoutineCard")
            self.state_badge.setText("NEXT EXAM")
            self.state_badge.setObjectName("nextBadge")
            self.state_badge.show()
        else:
            self.setObjectName("routineCard")
            self.state_badge.hide()

        self.apply_visual_theme(now)
        self.style().unpolish(self)
        self.style().polish(self)
        self.state_badge.style().unpolish(self.state_badge)
        self.state_badge.style().polish(self.state_badge)


class DragHeader(QFrame):
    def __init__(self, owner: "StickyExamWindow"):
        super().__init__()
        self.owner = owner
        self._fallback_offset = QPoint()
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setStyleSheet("background: transparent; border: none;")

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            self._fallback_offset = event.globalPosition().toPoint() - self.owner.frameGeometry().topLeft()
            handle = self.owner.windowHandle()
            if handle is not None:
                try:
                    if handle.startSystemMove():
                        event.accept()
                        return
                except Exception:
                    pass
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() & Qt.MouseButton.LeftButton:
            self.owner.move(event.globalPosition().toPoint() - self._fallback_offset)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        super().mouseReleaseEvent(event)


class ResizeCorner(QFrame):
    def __init__(self, owner: "StickyExamWindow"):
        super().__init__()
        self.owner = owner
        self.setFixedSize(28, 28)
        self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        self.setToolTip("Drag to resize")
        self.setStyleSheet("background: transparent; border: none;")

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            handle = self.owner.windowHandle()
            if handle is not None:
                try:
                    if handle.startSystemResize(Qt.Edge.RightEdge | Qt.Edge.BottomEdge):
                        event.accept()
                        return
                except Exception:
                    pass
        super().mousePressEvent(event)


class StickyExamWindow(QWidget):
    def __init__(self, exam: Exam, student_id: str, mode: str, index: int = 0, is_next: bool = False):
        super().__init__()
        self.exam = exam
        self.is_next = is_next
        self._last_theme_key = None
        self.tile_key = re.sub(r"[^A-Za-z0-9_.-]+", "_", f"{exam.course_code}_{exam.date}_{exam.time}")
        self.settings = QSettings("UIU", "UIU Exam Widget")

        room = exam.assigned_room(student_id) if mode == "student" else exam.room
        _, state = exam_state(exam)

        self.setWindowTitle(exam.course_code)
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Below this size the three metric blocks cannot remain readable. Prevent
        # the compositor from squeezing them until text overlaps or wraps randomly.
        self.setMinimumSize(430, 225)
        self.resize(470, 240)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(7, 7, 7, 7)

        self.card = QFrame()
        self.card.setObjectName("stickyCard")
        outer.addWidget(self.card)

        root = QVBoxLayout(self.card)
        root.setContentsMargins(13, 10, 13, 10)
        root.setSpacing(9)

        self.urgency_bar = QFrame()
        self.urgency_bar.setFixedHeight(4)
        root.addWidget(self.urgency_bar)

        drag = DragHeader(self)
        drag_layout = QHBoxLayout(drag)
        drag_layout.setContentsMargins(0, 0, 0, 0)
        drag_layout.setSpacing(7)

        title_col = QVBoxLayout()
        title_col.setSpacing(1)
        code = QLabel(exam.course_code)
        code.setObjectName("courseCode")
        code.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        title_col.addWidget(code)

        if exam.course_name:
            name = QLabel(exam.course_name)
            name.setObjectName("courseName")
            name.setWordWrap(True)
            name.setMaximumHeight(36)
            name.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            title_col.addWidget(name)
        drag_layout.addLayout(title_col, 1)

        self.state_badge = QLabel("")
        self.state_badge.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.state_badge.hide()
        drag_layout.addWidget(self.state_badge, 0, Qt.AlignmentFlag.AlignTop)

        close = QPushButton("×")
        close.setObjectName("closeTileButton")
        close.setFixedSize(30, 28)
        close.setToolTip("Close tile")
        close.clicked.connect(self.close)
        drag_layout.addWidget(close, 0, Qt.AlignmentFlag.AlignTop)
        root.addWidget(drag)

        # Stable metric row: fixed Date/Room panels and a flexible Time panel.
        # Font sizes do not scale with the window, so resizing never distorts them.
        metrics = QHBoxLayout()
        metrics.setSpacing(9)
        metrics.addWidget(DatePanel(exam, compact=True), 0)
        metrics.addWidget(TimePanel(exam, compact=True), 1)
        metrics.addWidget(RoomPanel(room, compact=True), 0)
        root.addLayout(metrics)

        footer = QHBoxLayout()
        footer.setSpacing(8)
        if exam.section:
            section = QLabel(f"SECTION {exam.section}")
            section.setObjectName("sectionBadge")
            footer.addWidget(section)

        self.status_label = LiveStatusLabel(exam)
        footer.addWidget(self.status_label)
        footer.addStretch(1)

        resize_wrap = ResizeCorner(self)
        resize_layout = QVBoxLayout(resize_wrap)
        resize_layout.setContentsMargins(4, 4, 0, 0)
        hint = QLabel("↘")
        hint.setObjectName("muted")
        hint.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        resize_layout.addWidget(hint)
        footer.addWidget(resize_wrap, 0, Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight)
        footer.addWidget(QSizeGrip(self))
        root.addLayout(footer)

        saved_geometry = self.settings.value(f"tileGeometry/{self.tile_key}")
        restored = False
        if saved_geometry is not None:
            try:
                restored = self.restoreGeometry(saved_geometry)
            except Exception:
                restored = False

        if not restored:
            screen = QApplication.primaryScreen().availableGeometry()
            columns = max(1, min(3, screen.width() // 490))
            col = index % columns
            row = index // columns
            self.move(screen.x() + 30 + col * 485, screen.y() + 50 + row * 255)

        # Old saved geometries from MVP 1.3 may be smaller than the new safe size.
        if self.width() < self.minimumWidth() or self.height() < self.minimumHeight():
            self.resize(max(self.width(), self.minimumWidth()), max(self.height(), self.minimumHeight()))

        self.refresh_time(datetime.now(), is_next)

    def apply_visual_theme(self, now: Optional[datetime] = None):
        now = now or datetime.now()
        theme = urgency_theme(self.exam, now)
        card_name = self.card.objectName()
        theme_key = (card_name, tuple(sorted(theme.items())))
        if theme_key == self._last_theme_key:
            return

        # Apply the QSS to the actual card, not the frameless top-level window.
        # The previous build generated `QFrame# { ... }` because the top-level
        # StickyExamWindow has no objectName, which is invalid Qt stylesheet syntax.
        self.card.setStyleSheet(routine_card_styles(f"QFrame#{card_name}", theme))
        self.urgency_bar.setStyleSheet(
            f"background: {theme['accent']}; border: none; border-radius: 2px;"
        )
        self._last_theme_key = theme_key

    def refresh_time(self, now: Optional[datetime] = None, is_next: Optional[bool] = None):
        now = now or datetime.now()
        if is_next is not None:
            self.is_next = is_next
        self.status_label.refresh(now)
        _, state = exam_state(self.exam, now)

        if state == "live":
            self.card.setObjectName("stickyLive")
            self.state_badge.setText("LIVE")
            self.state_badge.setObjectName("liveBadge")
            self.state_badge.show()
        elif self.is_next:
            self.card.setObjectName("stickyFeatured")
            self.state_badge.setText("NEXT")
            self.state_badge.setObjectName("nextBadge")
            self.state_badge.show()
        else:
            self.card.setObjectName("stickyCard")
            self.state_badge.hide()

        self.apply_visual_theme(now)
        self.card.style().unpolish(self.card)
        self.card.style().polish(self.card)
        self.state_badge.style().unpolish(self.state_badge)
        self.state_badge.style().polish(self.state_badge)

    def closeEvent(self, event: QCloseEvent):
        self.settings.setValue(f"tileGeometry/{self.tile_key}", self.saveGeometry())
        super().closeEvent(event)


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("appWindow")
        self.setWindowTitle("UIU Exam Widget")
        self.resize(940, 710)
        self.setMinimumSize(760, 540)

        self.exams: List[Exam] = []
        self.routine_cards: List[RoutineCard] = []
        self.sticky_windows: List[StickyExamWindow] = []
        self.worker_thread = None
        self.worker = None
        self.cached_fetched_at = ""

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(13)

        heading = QHBoxLayout()
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title = QLabel("Exam Routine")
        title.setObjectName("pageTitle")
        title_col.addWidget(title)
        subtitle = QLabel("Course, time and room — urgency is shown with subtle color accents.")
        subtitle.setObjectName("pageSubtitle")
        title_col.addWidget(subtitle)
        heading.addLayout(title_col)
        heading.addStretch(1)

        clock_col = QVBoxLayout()
        clock_col.setSpacing(3)
        self.clock_label = QLabel("")
        self.clock_label.setObjectName("clock")
        self.clock_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        clock_col.addWidget(self.clock_label)
        self.saved_badge = QLabel("")
        self.saved_badge.setObjectName("savedBadge")
        self.saved_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.saved_badge.hide()
        clock_col.addWidget(self.saved_badge, 0, Qt.AlignmentFlag.AlignRight)
        heading.addLayout(clock_col)
        root.addLayout(heading)

        toolbar = QFrame()
        toolbar.setObjectName("toolbar")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(12, 10, 12, 10)
        toolbar_layout.setSpacing(10)

        self.login_type = QComboBox()
        self.login_type.addItem("Student", "student")
        self.login_type.addItem("Faculty", "faculty")
        self.login_type.setMinimumWidth(120)
        self.login_type.currentIndexChanged.connect(self.login_type_changed)
        toolbar_layout.addWidget(self.login_type)

        self.username = QLineEdit()
        self.username.setPlaceholderText("Student ID")
        toolbar_layout.addWidget(self.username, 1)

        self.password = QLineEdit()
        self.password.setPlaceholderText("UCAM Password")
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        toolbar_layout.addWidget(self.password, 1)

        self.fetch_btn = QPushButton("Refresh Routine")
        self.fetch_btn.clicked.connect(self.fetch_routine)
        toolbar_layout.addWidget(self.fetch_btn)
        root.addWidget(toolbar)

        action_row = QHBoxLayout()
        self.status = QLabel("Fetch once and your routine stays saved locally.")
        self.status.setObjectName("muted")
        self.status.setWordWrap(True)
        action_row.addWidget(self.status, 1)

        self.sticky_btn = QPushButton("Show Desktop Tiles")
        self.sticky_btn.setEnabled(False)
        self.sticky_btn.clicked.connect(self.show_sticky_tiles)
        action_row.addWidget(self.sticky_btn)

        self.hide_sticky_btn = QPushButton("Hide Tiles")
        self.hide_sticky_btn.setObjectName("secondaryButton")
        self.hide_sticky_btn.setEnabled(False)
        self.hide_sticky_btn.clicked.connect(self.hide_sticky_tiles)
        action_row.addWidget(self.hide_sticky_btn)

        self.clear_btn = QPushButton("Clear Saved Routine")
        self.clear_btn.setObjectName("dangerButton")
        self.clear_btn.clicked.connect(self.clear_saved_routine)
        action_row.addWidget(self.clear_btn)
        root.addLayout(action_row)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.viewport().setStyleSheet("background: #0b0f19; border: none;")

        self.results_widget = QWidget()
        self.results_widget.setObjectName("resultsWidget")
        self.results_layout = QVBoxLayout(self.results_widget)
        self.results_layout.setContentsMargins(0, 5, 0, 5)
        self.results_layout.setSpacing(12)
        self.results_layout.addStretch()

        self.scroll.setWidget(self.results_widget)
        root.addWidget(self.scroll, 1)

        self.restore_cached_routine()

        self.clock_timer = QTimer(self)
        self.clock_timer.setInterval(30_000)
        self.clock_timer.timeout.connect(self.update_clock_and_statuses)
        self.clock_timer.start()
        self.update_clock_and_statuses()

    def selected_mode(self) -> str:
        return self.login_type.currentData()

    def login_type_changed(self):
        mode = self.selected_mode()
        if mode == "student":
            self.username.setPlaceholderText("Student ID")
            self.fetch_btn.setText("Refresh Routine")
        else:
            self.username.setPlaceholderText("UCAM Username")
            self.fetch_btn.setText("Faculty Login / Refresh")

    def clear_results(self):
        self.routine_cards.clear()
        while self.results_layout.count():
            item = self.results_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def restore_cached_routine(self):
        cached = load_routine()
        if not cached:
            return
        mode, username, fetched_at, exams = cached
        index = self.login_type.findData(mode)
        if index >= 0:
            self.login_type.setCurrentIndex(index)
        self.username.setText(username)
        self.cached_fetched_at = fetched_at
        self.exams = sorted_exams(exams)
        self.render_routine(saved=True)

    def render_routine(self, saved: bool = False):
        self.clear_results()
        now = datetime.now()
        self.exams = sorted_exams(self.exams, now)
        next_index = choose_next_exam_index(self.exams, now)
        mode = self.selected_mode()
        username = self.username.text().strip()

        for index, exam in enumerate(self.exams):
            card = RoutineCard(exam, username, mode, is_next=(index == next_index))
            self.routine_cards.append(card)
            self.results_layout.addWidget(card)
        self.results_layout.addStretch(1)

        self.sticky_btn.setEnabled(bool(self.exams))
        if self.exams:
            self.saved_badge.setText("SAVED LOCALLY")
            self.saved_badge.show()
            prefix = "Loaded saved routine" if saved else "Routine updated and saved"
            self.status.setText(f"{prefix}. {len(self.exams)} exam(s). Password is never stored.")
        else:
            self.saved_badge.hide()

    def update_clock_and_statuses(self):
        now = datetime.now()
        self.clock_label.setText(now.strftime("Local time · %a, %d %b · %I:%M %p").replace(" 0", " "))
        next_index = choose_next_exam_index(self.exams, now)
        next_exam = self.exams[next_index] if next_index is not None else None

        for index, card in enumerate(self.routine_cards):
            card.refresh_time(now, is_next=(index == next_index))
        for tile in list(self.sticky_windows):
            if tile.isVisible():
                tile.refresh_time(now, is_next=(tile.exam is next_exam))

    def fetch_routine(self):
        username = self.username.text().strip()
        pwd = self.password.text()
        mode = self.selected_mode()

        if not username or not pwd:
            label = "Student ID" if mode == "student" else "UCAM username"
            QMessageBox.warning(self, "Missing information", f"Enter your {label} and UCAM password.")
            return

        self.fetch_btn.setEnabled(False)
        self.status.setText(f"Connecting to ExamCon {mode.title()}…")

        self.worker_thread = QThread()
        self.worker = FetchWorker(username, pwd, mode)
        self.worker.moveToThread(self.worker_thread)

        self.worker_thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.fetch_success)
        self.worker.failed.connect(self.fetch_failed)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.failed.connect(self.worker_thread.quit)
        self.worker_thread.finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        self.worker_thread.start()

    def fetch_success(self, exams):
        self.exams = sorted_exams(exams)
        save_routine(self.selected_mode(), self.username.text().strip(), self.exams)
        self.password.clear()
        self.fetch_btn.setEnabled(True)
        self.render_routine(saved=False)

    def fetch_failed(self, message):
        self.fetch_btn.setEnabled(True)
        if self.exams:
            self.status.setText("Refresh failed; your previously saved routine is still available.")
        else:
            self.status.setText("Could not load the exam data.")
        QMessageBox.critical(self, "ExamCon error", message)

    def clear_saved_routine(self):
        if not self.exams and load_routine() is None:
            return
        answer = QMessageBox.question(
            self,
            "Clear saved routine?",
            "This removes the locally cached routine. It does not change anything on ExamCon.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.hide_sticky_tiles()
        clear_routine()
        self.exams = []
        self.clear_results()
        self.results_layout.addStretch(1)
        self.sticky_btn.setEnabled(False)
        self.saved_badge.hide()
        self.status.setText("Saved routine cleared. Fetch again whenever you want.")

    def show_sticky_tiles(self):
        self.hide_sticky_tiles()
        now = datetime.now()
        next_index = choose_next_exam_index(self.exams, now)
        username = self.username.text().strip()
        mode = self.selected_mode()

        for index, exam in enumerate(self.exams):
            tile = StickyExamWindow(exam, username, mode, index, is_next=(index == next_index))
            tile.show()
            self.sticky_windows.append(tile)

        self.hide_sticky_btn.setEnabled(bool(self.sticky_windows))
        self.status.setText("Tiles are movable/resizable. Urgency is shown with clean accent colors, not full-card tints.")
        self.update_clock_and_statuses()

    def hide_sticky_tiles(self):
        for window in self.sticky_windows:
            window.close()
        self.sticky_windows.clear()
        self.hide_sticky_btn.setEnabled(False)


INSTANCE_SERVER_NAME = "uiu-exam-widget-single-instance"


def _activate_macos_app() -> None:
    """Ask macOS to bring the GUI to the foreground when opened from the menu bar."""
    if sys.platform != "darwin":
        return
    try:
        from AppKit import NSApplication
        NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
    except Exception:
        pass


def _notify_existing_instance() -> bool:
    """Return True if another instance exists and was asked to show itself."""
    socket = QLocalSocket()
    socket.connectToServer(INSTANCE_SERVER_NAME)
    if socket.waitForConnected(250):
        socket.write(b"show\n")
        socket.flush()
        socket.waitForBytesWritten(250)
        socket.disconnectFromServer()
        return True
    return False


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("UIU Exam Widget")
    app.setStyleSheet(APP_QSS)

    # A panel click may launch the command repeatedly. If the GUI is already open,
    # tell the existing instance to raise itself instead of creating duplicates.
    if _notify_existing_instance():
        return

    QLocalServer.removeServer(INSTANCE_SERVER_NAME)
    instance_server = QLocalServer(app)
    if not instance_server.listen(INSTANCE_SERVER_NAME):
        # Rare stale-socket fallback. Continue normally rather than blocking the app.
        QLocalServer.removeServer(INSTANCE_SERVER_NAME)
        instance_server.listen(INSTANCE_SERVER_NAME)

    window = MainWindow()

    def raise_window():
        while instance_server.hasPendingConnections():
            client = instance_server.nextPendingConnection()
            if client is not None:
                client.disconnectFromServer()
        window.showNormal()
        window.show()
        window.raise_()
        window.activateWindow()
        _activate_macos_app()

    instance_server.newConnection.connect(raise_window)
    window.show()
    _activate_macos_app()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
