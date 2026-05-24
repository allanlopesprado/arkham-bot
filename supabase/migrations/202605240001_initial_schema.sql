create extension if not exists pgcrypto;

create or replace function public.set_updated_at()
returns trigger
language plpgsql
set search_path = public
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create table if not exists public.arkham_cards (
  code text primary key,
  name text not null,
  real_name text,
  type_code text,
  subtype_code text,
  faction_code text,
  faction_name text,
  pack_code text,
  pack_name text,
  position integer,
  xp integer,
  cost integer,
  quantity integer,
  is_unique boolean,
  is_exceptional boolean,
  deck_limit integer,
  text text,
  real_text text,
  flavor text,
  traits text,
  skill_willpower integer,
  skill_intellect integer,
  skill_combat integer,
  skill_agility integer,
  health integer,
  sanity integer,
  imagesrc text,
  backimagesrc text,
  spoiler_level text not null default 'safe',
  raw jsonb not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.arkham_packs (
  code text primary key,
  name text not null,
  raw jsonb not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.arkham_factions (
  code text primary key,
  name text not null,
  raw jsonb not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.arkham_faq (
  id uuid primary key default gen_random_uuid(),
  card_code text unique,
  raw jsonb not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.arkham_taboos (
  id uuid primary key default gen_random_uuid(),
  taboo_id text unique,
  raw jsonb not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.arkham_decklists_cache (
  decklist_id text primary key,
  raw jsonb not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.bot_settings (
  key text primary key,
  value jsonb not null,
  description text,
  updated_by text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.target_chats (
  id uuid primary key default gen_random_uuid(),
  chat_id text not null unique,
  title text,
  message_thread_id bigint,
  enabled boolean not null default true,
  raw jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.bot_admins (
  telegram_user_id bigint primary key,
  name text,
  role text not null default 'admin' check (role in ('owner','admin','viewer')),
  enabled boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.bot_commands (
  id uuid primary key default gen_random_uuid(),
  command_type text not null,
  payload jsonb not null,
  result jsonb,
  status text not null default 'pending' check (status in ('pending','processing','retrying','executed','failed','cancelled')),
  requested_by_telegram_user_id bigint,
  requested_by_name text,
  target_chat_id text,
  attempt_count integer not null default 0,
  max_attempts integer not null default 3,
  last_error text,
  scheduled_for timestamptz,
  next_attempt_at timestamptz,
  executed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.bot_posted_cards (
  card_code text primary key,
  posted_at timestamptz not null default now(),
  telegram_message_id bigint,
  target_chat_id text,
  raw jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.bot_posting_history (
  id uuid primary key default gen_random_uuid(),
  card_code text,
  card_name text,
  status text not null,
  target_chat_id text,
  telegram_message_id bigint,
  raw jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.bot_errors (
  id uuid primary key default gen_random_uuid(),
  context text,
  error_message text not null,
  card_code text,
  raw jsonb,
  created_at timestamptz not null default now()
);

create table if not exists public.audit_logs (
  id uuid primary key default gen_random_uuid(),
  actor_telegram_user_id bigint,
  actor_name text,
  action_type text not null,
  source text not null check (source in ('telegram_command','telegram_button','mini_app','system_job','ai_process','github_deploy','manual_script')),
  payload jsonb,
  result jsonb,
  ip_address text,
  user_agent text,
  created_at timestamptz not null default now()
);

create index if not exists idx_arkham_cards_name on public.arkham_cards using gin (to_tsvector('simple', coalesce(name,'') || ' ' || coalesce(real_name,'')));
create index if not exists idx_arkham_cards_type_code on public.arkham_cards(type_code);
create index if not exists idx_arkham_cards_faction_code on public.arkham_cards(faction_code);
create index if not exists idx_arkham_cards_pack_code on public.arkham_cards(pack_code);
create index if not exists idx_arkham_cards_spoiler_level on public.arkham_cards(spoiler_level);
create index if not exists idx_bot_commands_status on public.bot_commands(status);
create index if not exists idx_bot_commands_scheduled_for on public.bot_commands(scheduled_for);
create index if not exists idx_bot_commands_next_attempt_at on public.bot_commands(next_attempt_at);
create index if not exists idx_audit_logs_created_at on public.audit_logs(created_at);

do $$
declare
  table_name text;
begin
  foreach table_name in array array[
    'arkham_cards','arkham_packs','arkham_factions','arkham_faq','arkham_taboos',
    'arkham_decklists_cache','bot_settings','target_chats','bot_admins','bot_commands',
    'bot_posted_cards','bot_posting_history'
  ]
  loop
    execute format('drop trigger if exists trg_%I_updated_at on public.%I', table_name, table_name);
    execute format('create trigger trg_%I_updated_at before update on public.%I for each row execute function public.set_updated_at()', table_name, table_name);
  end loop;
end;
$$;

alter table public.arkham_cards enable row level security;
alter table public.arkham_packs enable row level security;
alter table public.arkham_factions enable row level security;
alter table public.arkham_faq enable row level security;
alter table public.arkham_taboos enable row level security;
alter table public.arkham_decklists_cache enable row level security;
alter table public.bot_settings enable row level security;
alter table public.target_chats enable row level security;
alter table public.bot_admins enable row level security;
alter table public.bot_commands enable row level security;
alter table public.bot_posted_cards enable row level security;
alter table public.bot_posting_history enable row level security;
alter table public.bot_errors enable row level security;
alter table public.audit_logs enable row level security;

-- RLS is enabled intentionally. Do not add permissive public policies here.
-- The Python backend uses service_role. Mini App/admin policies must be created only after the auth/admin phase.

insert into public.bot_settings (key, value, description)
values
  ('daily_post_enabled', 'true'::jsonb, 'Enable daily card posting'),
  ('daily_post_times', '["08:00"]'::jsonb, 'Daily card post times'),
  ('timezone', '"America/Sao_Paulo"'::jsonb, 'Default bot timezone')
on conflict (key) do nothing;
