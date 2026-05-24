-- Safe public read policies for non-sensitive ArkhamDB cache tables.
-- These policies allow the future Mini App to read public card/reference data with anon key.
-- No public write policies are created here.

do $$
begin
  if not exists (select 1 from pg_policies where schemaname='public' and tablename='arkham_cards' and policyname='Public read arkham cards') then
    create policy "Public read arkham cards" on public.arkham_cards for select to anon, authenticated using (true);
  end if;
  if not exists (select 1 from pg_policies where schemaname='public' and tablename='arkham_packs' and policyname='Public read arkham packs') then
    create policy "Public read arkham packs" on public.arkham_packs for select to anon, authenticated using (true);
  end if;
  if not exists (select 1 from pg_policies where schemaname='public' and tablename='arkham_factions' and policyname='Public read arkham factions') then
    create policy "Public read arkham factions" on public.arkham_factions for select to anon, authenticated using (true);
  end if;
  if not exists (select 1 from pg_policies where schemaname='public' and tablename='arkham_faq' and policyname='Public read arkham faq') then
    create policy "Public read arkham faq" on public.arkham_faq for select to anon, authenticated using (true);
  end if;
  if not exists (select 1 from pg_policies where schemaname='public' and tablename='arkham_taboos' and policyname='Public read arkham taboos') then
    create policy "Public read arkham taboos" on public.arkham_taboos for select to anon, authenticated using (true);
  end if;
  if not exists (select 1 from pg_policies where schemaname='public' and tablename='arkham_decklists_cache' and policyname='Public read arkham decklists cache') then
    create policy "Public read arkham decklists cache" on public.arkham_decklists_cache for select to anon, authenticated using (true);
  end if;
end $$;

-- Sensitive/admin tables intentionally have RLS enabled without anon policies:
-- bot_settings, bot_commands, bot_admins, target_chats, bot_posted_cards,
-- bot_posting_history, bot_errors, audit_logs.
-- Backend Python/Oracle uses service_role and bypasses RLS.
-- Mini App write paths must go through a validated backend/Worker or future authenticated policies.
