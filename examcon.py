from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Tuple

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

from models import Exam
from paths import APP_DIR


EXAMCON_URL = "https://examcon.uiu.ac.bd/"


class ExamConError(RuntimeError):
    pass


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _looks_like_exam_text(text: str) -> bool:
    low = text.lower()

    # Never accept the public homepage/login copy as an exam result.
    blocked = (
        "faculty login",
        "student exam routine search",
        "use your ucam username and password",
        "search your exam routine using your ucam",
        "looking for a countdown timer app",
        "reset login",
    )
    if any(x in low for x in blocked):
        return False

    date_like = bool(
        re.search(r"\b\d{1,2}[-/]\d{1,2}[-/](?:\d{2}|\d{4})\b", text)
        or re.search(
            r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2}(?:,\s*\d{4})?\b",
            low,
        )
        or re.search(
            r"\b\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*(?:\s+\d{4})?\b",
            low,
        )
    )
    time_like = bool(re.search(r"\b\d{1,2}:\d{2}\s*(?:am|pm)?\b", low))
    course_like = bool(re.search(r"\b[A-Z]{2,6}\s*[- ]?\s*\d{3,4}\b", text))
    room_like = bool(re.search(r"\b(?:room|venue|seat)\b\s*[:#-]?\s*[A-Za-z0-9][A-Za-z0-9 ._-]*", text, re.I))

    return sum((date_like, time_like, course_like, room_like)) >= 2


def _looks_like_exam_fields(fields: Dict[str, str]) -> bool:
    keys = " ".join(fields.keys()).lower()
    values = " ".join(str(v) for v in fields.values())

    key_score = sum(
        word in keys
        for word in ("course", "subject", "exam", "date", "time", "room", "venue", "slot", "seat")
    )

    return key_score >= 2 or _looks_like_exam_text(values)


def _extract_tables(html: str) -> List[Exam]:
    soup = BeautifulSoup(html, "html.parser")
    exams: List[Exam] = []

    for table in soup.find_all("table"):
        headers = [_clean(x.get_text(" ", strip=True)) for x in table.find_all("th")]

        for row in table.find_all("tr"):
            cells = [_clean(x.get_text(" ", strip=True)) for x in row.find_all("td")]
            if not cells:
                continue

            if headers and len(headers) == len(cells):
                fields = dict(zip(headers, cells))
            else:
                fields = {f"Column {i + 1}": value for i, value in enumerate(cells)}

            if any(fields.values()) and _looks_like_exam_fields(fields):
                exams.append(Exam(fields=fields))

    return exams


def _extract_card_like_blocks(html: str) -> List[Exam]:
    """Fallback for a routine rendered as cards rather than a table."""
    soup = BeautifulSoup(html, "html.parser")
    texts: List[str] = []

    for tag in soup.find_all(["div", "li", "article", "section"]):
        text = _clean(tag.get_text(" ", strip=True))
        if not (15 <= len(text) <= 650):
            continue
        if not _looks_like_exam_text(text):
            continue
        if text not in texts:
            texts.append(text)

    exams: List[Exam] = []
    for text in texts:
        fields: Dict[str, str] = {"Details": text}

        patterns = {
            "Date": r"(?:date)\s*[:\-]?\s*([^|,;]{3,45})",
            "Time": r"(?:time)\s*[:\-]?\s*([^|,;]{3,30})",
            "Room": r"(?:room|venue|seat)\s*[:#\-]?\s*([^|,;]{1,35})",
            "Course": r"(?:course|subject)\s*[:\-]?\s*([^|,;]{2,80})",
        }

        for key, pattern in patterns.items():
            m = re.search(pattern, text, flags=re.I)
            if m:
                fields[key] = _clean(m.group(1))

        # Useful fallback for a standalone course code such as CSE 3411.
        if "Course" not in fields:
            m = re.search(r"\b[A-Z]{2,6}\s*[- ]?\s*\d{3,4}\b", text)
            if m:
                fields["Course"] = _clean(m.group(0))

        exams.append(Exam(fields=fields))

    return exams


def _login_scope(page, mode: str):
    """
    Return the container belonging to the requested ExamCon login section.

    ExamCon exposes two separate credential areas on the same public page:
    Faculty Login and Student Exam Routine Search.  We deliberately scope every
    input/button lookup to only one of those containers.
    """
    heading_text = "Faculty Login" if mode == "faculty" else "Student Exam Routine Search"
    heading = page.get_by_text(heading_text, exact=True)

    if not heading.count():
        raise ExamConError(f'Could not find the "{heading_text}" section on ExamCon.')

    # Find the nearest ancestor that contains a password input. This avoids
    # accidentally crossing into the other login card.
    scope = heading.first.locator("xpath=ancestor::*[.//input[@type='password']][1]")
    if not scope.count():
        raise ExamConError(f'Could not identify the {mode} login container.')

    return scope


