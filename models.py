from dataclasses import dataclass, field
from datetime import datetime, timedelta
import re
from typing import Dict, List, Optional, Tuple


@dataclass
class Exam:
    fields: Dict[str, str] = field(default_factory=dict)

    def _clean_value(self, value) -> str:
        return re.sub(r"\s+", " ", str(value or "")).strip()

    def find_exactish(self, *keywords: str, default: str = "—") -> str:
        normalized = [(str(k).strip().lower(), self._clean_value(v)) for k, v in self.fields.items()]
        keys = [k.lower() for k in keywords]

        for wanted in keys:
            for key, value in normalized:
                if key == wanted and value:
                    return value

        for wanted in keys:
            for key, value in normalized:
                if key.startswith(wanted) and value:
                    return value

        for wanted in keys:
            for key, value in normalized:
                if wanted in key and value:
                    return value

        return default

    def find(self, *keywords: str, default: str = "—") -> str:
        return self.find_exactish(*keywords, default=default)

    @property
    def course_code(self) -> str:
        value = self.find_exactish(
            "course code", "subject code", "course", "subject", "code", default=""
        )
        if value:
            match = re.search(r"\b[A-Z]{2,8}\s*[- ]?\s*\d{3,5}[A-Z]?\b", value, re.I)
            if match:
                return re.sub(r"\s+", " ", match.group(0)).upper()

        all_text = " ".join(self._clean_value(v) for v in self.fields.values())
        match = re.search(r"\b[A-Z]{2,8}\s*[- ]?\s*\d{3,5}[A-Z]?\b", all_text, re.I)
        if match:
            return re.sub(r"\s+", " ", match.group(0)).upper()

        return value or "EXAM"

    @property
    def course_name(self) -> str:
        name = self.find_exactish(
            "course title", "course name", "subject title", "subject name", "title", default=""
        )
        if name and name.lower() != self.course_code.lower():
            return name

        course_value = self.find_exactish("course", "subject", default="")
        if course_value and course_value.lower() != self.course_code.lower():
            stripped = re.sub(re.escape(self.course_code), "", course_value, flags=re.I).strip(" -:()")
            if stripped:
                return stripped
        return ""

    @property
    def course(self) -> str:
        return self.course_code

    @property
    def date(self) -> str:
        return self.find_exactish("exam date", "date")

    @property
    def day(self) -> str:
        return self.find_exactish("day", "exam day", default="")

    @property
    def time(self) -> str:
        return self.find_exactish("exam time", "time", "slot")

    @property
    def room(self) -> str:
        return self.find_exactish("room no", "room", "venue", "seat room", "exam room")

    @property
    def section(self) -> str:
        return self.find_exactish("section", "sec", default="")

    @property
    def teacher(self) -> str:
        return self.find_exactish("faculty", "teacher", "instructor", default="")

    def room_ranges(self) -> List[Tuple[str, int, int]]:
        text = self._clean_value(self.room)
        if not text or text == "—":
            return []

        pattern = re.compile(
            r"(?P<room>[A-Za-z]?\d{2,4}[A-Za-z]?)\s*"
            r"\(\s*(?P<start>\d{6,15})\s*[-–—]\s*(?P<end>\d{6,15})\s*\)",
            re.I,
        )

        ranges: List[Tuple[str, int, int]] = []
        for match in pattern.finditer(text):
            try:
                start = int(match.group("start"))
                end = int(match.group("end"))
            except ValueError:
                continue
            if start > end:
                start, end = end, start
            ranges.append((match.group("room").upper(), start, end))
        return ranges

    def assigned_room(self, student_id: str = "") -> str:
        ranges = self.room_ranges()
        if not ranges:
            return self.room

        digits = re.sub(r"\D", "", student_id or "")
        if not digits:
            return "—"

        try:
            student_number = int(digits)
        except ValueError:
            return "—"

        for room, start, end in ranges:
            if start <= student_number <= end:
                return room

        return "—"

    def _parsed_date(self) -> Optional[datetime]:
        date_text = self.date.strip()
        if not date_text or date_text == "—":
            return None

        normalized_date = re.sub(r"\s+", " ", date_text.replace(".", " ")).strip()
        normalized_date = re.sub(r"(\d)(st|nd|rd|th)\b", r"\1", normalized_date, flags=re.I)

        date_formats = (
            "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d.%m.%Y",
            "%d-%b-%y", "%d-%B-%y", "%d/%b/%y", "%d/%B/%y",
            "%d %b %Y", "%d %B %Y", "%b %d %Y", "%B %d %Y",
            "%b %d, %Y", "%B %d, %Y", "%d %b %y", "%d %B %y",
        )
        for fmt in date_formats:
            try:
                return datetime.strptime(normalized_date, fmt)
            except ValueError:
                pass

        current_year = datetime.now().year
        for fmt in ("%d %b", "%d %B", "%b %d", "%B %d"):
            try:
                return datetime.strptime(normalized_date, fmt).replace(year=current_year)
            except ValueError:
                pass
        return None

    def _time_matches(self) -> List[Tuple[int, int, Optional[str]]]:
        text = self._clean_value(self.time).upper().replace(".", "")
        matches = re.findall(r"\b(\d{1,2}):(\d{2})\s*(AM|PM)?\b", text, re.I)
        result: List[Tuple[int, int, Optional[str]]] = []
        for hour_text, minute_text, meridiem in matches:
            try:
                hour = int(hour_text)
                minute = int(minute_text)
            except ValueError:
                continue
            result.append((hour, minute, meridiem.upper() if meridiem else None))
        return result

    @staticmethod
    def _to_24h(hour: int, minute: int, meridiem: Optional[str]) -> Optional[Tuple[int, int]]:
        if not (0 <= minute <= 59):
            return None
        if meridiem:
            if not (1 <= hour <= 12):
                return None
            if meridiem == "AM":
                hour = 0 if hour == 12 else hour
            else:
                hour = 12 if hour == 12 else hour + 12
        else:
            if not (0 <= hour <= 23):
                return None
        return hour, minute

    def start_datetime(self) -> Optional[datetime]:
        base = self._parsed_date()
        if base is None:
            return None

        times = self._time_matches()
        if not times:
            return base

        hour, minute, meridiem = times[0]
        converted = self._to_24h(hour, minute, meridiem)
        if converted is None:
            return base
        hour24, minute = converted
        return base.replace(hour=hour24, minute=minute, second=0, microsecond=0)

    def end_datetime(self) -> Optional[datetime]:
        start = self.start_datetime()
        if start is None:
            return None

        times = self._time_matches()
        if len(times) < 2:
            return None

        hour, minute, meridiem = times[1]
        converted = self._to_24h(hour, minute, meridiem)
        if converted is None:
            return None
        hour24, minute = converted
        end = start.replace(hour=hour24, minute=minute, second=0, microsecond=0)
        if end < start:
            end += timedelta(days=1)
        return end

    def sort_datetime(self) -> Optional[datetime]:
        return self.start_datetime()
