"""Question-driven extraction, split into four category calls.

Call order and budgets are fixed:

  1. summary + topics          600 tokens   (first, so the UI can show a summary early)
  2. decisions + open_questions 800
  3. actions                    900
  4. risks + follow_ups         500

Calls 2-4 run sequentially to respect provider rate limits. After each call the pipeline
emits a `question` event and one `spec` event per finished section. A call that answers with
bad JSON gets one retry, then its sections are left empty with a warning; the rest of the
meeting is still usable. If the *first* call cannot be made at all, the provider is treated
as unavailable and the chain moves on.
"""
from __future__ import annotations

from typing import Any, AsyncIterator

from app.meetings.questions import parse_questions
from app.meetings.verify import verify_spec
from app.providers.base import (
    BadOutput, MockProvider, ProviderError, circuit_open, provider_for, settings, trip,
)

# (call name, MeetingSpec fields filled, max_output_tokens)
CALLS: tuple[tuple[str, tuple[str, ...], int], ...] = (
    ("summary", ("summary", "topics"), 600),
    ("decisions", ("decisions", "open_questions"), 800),
    ("actions", ("action_items",), 900),
    ("risks", ("risks", "follow_ups"), 500),
)

# questions.md category -> MeetingSpec field
FIELD_FOR_CATEGORY = {
    "summary": "summary",
    "topics": "topics",
    "decisions": "decisions",
    "open_questions": "open_questions",
    "actions": "action_items",
    "risks": "risks",
    "follow_ups": "follow_ups",
}

CATEGORIES_FOR_CALL = {
    "summary": ("summary", "topics"),
    "decisions": ("decisions", "open_questions"),
    "actions": ("actions",),
    "risks": ("risks", "follow_ups"),
}


def empty_spec(segments: list[dict], meeting: dict) -> dict:
    return {
        "meeting_id": meeting["meeting_id"],
        "title": meeting["title"],
        "meeting_date": meeting["meeting_date"],
        "duration_s": segments[-1].get("end") if segments else None,
        "source": meeting["source"],
        "summary": {"tldr": "", "bullets": []},
        "topics": [],
        "decisions": [],
        "action_items": [],
        "open_questions": [],
        "risks": [],
        "follow_ups": {"next_meeting": None, "notify": []},
        "attendees": [],
        "edited": False,
        "warnings": [],
    }


def attendees_from_segments(segments: list[dict]) -> list[dict]:
    """Speaker labels are the only attendee source we can honestly claim (no invented names)."""
    order: list[str] = []
    chars: dict[str, int] = {}
    joined: dict[str, float | None] = {}
    for segment in segments:
        name = (segment.get("speaker") or "").strip()
        if not name:
            continue
        if name not in chars:
            order.append(name); chars[name] = 0; joined[name] = segment.get("start")
        chars[name] += len(segment.get("text") or "")
    total = sum(chars.values()) or 1
    return [
        {"name": name, "talk_share": round(chars[name] / total, 2), "joined_at_s": joined[name]}
        for name in order
    ]


def _normalise(spec: dict) -> dict:
    """Give every item a stable id and the flags the UI and the verifier expect."""
    for category in ("decisions", "action_items", "open_questions", "risks"):
        for index, item in enumerate(spec.get(category) or []):
            if not isinstance(item, dict):
                continue
            item.setdefault("id", f"{category[0]}{index + 1}")
            item.setdefault("evidence", [])
            # Missing `verified` must not mean "false": the C.6 checks below decide.
            item.setdefault("verified", True)
            item.setdefault("confirmed", False)
            if category == "action_items":
                item.setdefault("due_iso", None)
                item.setdefault("due_resolved_from_relative", False)
                item.setdefault("done", False)
                item.setdefault("note", None)
    return spec


