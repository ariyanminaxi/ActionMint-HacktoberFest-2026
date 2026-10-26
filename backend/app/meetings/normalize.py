from __future__ import annotations
import re
from datetime import datetime

def normalize_transcript(text: str) -> list[dict]:
    """Convert plain text, VTT/SRT, or timestamped transcript lines into stable segments."""
    raw = [line.strip() for line in text.replace("\r", "").splitlines() if line.strip()]
    segments = []
    stamp = re.compile(r"\[(\d{2}):(\d{2}):(\d{2})\]\s*(?:([^:]{1,60}):\s*)?(.*)")
    vtt = re.compile(r"(?:(\d{2}:)?\d{2}:\d{2})[,.]\d{3}\s*-->\s*(?:(\d{2}:)?\d{2}:\d{2})[,.]\d{3}")
    current_time = None
    for line in raw:
        if line.upper().startswith(("WEBVTT", "NOTE ")) or line.isdigit(): continue
        if vtt.match(line):
            left = line.split("-->")[0].strip().replace(",", ".")
            try:
                parts = [float(x) for x in left.split(":")]
                current_time = sum(v * (60 ** i) for i, v in enumerate(reversed(parts)))
            except ValueError: current_time = None
            continue
        m = stamp.match(line)
        if m:
            h, minute, sec = map(int, m.group(1,2,3)); start = h*3600+minute*60+sec
            speaker = m.group(4).strip() if m.group(4) else None
            body = m.group(5).strip()
        else:
            start = current_time; speaker = None; body = line
        if not body or body.lower() in {"um", "uh", "okay okay"}: continue
        if segments and speaker == segments[-1]["speaker"] and start is not None and segments[-1]["end"] is not None and start - segments[-1]["end"] < 2:
            segments[-1]["text"] += " " + body
            segments[-1]["end"] = start
        else:
            segments.append({"id": f"S{len(segments)+1}", "start": start, "end": start, "speaker": speaker, "text": body})
        if current_time is not None: current_time += 2
    if not segments and text.strip():
        for i, sentence in enumerate(re.split(r"(?<=[.!?])\s+", text.strip())):
            if sentence.strip(): segments.append({"id":f"S{i+1}","start":None,"end":None,"speaker":None,"text":sentence.strip()})
    return segments

def format_stamp(seconds: float | None) -> str | None:
    if seconds is None: return None
    s = int(seconds); return f"{s//3600:02d}:{(s%3600)//60:02d}:{s%60:02d}"
