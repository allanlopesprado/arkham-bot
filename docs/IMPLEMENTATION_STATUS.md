# Implementation Status — Full Local Package

This package contains the maximum implementation that can be completed locally without real credentials or remote service access.

## Implemented locally

- Modular Python bot under `src/arkham_bot/`.
- `main.py` entrypoint and legacy `arkham_daily_card_bot.py` wrapper.
- Telegram long polling setup.
- Daily card posting flow.
- Internal scheduler at 08:00 America/Sao_Paulo.
- Scheduler-safe daily posting result contract.
- Last pinned card local state and unpin/pin flow.
- Local storage under `data/` and logs under `logs/`.
- ArkhamDB client and payload validators.
- ArkhamDB resource matrix: Card, Pack, Faction, Faq, Taboo, Decklist public; Collection and Deck OAuth future.
- Supabase migration baseline plus public-read policies for non-sensitive ArkhamDB cache tables.
- Supabase REST client and repositories.
- `bot_commands` worker with retry, result, next_attempt_at and admin validation.
- Admin helpers and admin Telegram commands.
- Public commands: `/help`, `/menu`, `/status`, `/card`, `/today`, `/random`, `/faq`, `/taboo`, `/decklist`, `/search`, `/pack`, `/faction`, `/type`, `/xp`.
- Rate limiter with admin bypass.
- ArkhamDB sync script with dry-run and optional FAQ sync.
- Optional AI daily card selector scaffold with strict JSON validation.
- ArkhamDB OAuth helper primitives for future Collection/Deck authenticated phase.
- Healthcheck CLI with strict/non-strict behavior.
- Unit tests for model validation, healthcheck behavior, CLI help, rate limiting, scheduler pure logic, formatters, repository helpers and package imports.
- Systemd service template.
- GitHub Actions workflow with tests, strict remote healthcheck and rollback attempt.
- Backup script.
- Mini App scaffold with Supabase anon read and Worker command enqueue flow.
- Cloudflare Worker scaffold for Telegram initData validation and bot_commands insertion.

## Validated locally

```bash
python -m compileall -q .
python -m pytest -q
python main.py --help
python main.py healthcheck
python main.py healthcheck --strict
```

Current local automated test count: **21 passed**.

Expected local result without `.env` secrets:

- `python main.py healthcheck` exits `0` with warnings.
- `python main.py healthcheck --strict` exits non-zero with errors.

## Not executable locally without credentials/infrastructure

- Apply Supabase migrations to remote project.
- Test Supabase REST connection with service role.
- Run real Telegram bot against a group/channel.
- Pin/unpin real Telegram messages.
- Deploy systemd on Oracle.
- Run GitHub Actions against Oracle.
- Deploy Cloudflare Pages.
- Deploy Cloudflare Worker.
- Test OpenAI API call.
- Complete real ArkhamDB OAuth callback flow.

## Next required external sequence

1. Create `.env` from `.env.example` with real secrets.
2. Apply Supabase migrations.
3. Run `python scripts/sync_arkhamdb.py --dry-run`.
4. Run `python scripts/sync_arkhamdb.py`.
5. Run `python main.py healthcheck --strict`.
6. Run `python main.py interactive` locally.
7. Move to Oracle and configure systemd.
8. Configure GitHub Actions secrets.
9. Deploy Mini App to Cloudflare Pages.
10. Deploy Worker only if using Mini App command enqueue.


## Dependency fix — tzdata

Status: aplicado.

Motivo: testes no Windows falharam em `ZoneInfo("America/Sao_Paulo")` por ausência do pacote `tzdata`. O projeto agora declara `tzdata` como dependência de runtime em `requirements.txt` e `pyproject.toml`.

Validação esperada: `python -m pytest -q` deve passar também no Windows.
