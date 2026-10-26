import dataclasses

import pytest

from app import config
from app.meetings import extraction
from app.meetings.normalize import normalize_transcript
from app.meetings.sample import SAMPLE_TRANSCRIPT
from app.providers.base import Provider, ProviderError, reset_circuit

SEGMENTS = normalize_transcript(SAMPLE_TRANSCRIPT)
MEETING = {"meeting_id": "abc12345", "title": "Launch readiness", "meeting_date": "2026-10-26", "source": "transcript"}
GOLDEN_MARKERS = {
    "summary": {"summary": {"tldr": "A test summary.", "bullets": ["One point"]}, "topics": [{"label": "Launch", "start_segment": "S1"}]},
    "decisions": {"decisions": [{"id": "d1", "text": "Move the launch to November 4th.", "decided_by": "Priya", "evidence": ["S3"]}],
                  "open_questions": [{"id": "q1", "text": "Will the pricing page show annual discounts?", "evidence": ["S7"]}]},
    "actions": {"action_items": [{"id": "a1", "task": "Fix the payment-flow blockers.", "owner": "Anita", "due_raw": "by Friday", "note": None, "evidence": ["S4"]}]},
    "risks": {"risks": [{"id": "r1", "text": "A further payment-provider API change could delay the launch.", "raised_by": "Rahul", "evidence": ["S10"]}],
              "follow_ups": {"next_meeting": "next Tuesday", "notify": ["Finance"]}},
}


class FakeProvider(Provider):
    name = "fake"

    def __init__(self, fail_on: str | None = None, bad_json_on: str | None = None):
        self.calls: list[tuple[str, int]] = []
        self.fail_on = fail_on
        self.bad_json_on = bad_json_on

    async def extract_group(self, segments, meeting, group, max_tokens):
        self.calls.append((group, max_tokens))
        if group == self.fail_on:
            raise ProviderError("provider unavailable")
        return GOLDEN_MARKERS[group]


class SecondProvider(FakeProvider):
    name = "second"


def use_chain(monkeypatch, *providers):
    by_name = {provider.name: provider for provider in providers}
    monkeypatch.setattr(extraction, "settings", dataclasses.replace(config.settings, provider_chain=tuple(by_name)))
    monkeypatch.setattr(extraction, "provider_for", lambda name: by_name.get(name))
    reset_circuit()


@pytest.mark.anyio
async def test_four_calls_run_in_order_with_the_documented_budgets(monkeypatch):
    fake = FakeProvider()
    use_chain(monkeypatch, fake)
    kinds: list[str] = []
    spec = None
    async for kind, payload in extraction.iter_extraction(SEGMENTS, MEETING):
        kinds.append(kind)
        if kind == "result":
            spec = payload["spec"]
    assert fake.calls == [("summary", 600), ("decisions", 800), ("actions", 900), ("risks", 500)]
    # A question event follows each call, and the calls themselves are announced.
    assert kinds.count("call") == 4
    assert kinds.count("question") == 7  # 2 + 2 + 1 + 2 categories
    assert kinds[-1] == "result"
    first_question = kinds.index("question")
    assert kinds.index("call") < first_question
    assert spec["action_items"][0]["due_iso"] == "2026-10-30"
    assert spec["follow_ups"]["next_meeting"] == "next Tuesday"


@pytest.mark.anyio
async def test_a_failed_later_call_leaves_only_that_section_empty(monkeypatch):
    fake = FakeProvider(fail_on="actions")
    use_chain(monkeypatch, fake)
    spec = None
    async for kind, payload in extraction.iter_extraction(SEGMENTS, MEETING):
        if kind == "result":
            spec = payload["spec"]
    assert spec["action_items"] == []
    assert any("Actions" in warning for warning in spec["warnings"])
    assert spec["decisions"] and spec["risks"] and spec["summary"]["tldr"]


@pytest.mark.anyio
async def test_a_dead_first_call_moves_down_the_chain(monkeypatch):
    dead = FakeProvider(fail_on="summary")
    dead.name = "dead"
    second = SecondProvider()
    use_chain(monkeypatch, dead, second)
    spec = None
    async for kind, payload in extraction.iter_extraction(SEGMENTS, MEETING):
        if kind == "result":
            spec = payload["spec"]
    assert dead.calls == [("summary", 600)]
    assert len(second.calls) == 4
    assert spec["summary"]["tldr"] == "A test summary."


@pytest.mark.anyio
async def test_attendees_come_from_speaker_labels_when_the_model_returns_none(monkeypatch):
    fake = FakeProvider()
    use_chain(monkeypatch, fake)
    spec = None
    async for kind, payload in extraction.iter_extraction(SEGMENTS, MEETING):
        if kind == "result":
            spec = payload["spec"]
    names = [person["name"] for person in spec["attendees"]]
    assert names == ["Priya", "Rahul", "Anita"]
    assert abs(sum(person["talk_share"] for person in spec["attendees"]) - 1) < 0.05


@pytest.mark.anyio
async def test_an_invented_owner_is_dropped_by_the_verifier(monkeypatch):
    fake = FakeProvider()
    fake.calls = []

    async def extract_group(segments, meeting, group, max_tokens):
        fake.calls.append((group, max_tokens))
        data = GOLDEN_MARKERS[group]
        if group == "actions":
            data = {"action_items": [{"id": "a1", "task": "Fix the payment-flow blockers.", "owner": "Grace", "due_raw": "by Friday", "evidence": ["S4"]}]}
        return data

    fake.extract_group = extract_group
    use_chain(monkeypatch, fake)
    spec = None
    async for kind, payload in extraction.iter_extraction(SEGMENTS, MEETING):
        if kind == "result":
            spec = payload["spec"]
    assert spec["action_items"][0]["owner"] is None
    assert "owner not stated" in (spec["action_items"][0]["note"] or "")
    assert spec["action_items"][0]["due_iso"] == "2026-10-30"  # "by Friday" was spoken
