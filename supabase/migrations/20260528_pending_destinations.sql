-- Pending destinations: groups/channels where the bot was added but not yet confirmed
CREATE TABLE IF NOT EXISTS pending_destinations (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  chat_id     text NOT NULL UNIQUE,
  chat_title  text NOT NULL DEFAULT '',
  chat_type   text NOT NULL DEFAULT 'group',
  chat_username text,
  added_at    timestamptz NOT NULL DEFAULT now(),
  status      text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'dismissed'))
);

ALTER TABLE pending_destinations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "service_role_all" ON pending_destinations
  USING (true) WITH CHECK (true);
