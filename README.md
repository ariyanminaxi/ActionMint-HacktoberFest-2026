# ActionMint

Turn a meeting transcript into decisions, owners and dates you can act on — and keep the uncertainty visible.

Long meetings reliably lose the two things that matter afterwards: what was actually decided, and who promised to do what. ActionMint takes a transcript (or a recording, or a bot that listens) and produces a short summary, a decisions list, an action checklist with owners and due dates, open questions, risks and follow-ups. Then it makes you check it before anyone sees it, and exports the version you approved.

## Demo

There is **no public deployment** in this repository. The Render blueprint (`render.yaml`) and the
static Vercel config are ready but were not deployed from here; every command below was run
locally. The fastest demo is mock mode, which needs no API keys.

Screenshots from the Playwright walkthrough are committed in [`docs/screenshots/`](docs/screenshots/):
the token gate, landing page, processing view, review overview, a tab transition mid-flight, the
Actions lanes, the Meet-only error, the simulated-bot result, and 360/768 px layouts. They are
captures of the running app, not mockups.

## How it works

```text
INPUT                NORMALISE          EXTRACT             VERIFY (code)        REVIEW/EDIT        EXPORT
paste / .txt/.vtt ┐
upload -> STT     ├─> segments[]  ──>  4 category    ──>   evidence + owner  ──> editable store ──> md/json/csv/ics
meeting link      ┘    S1..Sn           calls -> JSON      + date checks         (undo, validate)    + recap card
```