def _find_credentials_inputs(scope, mode: str):
    # First try semantic/name/id selectors.
    if mode == "student":
        user_candidates = scope.locator(
            'input[name*="student" i], input[id*="student" i], '
            'input[name*="user" i], input[id*="user" i], '
            'input:not([type]), input[type="text"], input[type="email"], input[type="number"]'
        )
    else:
        user_candidates = scope.locator(
            'input[name*="user" i], input[id*="user" i], '
            'input:not([type]), input[type="text"], input[type="email"], input[type="number"]'
        )

    password_candidates = scope.locator('input[type="password"]')

    if not user_candidates.count() or not password_candidates.count():
        raise ExamConError(f"Could not locate the {mode} username/password fields.")

    # In a correctly scoped card there should normally be one of each. Pick the
    # first visible candidate instead of using page-level .last/.first heuristics.
    username_box = None
    for i in range(user_candidates.count()):
        candidate = user_candidates.nth(i)
        if candidate.is_visible():
            username_box = candidate
            break

    password_box = None
    for i in range(password_candidates.count()):
        candidate = password_candidates.nth(i)
        if candidate.is_visible():
            password_box = candidate
            break

    if username_box is None or password_box is None:
        raise ExamConError(f"The {mode} login fields were found but are not visible.")

    return username_box, password_box


def _submit_scope(scope, password_box):
    submit = scope.locator('button[type="submit"], input[type="submit"], button')

    for i in range(submit.count()):
        candidate = submit.nth(i)
        if candidate.is_visible():
            candidate.click()
            return

    # Some forms have no explicit submit button.
    password_box.press("Enter")


def _safe_debug_html(html: str, username: str, password: str) -> str:
    # Keep diagnostics useful without intentionally persisting credentials.
    for secret in (username, password):
        if secret:
            html = html.replace(secret, "[REDACTED]")
    return html


def fetch_exam_routine(username: str, password: str, mode: str = "student") -> List[Exam]:
    username = username.strip()
    mode = mode.lower().strip()

    if mode not in {"student", "faculty"}:
        raise ExamConError("Login type must be Student or Faculty.")

    if not username or not password:
        raise ExamConError("Username/Student ID and password are required.")

    debug_path = APP_DIR
    debug_path.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 Chrome/126 Safari/537.36"
            ),
        )
        page = context.new_page()

        try:
            page.goto(EXAMCON_URL, wait_until="domcontentloaded", timeout=30000)
        except PlaywrightTimeoutError as exc:
            browser.close()
            raise ExamConError(
                "ExamCon did not load. Check your internet connection and try again."
            ) from exc

        scope = _login_scope(page, mode)
        username_box, password_box = _find_credentials_inputs(scope, mode)

        username_box.fill(username)
        password_box.fill(password)

        before_url = page.url
        before_body = _clean(page.locator("body").inner_text())

        _submit_scope(scope, password_box)

        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except PlaywrightTimeoutError:
            pass

        page.wait_for_timeout(1500)

        html = page.content()
        body_text = _clean(page.locator("body").inner_text())
        low = body_text.lower()

        auth_error_terms = (
            "invalid password",
            "wrong password",
            "incorrect password",
            "invalid username",
            "invalid student",
            "authentication failed",
            "login failed",
            "credentials do not match",
        )
        if any(term in low for term in auth_error_terms):
            browser.close()
            raise ExamConError(
                f"ExamCon rejected the {mode} username/Student ID or UCAM password."
            )

        # Only parse structured output. The homepage/login cards are explicitly
        # excluded by the validators above.
        exams = _extract_tables(html)
        if not exams:
            exams = _extract_card_like_blocks(html)

        if exams:
            browser.close()
            return exams

        safe_html = _safe_debug_html(html, username, password)
        (debug_path / f"last-result-{mode}.html").write_text(safe_html, encoding="utf-8")

        # Give a more useful error when submission appears to have done nothing.
        page_changed = page.url != before_url or body_text != before_body
        browser.close()

        if not page_changed:
            raise ExamConError(
                f"The {mode} form was submitted, but ExamCon did not show a new result. "
                "The form may have changed or the request may be blocked."
            )

        raise ExamConError(
            f"The {mode} login/result page changed, but no exam routine could be identified yet. "
            f"A redacted debug copy was saved to {debug_path / f'last-result-{mode}.html'}"
        )
