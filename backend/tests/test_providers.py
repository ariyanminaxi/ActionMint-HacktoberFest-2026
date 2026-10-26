import dataclasses
import json
import logging

import httpx
import pytest

from app import config
from app.meetings import extraction
from app.meetings.normalize import normalize_transcript
from app.meetings.sample import SAMPLE_TRANSCRIPT, golden_spec
from app.providers import base

SEGMENTS = normalize_transcript(SAMPLE_TRANSCRIPT)
MEETING = {"meeting_id": "abc12345", "title": "Launch readiness", "meeting_date": "2026-10-26", "source": "transcript"}
GROQ_KEY = "gsk_test_key_that_must_never_leak_0123456789"


def group_payload(prompt: str) -> dict:
    """One chat-completions answer per extraction call, mirroring the golden extraction."""
    spec = golden_spec("abc12345", "2026-10-26")
    if "Q-SUM-1" in prompt:
        return {"summary": spec["summary"], "topics": spec["topics"], "attendees": spec["attendees"]}
    if "Q-DEC-1" in prompt:
        return {"decisions": spec["decisions"], "open_questions": spec["open_questions"]}
    if "Q-ACT-1" in prompt:
        actions = []
        for item in spec["action_items"]:
            clean = {k: v for k, v in item.items() if k not in ("due_iso", "due_resolved_from_relative", "done")}
            actions.append(clean)
        return {"action_items": actions}
    if "Q-RISK-1" in prompt:
        return {"risks": spec["risks"], "follow_ups": spec["follow_ups"]}
    raise AssertionError("prompt did not contain a known question id")


@pytest.fixture
def groq_env(monkeypatch):
    """Settings is frozen, so swap the module-level instance instead of patching a field."""
    patched = dataclasses.replace(config.settings, groq_api_key=GROQ_KEY, provider_chain=("groq", "mock"))
    monkeypatch.setattr(base, "settings", patched)
    monkeypatch.setattr(extraction, "settings", patched)
    base.reset_circuit()
    yield
    base.reset_circuit()


def patch_transport(monkeypatch, handler):
    real_client = httpx.AsyncClient

    def factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_client(*args, **kwargs)

    monkeypatch.setattr(base.httpx, "AsyncClient", factory)


def test_groq_is_absent_without_a_key(monkeypatch):
    monkeypatch.setattr(base, "settings", dataclasses.replace(config.settings, groq_api_key=""))
    assert base.provider_for("groq") is None
    monkeypatch.setattr(base, "settings", dataclasses.replace(config.settings, groq_api_key=GROQ_KEY))
    provider = base.provider_for("groq")
    assert provider is not None and provider.name == "groq"
    assert provider.model == "openai/gpt-oss-20b"
    assert provider.max_tokens == 900


@pytest.mark.anyio
async def test_groq_makes_four_budgeted_calls_in_order(monkeypatch, groq_env):
    seen = {"bodies": [], "auth": None, "urls": set()}

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        seen["bodies"].append(body)
        seen["auth"] = request.headers.get("authorization")
        seen["urls"].add(str(request.url))
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(group_payload(body["messages"][0]["content"]))}}]})

    patch_transport(monkeypatch, handler)
    spec, provider = await extraction.extract_with_chain(SEGMENTS, MEETING)
    assert provider == "groq"
    assert seen["auth"] == f"Bearer {GROQ_KEY}"
    assert seen["urls"] == {"https://api.groq.com/openai/v1/chat/completions"}
    assert len(seen["bodies"]) == 4
    assert [body["max_tokens"] for body in seen["bodies"]] == [600, 800, 900, 500]
    assert seen["bodies"][0]["model"] == "openai/gpt-oss-20b"
    # Call 1 asks for the summary, call 3 for the actions: order matters for the UI.
    assert "Q-SUM-1" in seen["bodies"][0]["messages"][0]["content"]
    assert "Q-DEC-1" in seen["bodies"][1]["messages"][0]["content"]
    assert "Q-ACT-1" in seen["bodies"][2]["messages"][0]["content"]
    assert "Q-RISK-1" in seen["bodies"][3]["messages"][0]["content"]
    assert spec["action_items"][0]["owner"] == "Anita"
    assert spec["action_items"][0]["due_iso"] == "2026-10-30"
    assert spec["summary"]["tldr"]


@pytest.mark.anyio
async def test_groq_429_falls_through_to_the_next_provider(monkeypatch, groq_env):
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(429, headers={"retry-after": "0"}, json={"error": "rate limited"})

    patch_transport(monkeypatch, handler)
    monkeypatch.setattr(base.asyncio, "sleep", _no_sleep)
    spec, provider = await extraction.extract_with_chain(SEGMENTS, MEETING)
    assert provider == "mock"
    assert calls["n"] == 3  # initial try plus the two allowed retries, then the chain moves on
    assert base.circuit_open("groq")
    assert spec["warnings"]  # demo mode is labelled, never silent


@pytest.mark.anyio
async def test_groq_connect_error_then_circuit_breaker_skips_it(monkeypatch, groq_env):
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        raise httpx.ConnectError("no route", request=request)

    patch_transport(monkeypatch, handler)
    _, first = await extraction.extract_with_chain(SEGMENTS, MEETING)
    assert first == "mock"
    _, second = await extraction.extract_with_chain(SEGMENTS, MEETING)
    assert second == "mock"
    assert calls["n"] == 1  # the breaker remembered the failure for 60 s


@pytest.mark.anyio
async def test_malformed_body_is_retried_once_then_falls_back(monkeypatch, groq_env):
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(200, json={"choices": [{"message": {"content": "not json at all"}}]})

    patch_transport(monkeypatch, handler)
    spec, provider = await extraction.extract_with_chain(SEGMENTS, MEETING)
    assert provider == "mock"
    assert calls["n"] == 2  # the C.5 retry, then the chain moves on
    assert spec["summary"]["tldr"]


@pytest.mark.anyio
async def test_groq_key_never_appears_in_logs_or_errors(monkeypatch, groq_env, caplog):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route", request=request)

    patch_transport(monkeypatch, handler)
    with caplog.at_level(logging.DEBUG):
        spec, provider = await extraction.extract_with_chain(SEGMENTS, MEETING)
    assert provider == "mock"
    assert GROQ_KEY not in caplog.text
    assert GROQ_KEY not in json.dumps(spec)


async def _no_sleep(_seconds):
    return None
