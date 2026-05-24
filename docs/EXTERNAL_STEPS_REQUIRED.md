# External Steps Required

These steps cannot be completed inside this local code package because they require real credentials, remote services, or infrastructure access.

## Supabase

1. Create a project if it does not already exist.
2. Set local env vars only in `.env`, never in Git:

```env
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
```

3. Apply migrations only after review:

```bash
supabase db push
```

4. Run sync dry-run first:

```bash
python scripts/sync_arkhamdb.py --dry-run
```

5. Run real sync:

```bash
python scripts/sync_arkhamdb.py
```

## Telegram

1. Revoke any token previously exposed in chat.
2. Create/set a new token in `.env`:

```env
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
ADMIN_TELEGRAM_USER_IDS=
```

3. Test:

```bash
python main.py healthcheck --strict
python main.py interactive
```

## Oracle/systemd

Copy `deploy/systemd/arkham-bot.service` to `/etc/systemd/system/arkham-bot.service`, adjust paths, then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable arkham-bot
sudo systemctl start arkham-bot
journalctl -u arkham-bot -f
```

## GitHub Actions

Required repository secrets:

```txt
ORACLE_HOST
ORACLE_USER
ORACLE_SSH_KEY
ORACLE_PROJECT_PATH
```

Secrets that should remain on Oracle `.env`, not in GitHub Actions unless a workflow strictly needs them:

```txt
TELEGRAM_BOT_TOKEN
SUPABASE_SERVICE_ROLE_KEY
OPENAI_API_KEY
```

## Cloudflare Pages / Mini App

1. Deploy `miniapp/` to Cloudflare Pages.
2. Use public env vars only:

```txt
VITE_SUPABASE_URL
VITE_SUPABASE_ANON_KEY
VITE_COMMANDS_API_URL optional Worker URL
```

3. Service role must never appear in the frontend bundle.

## Cloudflare Worker optional

The Worker scaffold validates Telegram Mini App initData and can insert `bot_commands` using secrets stored in Cloudflare, not in frontend code.
