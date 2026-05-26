-- Fix arkham_cards schema to match ArkhamDB JSON structure exactly
-- Previous schema had spoiler_level (text) but code sent spoiler (boolean) -- mismatch
-- Add all missing ArkhamDB fields as indexed columns; raw jsonb remains the source of truth

-- Replace spoiler_level (text, never properly set) with spoiler (boolean)
ALTER TABLE public.arkham_cards
  ADD COLUMN IF NOT EXISTS spoiler boolean not null default false;

ALTER TABLE public.arkham_cards
  DROP COLUMN IF EXISTS spoiler_level;

-- Add missing ArkhamDB card fields
ALTER TABLE public.arkham_cards
  ADD COLUMN IF NOT EXISTS double_sided boolean,
  ADD COLUMN IF NOT EXISTS back_text text,
  ADD COLUMN IF NOT EXISTS back_name text,
  ADD COLUMN IF NOT EXISTS back_flavor text,
  ADD COLUMN IF NOT EXISTS skill_wild integer;

-- Index spoiler for daily card selection filtering
CREATE INDEX IF NOT EXISTS idx_arkham_cards_spoiler ON public.arkham_cards(spoiler);
CREATE INDEX IF NOT EXISTS idx_arkham_cards_double_sided ON public.arkham_cards(double_sided);
