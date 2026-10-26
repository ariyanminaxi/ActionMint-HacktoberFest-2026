from __future__ import annotations
import asyncio
from app.meetings.sample import SAMPLE_TRANSCRIPT
from app.meetings.normalize import normalize_transcript

async def replay_sample(on_segment):
    """Transparent demo adapter: replays bundled text, not a real meeting bot."""
    for segment in normalize_transcript(SAMPLE_TRANSCRIPT):
        await asyncio.sleep(.18)
        await on_segment(segment)
