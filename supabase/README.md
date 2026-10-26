# supabase (optional)

Cloud history is **off by default**. Nothing here runs unless both `SUPABASE_URL` and
`SUPABASE_SERVICE_KEY` are set on the backend, and the UI has no History tab in this build.

- `migrations/0001_meetings_saved.sql` — one table, `meetings_saved`, keyed by `meeting_id`, with
  the reviewed `MeetingSpec` as JSONB. It never stores transcripts, audio or tokens.

To enable it, apply the migration in the Supabase SQL editor and set the two variables in the
backend environment (never in a committed file, never in the browser). Without them, `/api/history`
returns a clear `history_unavailable` error and the review flow is unaffected.
