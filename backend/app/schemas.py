from __future__ import annotations
from datetime import date
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

class Summary(StrictModel):
    tldr: str = Field(default="", max_length=400)
    bullets: list[str] = Field(default_factory=list, max_length=6)

class Topic(StrictModel):
    label: str = Field(max_length=80)
    start_segment: str | None = None

class Decision(StrictModel):
    id: str
    text: str = Field(max_length=240)
    decided_by: str | None = None
    evidence: list[str] = Field(min_length=1, max_length=4)
    verified: bool = True
    confirmed: bool = False

class ActionItem(StrictModel):
    id: str
    task: str = Field(max_length=200)
    owner: str | None = None
    due_raw: str | None = None
    due_iso: str | None = None
    due_resolved_from_relative: bool = False
    note: str | None = None
    done: bool = False
    evidence: list[str] = Field(default_factory=list, max_length=4)
    verified: bool = True
    confirmed: bool = False

class EvidenceItem(StrictModel):
    id: str
    text: str = Field(max_length=200)
    evidence: list[str] = Field(default_factory=list, max_length=4)
    verified: bool = False
    confirmed: bool = False

class Risk(StrictModel):
    id: str
    text: str = Field(max_length=200)
    raised_by: str | None = None
    evidence: list[str] = Field(min_length=1, max_length=4)
    verified: bool = True
    confirmed: bool = False

class FollowUps(StrictModel):
    next_meeting: str | None = None
    notify: list[str] = Field(default_factory=list, max_length=5)

class Attendee(StrictModel):
    name: str
    talk_share: float | None = Field(default=None, ge=0, le=1)
    joined_at_s: float | None = None

class MeetingSpec(StrictModel):
    meeting_id: str
    title: str = Field(max_length=120)
    meeting_date: str
    duration_s: float | None = None
    source: Literal["transcript", "upload", "link"]
    summary: Summary = Field(default_factory=Summary)
    topics: list[Topic] = Field(default_factory=list, max_length=8)
    decisions: list[Decision] = Field(default_factory=list, max_length=12)
    action_items: list[ActionItem] = Field(default_factory=list, max_length=25)
    open_questions: list[EvidenceItem] = Field(default_factory=list, max_length=6)
    risks: list[Risk] = Field(default_factory=list, max_length=5)
    follow_ups: FollowUps = Field(default_factory=FollowUps)
    attendees: list[Attendee] = Field(default_factory=list)
    edited: bool = False
    warnings: list[str] = Field(default_factory=list)

    @field_validator("meeting_date")
    @classmethod
    def valid_iso_date(cls, v: str) -> str:
        date.fromisoformat(v)
        return v

class CreateMeeting(StrictModel):
    source: Literal["transcript", "upload", "link"] = "transcript"
    title: str | None = Field(default=None, max_length=120)
    meeting_date: str | None = None
    text: str | None = Field(default=None, max_length=60000)

class TranscriptBody(StrictModel):
    text: str = Field(min_length=1, max_length=60000)

class BotBody(StrictModel):
    meeting_url: str = Field(max_length=1000)
    consent: bool

class AskBody(StrictModel):
    question: str = Field(min_length=1, max_length=300)

class SaveBody(StrictModel):
    spec: MeetingSpec

class HealthProvider(BaseModel):
    name: str
    ok: bool
    latency_ms: int | None = None
    configured: bool = True

class HealthResponse(BaseModel):
    status: Literal["ok"]
    providers: list[HealthProvider]
    default_provider: str
    model: str
    history: dict[str, bool]
    bot: dict[str, str | bool] = Field(default_factory=dict)
