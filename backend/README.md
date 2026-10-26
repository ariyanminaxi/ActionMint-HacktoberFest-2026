# backend

FastAPI service for ActionMint. It ingests a transcript or a short recording, normalises it into
segments, runs the four-call extraction, verifies every citation in code, and
serves the editable meeting state over plain JSON plus one SSE stream.

## Layout

```text
app/main.py              routes, rate limits, security headers, SSE
app/config.py            settings from the environment (never from committed files)
app/security.py          X-App-Token and per-meeting session token checks
app/schemas.py           pydantic MeetingSpec and request bodies
app/meetings/            normalize, extraction (4 calls), verify, dates, questions, export_md, store
app/providers/           gemini, groq, ollama (OpenAI-compatible), mock + circuit breaker
app/stt/                 media transcription (mock by default)
app/bots/simulated.py    replays the sample transcript; never joins a call
app/history/             optional Supabase history client
data/questions.md        the extraction rubric parsed at runtime
data/standup.txt         the golden sample transcript
tests/                   pytest suite (extraction, providers, API, dates, Meet URLs)
```

## Run

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:ENV="dev"; $env:PROVIDER_CHAIN="mock"; $env:STT_BACKEND="mock"
uvicorn app.main:app --reload --port 8000
```

`ENV=prod` refuses to start without a real `APP_TOKEN`; `APP_TOKEN` is required on every `/api/*`
request as `X-App-Token`. Python 3.11 and 3.12 are both tested (3.14 also passes locally).

## Test

```powershell
python -m pytest -q
```

Optional real transcription: install `requirements-stt.txt` on Python 3.11/3.12 and set
`STT_BACKEND=faster-whisper`. Keep it out of the deploy: Render uses `STT_BACKEND=mock`.

## Data and privacy

Sessions live in process memory with a TTL, transcripts are never logged, and uploaded media is
deleted after transcription. A restart drops every session; there is no database requirement.
