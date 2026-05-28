-- PEND-009: Telegram Topics support
-- Replace UNIQUE(chat_id) with UNIQUE(chat_id, message_thread_id)
-- allowing multiple topics per group.
--
-- NULL thread_id = main chat (no topic), treated as distinct per (chat_id, NULL) pair.
-- Postgres UNIQUE treats two NULLs as not equal, so (chat_id, NULL) is always unique —
-- that's actually the correct behavior: one "main chat" entry per chat_id.

-- Drop the old single-column unique constraint
ALTER TABLE target_chats
  DROP CONSTRAINT IF EXISTS target_chats_chat_id_key;

-- Add composite unique constraint
ALTER TABLE target_chats
  ADD CONSTRAINT target_chats_chat_id_thread_key
  UNIQUE (chat_id, message_thread_id);
