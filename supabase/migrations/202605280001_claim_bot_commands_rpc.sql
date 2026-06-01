-- 4.10: Atomic command claiming with FOR UPDATE SKIP LOCKED
-- Prevents two bot instances from executing the same command simultaneously.
--
-- Usage: SELECT * FROM claim_bot_commands(10);

CREATE OR REPLACE FUNCTION claim_bot_commands(batch_size integer DEFAULT 10)
RETURNS SETOF bot_commands
LANGUAGE sql
AS $$
  UPDATE bot_commands
  SET
    status = 'processing',
    attempt_count = attempt_count + 1,
    updated_at = now()
  WHERE id IN (
    SELECT id
    FROM bot_commands
    WHERE status IN ('pending', 'retrying')
    ORDER BY created_at ASC
    FOR UPDATE SKIP LOCKED
    LIMIT batch_size
  )
  RETURNING *;
$$;
