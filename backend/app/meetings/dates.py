from __future__ import annotations
import re
from datetime import date, timedelta

MONTHS = {"jan":1,"january":1,"feb":2,"february":2,"mar":3,"march":3,"apr":4,"april":4,"may":5,"jun":6,"june":6,"jul":7,"july":7,"aug":8,"august":8,"sep":9,"sept":9,"september":9,"oct":10,"october":10,"nov":11,"november":11,"dec":12,"december":12}

def resolve_due_date(raw: str | None, meeting_date: str) -> tuple[str | None, bool]:
    if not raw: return None, False
    base = date.fromisoformat(meeting_date)
    s = " ".join(raw.strip().lower().split())
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        try: return date.fromisoformat(s).isoformat(), False
        except ValueError: return None, False
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?", s)
    if m:
        day, month = int(m.group(1)), int(m.group(2)); year = int(m.group(3) or base.year)
        if year < 100: year += 2000
        try: return date(year, month, day).isoformat(), False
        except ValueError: return None, False
    m = re.search(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+([a-z]+)(?:\s+(\d{4}))?\b", s) or re.search(r"\b([a-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?(?:,?\s+(\d{4}))?\b", s)
    if m:
        # Support both day-first and month-first forms.
        if m.group(1).isdigit(): day, month_word, year_s = int(m.group(1)), m.group(2), m.group(3)
        else: month_word, day, year_s = m.group(1), int(m.group(2)), m.group(3)
        month = MONTHS.get(month_word.rstrip("."))
        if month:
            year = int(year_s or base.year)
            if not year_s and date(year, month, day) < base: year += 1
            try: return date(year, month, day).isoformat(), False
            except ValueError: return None, False
    if s == "today": return base.isoformat(), True
    if s == "tomorrow": return (base + timedelta(days=1)).isoformat(), True
    weekdays = {"monday":0,"tuesday":1,"wednesday":2,"thursday":3,"friday":4,"saturday":5,"sunday":6}
    m = re.fullmatch(r"(?:by |on |this )?(monday|tuesday|wednesday|thursday|friday|saturday|sunday)", s)
    if m:
        wd = weekdays[m.group(1)]; delta = (wd - base.weekday()) % 7
        return (base + timedelta(days=delta)).isoformat(), True
    m = re.fullmatch(r"next (monday|tuesday|wednesday|thursday|friday|saturday|sunday)", s)
    if m:
        wd = weekdays[m.group(1)]; delta = ((wd - base.weekday()) % 7) + 7
        return (base + timedelta(days=delta)).isoformat(), True
    if s == "end of week": return (base + timedelta(days=(4-base.weekday()) % 7)).isoformat(), True
    if s == "end of month":
        n = (base.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        return n.isoformat(), True
    m = re.fullmatch(r"in (\d+) (day|days|week|weeks)", s)
    if m:
        n = int(m.group(1)); days = n * (7 if m.group(2).startswith("week") else 1)
        return (base + timedelta(days=days)).isoformat(), True
    if s == "next week": return (base + timedelta(days=7-base.weekday())).isoformat(), True
    return None, False
