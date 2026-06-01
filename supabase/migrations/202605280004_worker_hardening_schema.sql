-- Arkham Bot — Worker hardening schema changes
-- Date: 2026-05-28
-- Purpose: version the safe Supabase schema changes executed during Mini App / Worker hardening.
--
-- This migration is intentionally idempotent.
-- It records only changes that were already validated as safe in the live Supabase schema.
--
-- DO NOT include the Telegram topic uniqueness change here yet.
-- target_chats still has UNIQUE(chat_id), and changing it requires a coordinated Worker code change.

begin;

-- /packs expects these fields when reading arkham_packs from Supabase.
alter table public.arkham_packs
  add column if not exists cycle_position integer,
  add column if not exists position integer,
  add column if not exists chapter integer,
  add column if not exists total integer;

-- Backfill values from raw JSON. The nullif guard handles empty strings.
-- This assumes the existing raw payload follows ArkhamDB pack fields.
update public.arkham_packs
set
  cycle_position = nullif(raw ->> 'cycle_position', '')::integer,
  position = nullif(raw ->> 'position', '')::integer,
  chapter = coalesce(nullif(raw ->> 'chapter', '')::integer, 1),
  total = coalesce(nullif(raw ->> 'total', '')::integer, 0)
where cycle_position is null
   or position is null
   or chapter is null
   or total is null;

-- Prepare target_chats for soft delete from the Worker.
-- Worker code must still be changed from DELETE to PATCH enabled=false.
alter table public.target_chats
  add column if not exists removed_by_user_id bigint,
  add column if not exists removed_by_name text,
  add column if not exists removed_at timestamptz;

commit;

-- Post-migration validation queries:
--
-- select
--   count(*) as total_packs,
--   count(*) filter (where cycle_position is null) as sem_cycle_position,
--   count(*) filter (where position is null) as sem_position,
--   count(*) filter (where chapter is null) as sem_chapter,
--   count(*) filter (where total is null) as sem_total
-- from public.arkham_packs;
--
-- select
--   column_name,
--   data_type,
--   is_nullable
-- from information_schema.columns
-- where table_schema = 'public'
--   and table_name = 'target_chats'
--   and column_name in ('removed_by_user_id', 'removed_by_name', 'removed_at')
-- order by column_name;
