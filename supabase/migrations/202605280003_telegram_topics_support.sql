-- PEND-009: Telegram Topics support
-- Replace UNIQUE(chat_id) with topic-aware unique indexes, allowing multiple
-- topics per group while keeping a single main-chat row.
--
-- NULL thread_id = main chat (no topic).
-- PostgreSQL UNIQUE constraints treat NULL values as distinct, so a composite
-- UNIQUE(chat_id, message_thread_id) would still allow duplicate main-chat rows.

-- Drop the old single-column unique constraint.
ALTER TABLE target_chats
  DROP CONSTRAINT IF EXISTS target_chats_chat_id_key;

-- Drop the previous composite constraint if this migration was applied before
-- the partial-index fix.
ALTER TABLE target_chats
  DROP CONSTRAINT IF EXISTS target_chats_chat_id_thread_key;

CREATE UNIQUE INDEX IF NOT EXISTS target_chats_unique_main_chat
  ON target_chats (chat_id)
  WHERE enabled = true AND message_thread_id IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS target_chats_unique_topic
  ON target_chats (chat_id, message_thread_id)
  WHERE enabled = true AND message_thread_id IS NOT NULL;
