-- Add source column to track manual vs scheduled posts
ALTER TABLE public.bot_posting_history
  ADD COLUMN IF NOT EXISTS source text DEFAULT 'manual';

COMMENT ON COLUMN public.bot_posting_history.source IS 'manual = posted via mini app or command, scheduled = posted by scheduler';