def _merge(spec: dict, part: dict[str, Any], fields: tuple[str, ...]) -> None:
    for field in fields:
        if field not in part or part[field] is None:
            continue
        if field == "summary":
            value = part[field]
            if isinstance(value, dict):
                spec["summary"] = {
                    "tldr": str(value.get("tldr") or "")[:400],
                    "bullets": [str(x)[:160] for x in (value.get("bullets") or [])][:6],
                }
        elif field == "follow_ups":
            value = part[field]
            if isinstance(value, dict):
                spec["follow_ups"] = {
                    "next_meeting": value.get("next_meeting") or None,
                    "notify": [str(x) for x in (value.get("notify") or [])][:5],
                }
        elif isinstance(part[field], list):
            spec[field] = part[field][: 25 if field == "action_items" else (12 if field == "decisions" else 8)]


async def _call_with_retry(provider, segments, meeting, group: str, budget: int) -> dict:
    try:
        return await provider.extract_group(segments, meeting, group, budget)
    except BadOutput:
        # C.5: one retry with an explicit reminder, then the caller decides what to do.
        return await provider.extract_group(segments, meeting, group, budget)


def _question_payload(spec: dict, category: str) -> dict:
    field = FIELD_FOR_CATEGORY[category]
    value = spec.get(field)
    if isinstance(value, list):
        return {
            "category": category,
            "count": len(value),
            "unverified": sum(1 for item in value if isinstance(item, dict) and item.get("verified") is False),
        }
    return {"category": category, "count": 1 if value else 0, "unverified": 0}


async def _spec_with_provider(provider, segments, meeting) -> tuple[dict, list[str], list[tuple[str, dict]]]:
    """Run the four calls. Returns (spec, warnings, events) without touching the network policy."""
    spec = empty_spec(segments, meeting)
    warnings: list[str] = []
    events: list[tuple[str, dict]] = []
    for index, (group, fields, budget) in enumerate(CALLS):
        try:
            part = await _call_with_retry(provider, segments, meeting, group, budget)
        except ProviderError as exc:
            if index == 0:
                raise
            warnings.append(f"{group.title()} could not be extracted ({provider.name}); that section is empty.")
            part = {}
        _merge(spec, part, fields)
        if part.get("attendees"):
            spec["attendees"] = part["attendees"]
        events.append(("call", {"group": group, "budget": budget, "ok": bool(part)}))
        for field in fields:
            events.append(("section", {"section": field, "data": spec[field]}))
        for category in CATEGORIES_FOR_CALL[group]:
            events.append(("question", _question_payload(spec, category)))
    if not spec["attendees"]:
        spec["attendees"] = attendees_from_segments(segments)
    spec = _normalise(spec)
    spec["warnings"] = list(dict.fromkeys(warnings + spec["warnings"]))
    return spec, warnings, events


async def iter_extraction(segments: list[dict], meeting: dict) -> AsyncIterator[tuple[str, dict]]:
    """Yield ("call"/"section"/"question"/"result", payload) as the four calls complete."""
    errors: list[str] = []
    for name in settings.provider_chain:
        provider = provider_for(name)
        if provider is None:
            continue
        if circuit_open(name):
            errors.append(f"{name} skipped (recent failure)")
            continue
        try:
            spec, warnings, events = await _spec_with_provider(provider, segments, meeting)
        except ProviderError as exc:
            errors.append(str(exc)); trip(name)
            continue
        for kind, payload in events:
            yield kind, payload
        spec = verify_spec(spec, segments)
        yield "result", {"spec": spec, "provider": name, "warnings": warnings}
        return

    # No real provider worked: fall back to the clearly labelled demo output.
    mock = MockProvider()
    spec, warnings, events = await _spec_with_provider(mock, segments, meeting)
    for kind, payload in events:
        yield kind, payload
    spec = verify_spec(spec, segments)
    if errors:
        spec["warnings"].append("AI providers unavailable; returned clearly labelled demo-mode output.")
    yield "result", {"spec": spec, "provider": "mock", "warnings": warnings}


async def extract_with_chain(segments: list[dict], meeting: dict) -> tuple[dict, str]:
    """Drain iter_extraction for callers (tests, scripts) that only need the final spec."""
    spec: dict = {}
    provider = "mock"
    async for kind, payload in iter_extraction(segments, meeting):
        if kind == "result":
            spec, provider = payload["spec"], payload["provider"]
    return spec, provider