Owners and due dates are the easiest things for a model to invent, so they are only kept when the meeting actually says them. Every extracted item cites the transcript segments it came from; the backend re-checks those citations in code (the cited ids must exist, at least 40% of the item's content words must appear in them, and any owner or date must literally appear in the evidence). Anything that fails is **kept but flagged** with an amber "Check this" badge instead of being deleted, and the count appears in a banner above the tabs. Exports mark unverified items with `(unverified)`; the recap card leaves them off entirely.

## Inputs

| Input | Accepted | Limits |
|---|---|---|
| Paste text | plain text, `[hh:mm:ss] Speaker:` lines, `.vtt`, `.srt` pasted in | 60,000 characters |
| Upload `.txt` / `.vtt` / `.srt` | read as text | 60,000 characters |
| Upload audio/video | `.mp3 .wav .m4a .mp4 .webm .mkv`, extension **and** magic bytes checked | 10 MB, 5 minutes (configurable) |
| Meeting link | simulated bot only (see below) | — |

## Outputs

| Output | Where | Built from |
|---|---|---|
| TL;DR + key points | Overview tab | draft, editable |
| Decisions (with decider + evidence) | Decisions tab | draft, editable |
| Action items, owner, due date, done state | Actions tab | draft, editable |
| Open questions, risks, follow-ups | Overview (editable) | draft, editable |
| Attendees, talk share, join time | People tab | draft |
| Timeline of topics, decisions, actions | Timeline tab | draft |
| Recap card | Recap tab | **edited** state, verified items only |
| Markdown | Download | **edited** state |
| JSON (full `MeetingSpec`) | Download | **edited** state |
| CSV (action items, formula-injection escaped) | Download | **edited** state |
| ICS (one all-day event per dated action) | Download | **edited** state |
| Print / PDF | Browser print stylesheet | **edited** state |

## A worked example

Input (`backend/data/samples/standup.txt`, the "golden sample"):

```text
[00:00:41] Priya: Agreed. Let's move the launch to November 4th. That's decided.
[00:00:55] Anita: I can fix the payment blockers. I'll have them done by Friday.
[00:01:10] Priya: Great. Rahul, please re-run the full regression once Anita is done.
[00:01:22] Rahul: Sure, I'll do that early next week.
```

Output:

```text
Decisions
1. Move the launch to November 4th. — decided by Priya [S3]

Action items
| Done | Task                                | Owner  | Due        | Source |
| [ ]  | Fix the payment-flow blockers.      | Anita  | 2026-10-30 | S4     |
| [ ]  | Re-run the full regression ...      | Rahul  | early next week | S5, S6 |
| [ ]  | Ask finance about annual discounts  | Priya  | —          | S9     |
```

`by Friday` resolves to 2026-10-30 (day-first dates, meeting date 2026-10-26, a Monday). `early next week` cannot be resolved deterministically, so it stays as the spoken phrase with no date. This is the golden fixture the tests assert against: three actions, one decision, zero invented owners, zero invented dates.

## Quick start

Windows (PowerShell), from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
$env:PROVIDER_CHAIN="mock"; $env:STT_BACKEND="mock"; $env:ENV="dev"
cd backend; uvicorn app.main:app --reload --port 8000
```

In a second terminal:

```powershell
cd frontend
corepack pnpm install --frozen-lockfile
corepack pnpm run dev
```

Open http://localhost:5173 and press **Use local demo token** (development accepts `dev-token-change-me`). macOS/Linux: same commands with `.venv/bin/activate`, `export` instead of `$env:`, and `/` instead of `\`.

Python 3.11 and 3.12 are both verified (`uv venv --python 3.11` or `py -3.11`); 3.14 also passes locally. Python 3.11/3.12 is required only for the optional `faster-whisper` path — the mock STT works everywhere.

Mock mode needs no keys at all. To use a real model, copy `backend/.env.example` to `.env` and set `GEMINI_API_KEY` and/or `GROQ_API_KEY`; the chain is `gemini,groq,ollama,mock` and falls through to the next provider on a rate limit, a connection error or a circuit breaker trip.

Asset pipeline (only needed when the category images change):

```powershell
pip install pillow numpy
python scripts\keyout.py --all raw frontend\public\assets\categories
```

## Configuration

Every value is blank in the committed `.example` files. Names only, no values.

| Variable | File | Purpose |
|---|---|---|
| `APP_TOKEN` | `.env` | shared access token sent as `X-App-Token` (required outside `ENV=dev`) |
| `ENV` | `.env` | `dev` or `prod`; `prod` refuses to start without `APP_TOKEN` |
| `ALLOWED_ORIGINS` | `.env` | CORS allowlist |
| `PROVIDER_CHAIN` | `.env` | provider order, default `gemini,groq,ollama,mock` |
| `GEMINI_API_KEY`, `GEMINI_MODEL` | `.env` | primary provider |
| `GROQ_API_KEY`, `GROQ_MODEL`, `GROQ_BASE_URL` | `.env` | backup provider; absent when no key |
| `OLLAMA_URL`, `OLLAMA_MODEL` | `.env` | optional local provider |
| `STT_BACKEND`, `STT_MODEL` | `.env` | `mock` or `faster-whisper` |
| `MAX_MEDIA_MB`, `MAX_MEDIA_MIN` | `.env` | upload limits |
| `BOT_BACKEND`, `BOT_NAME`, `BOT_PLATFORMS` | `.env` | `simulated` (default) |
| `BOT_API_KEY`, `BOT_API_BASE`, `BOT_WORKER_URL`, `BOT_WORKER_SECRET`, `BOT_WEBHOOK_SECRET` | `.env` | reserved for a hosted bot; unused by the simulated bot |
| `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` | `.env` | optional cloud history, off unless both are set |
| `VITE_API_BASE` | `frontend/.env` | API origin for the static build |

## Project structure

```text
frontend/    React + Vite + TypeScript app (landing, /meet, /meet/:id review)  -> frontend/README.md
backend/     FastAPI service: ingest, normalise, extract, verify, export, history -> backend/README.md
model/       provider config and the env template (no weights, no keys)      -> model/README.md
scripts/     check.py, ping.py, keyout.py (asset pipeline)                  -> scripts/README.md
supabase/    optional history migration                                    -> supabase/README.md
docs/        architecture, demo script, screenshots                         -> docs/README.md
.github/     CI: check --strict, pytest on 3.11 + 3.12, tsc, lint, vitest, build
```

The layout is the final one from the brief: application code only in `backend/` and `frontend/`,
design-time inputs in `raw/` (git-ignored), artefacts in `docs/screenshots/`, and no generated
build output or secrets in the tree.

## Bot and meeting links

`BOT_BACKEND=simulated` (the default) replays the bundled sample transcript at 8× speed through the real token, live-caption, finalize and review path. It is always labelled "Simulated bot" and **never joins a call**.

There is no real meeting bot in this build. Automated participants need host admission, organisation policy and platform-terms checks; a real bot would need a worker that joins as a guest and reads the platform's live captions. Anyone in the meeting must be told that a bot is recording and transcribing — the consent checkbox on `/meet` is mandatory.

## Privacy

Transcripts, audio and results live in server memory only and are purged when the session expires (30 minutes from the last activity, 3 hours for a live bot session). Uploaded media is deleted right after transcription. Nothing is written to disk. Cloud history is optional, off by default, and stores only the reviewed `MeetingSpec` — never the transcript or audio — and is shared by everyone holding the app token. Logs contain meeting ids, stages and latencies, never transcript text.

## Testing

```powershell
python scripts\check.py --strict
cd backend; python -m pytest -q
cd frontend; corepack pnpm run typecheck; corepack pnpm run lint; corepack pnpm run test; corepack pnpm run build
python scripts\ping.py http://127.0.0.1:8000
```

A pass looks like: `ActionMint repository checks passed (strict)`, **52 passed** (backend),
no TypeScript output, a clean ESLint run, **38 passed** across 7 vitest files, a Vite build with no
errors, and `Healthy: .../health`. The CI workflow runs the backend suite on Python 3.11 and 3.12
and the frontend checks on Node 20.

The UI itself is verified in a real browser. With the backend (`PROVIDER_CHAIN=mock`,
`STT_BACKEND=mock`, a throwaway `APP_TOKEN`) and Vite running:

```powershell
cd frontend
npx playwright install chromium
$env:E2E_APP_TOKEN="<the same throwaway token>"
node e2e/demo.mjs
```

It drives the token dialog, the demo transcript, processing, results, tab transitions, owner/date
edits, undo/redo, reorder, merge, export validation, Markdown + ICS downloads, the Meet-only
validator, the consent-gated simulated bot, 360/768 px layouts and keyboard focus, and fails on a
console error or a failed request. It also writes the screenshots above.

## Known limits

- Long transcripts are truncated to the provider's window; map-reduce windowing is planned but not implemented.
- Data is in memory: a restart loses sessions. Short meetings only (60k characters / 5 minutes of audio by default).
- Real transcription needs `faster-whisper` and a Python 3.11/3.12 interpreter; the mock STT path returns the bundled sample and says so.
- The Flow and History tabs stay hidden until they have content; there is no History UI in this build.
- **No real meeting bot.** Link input goes through the consent-gated simulated adapter, which replays the sample transcript and never joins a call. There is no live-caption view during capture and no capture-my-tab audio mode yet.
- **No Listen (text-to-speech) bar** in this build.
- Supabase history is optional and unconfigured here, so the save/history endpoints return `history_unavailable`.

## What we would build next

1. A self-hosted caption-reading bot for Google Meet (or the no-bot `getDisplayMedia` capture path), with consent, an allowlist and a kill switch.
2. A spoken read-out of the notes (Web Speech API), verified items only, so the summary can be listened to on the way out of the room.
3. Real STT in the deploy image (pinned Python 3.11 with `faster-whisper`) instead of the labelled mock transcription.

## Credits

Thank you to the people and projects this app is built on. Each project keeps its own licence;
these credits do not change it. The generated list with exact versions and licences is in
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

**Models and APIs**
- [Google Gemini API](https://ai.google.dev/) and the Gemma model family — Google — model use under Google's API terms.
- [Groq](https://groq.com/) — Groq, Inc. — OpenAI-compatible chat completions under Groq's terms.
- [Ollama](https://ollama.com/) — Ollama contributors (MIT client); individual model licences vary.
- [Supabase](https://supabase.com/) — Supabase Inc. — optional history storage under its terms.

**Speech**
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) — SYSTRAN (MIT), optional local transcription.
- [imageio-ffmpeg](https://github.com/imageio/imageio-ffmpeg) — ImageIO contributors (BSD-2-Clause), bundled FFmpeg binary; FFmpeg itself is LGPL/GPL depending on the build.
- The Web Speech API is provided by the user's browser; the Listen feature never uploads audio.

**Backend**
- [FastAPI](https://fastapi.tiangolo.com/) — Sebastián Ramírez (MIT) · [Uvicorn](https://www.uvicorn.org/) — Encode (BSD-3-Clause) · [Pydantic](https://docs.pydantic.dev/) — Pydantic Services Inc. (MIT) · [HTTPX](https://www.python-httpx.org/) — Encode (BSD-3-Clause) · [SlowAPI](https://github.com/laurentS/slowapi) — Léo Unbekandt (MIT) · [google-genai](https://github.com/googleapis/python-genai) — Google (Apache-2.0) · [python-dotenv](https://github.com/theskumar/python-dotenv) — Saurabh Kumar (BSD-3-Clause) · [python-multipart](https://github.com/Kludex/python-multipart) — Andrew Dunham and contributors (Apache-2.0) · [pytest](https://pytest.org/) — pytest-dev (MIT) · [anyio](https://anyio.readthedocs.io/) — Alex Grönholm (MIT).

**Frontend**
- [React](https://react.dev/) — Meta (MIT) · [React Router](https://reactrouter.com/) — Remix Software (MIT) · [Zustand](https://github.com/pmndrs/zustand) — pmndrs contributors (MIT) · [zod](https://zod.dev/) — Colin McDonnell (MIT) · [lucide](https://lucide.dev/) — Lucide contributors (ISC) · [GSAP and ScrollTrigger](https://gsap.com/) — Webflow/GreenSock (GreenSock standard no-charge licence) · [Lenis](https://github.com/darkroomengineering/lenis) — Studio Freight / darkroom.engineering (MIT).
- [Vite](https://vite.dev/) — Evan You and Vite contributors (MIT) · [TypeScript](https://www.typescriptlang.org/) — Microsoft (Apache-2.0) · [Vitest](https://vitest.dev/) — Vitest contributors (MIT) · [Playwright](https://playwright.dev/) — Microsoft (Apache-2.0) · [ESLint](https://eslint.org/) — OpenJS Foundation (MIT).

**Fonts**
- [DM Sans](https://fonts.google.com/specimen/DM+Sans) via [Fontsource](https://fontsource.org/) — Colophon Foundry for Google (SIL OFL 1.1).
- [Space Grotesk](https://fonts.google.com/specimen/Space+Grotesk) via Fontsource — Florian Karsten (SIL OFL 1.1).

**Hosting and tooling**
- [Render](https://render.com/) — Render Services, Inc. — blueprint hosting under its terms.
- [GitHub Actions](https://github.com/features/actions) — GitHub, Inc.
- [Pillow](https://python-pillow.org/) — Jeffrey A. Clark and contributors (MIT-CMU) and [NumPy](https://numpy.org/) — NumPy contributors (BSD-3-Clause) for the category-image pipeline.

**Artwork and samples**
The category illustrations were produced with an image-generation model and edited by the team;
they are not hand-drawn. The sample meeting transcript in `backend/data/samples/standup.txt` was
written by the team. No meeting-bot repository was adopted for this build; the simulated bot is
original code.

## License

MIT — see [LICENSE](LICENSE).
