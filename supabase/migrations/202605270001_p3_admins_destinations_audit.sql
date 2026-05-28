-- P3: audit columns for bot_admins, added_by for target_chats, RLS policies
-- bot_admins: add audit columns
alter table public.bot_admins
  add column if not exists added_by_user_id bigint,
  add column if not exists added_by_name text,
  add column if not exists removed_by_user_id bigint,
  add column if not exists removed_by_name text,
  add column if not exists removed_at timestamptz;

-- target_chats: add added_by audit
alter table public.target_chats
  add column if not exists added_by_user_id bigint,
  add column if not exists added_by_name text;
