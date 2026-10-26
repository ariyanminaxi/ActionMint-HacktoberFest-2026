create extension if not exists pgcrypto;

create table if not exists public.meetings_saved (
  id uuid primary key default gen_random_uuid(),
  meeting_id text not null unique,
  title text not null,
  meeting_date date not null,
  spec jsonb not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists meetings_saved_created_idx
  on public.meetings_saved (created_at desc);

alter table public.meetings_saved enable row level security;
revoke all on public.meetings_saved from anon, authenticated;
