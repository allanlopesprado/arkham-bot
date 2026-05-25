# Arkham Bot

Bot Telegram para Arkham Horror: The Card Game, com backend Python, fila/estado no Supabase, Mini App administrativo em React/Vite e Worker Cloudflare para comandos autenticados.

## Documentacao

- [Documentacao tecnica](docs/TECHNICAL.md)
- [Operacao e deploy](docs/OPERATIONS.md)

## Componentes

- `main.py`: entrada do backend Python.
- `src/arkham_bot/`: pacote principal do bot.
- `scripts/`: healthcheck, sync ArkhamDB e utilitarios.
- `supabase/migrations/`: schema do banco.
- `worker/`: Cloudflare Worker usado pelo Mini App.
- `miniapp/`: Telegram Mini App em React/Vite.
- `.github/workflows/`: validacao e deploy Oracle.
- `deploy/systemd/`: unit file do servico Linux.

## Setup Local

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python -m pip install -e .
```

Crie `.env` a partir de `.env.example` quando for usar Telegram/Supabase reais.

## Comandos

```powershell
python main.py --help
python main.py healthcheck
python main.py healthcheck --strict
python main.py interactive
python scripts/sync_arkhamdb.py --dry-run
```

## Validacao

```powershell
python -m compileall -q .
python -m pytest -q
python main.py healthcheck --strict
```

Worker:

```powershell
cd worker
npm run dry-run
```

Mini App:

```powershell
cd miniapp
npm run build
npm run dry-run
```

## Seguranca

- Nunca commitar `.env` ou secrets reais.
- `SUPABASE_SERVICE_ROLE_KEY` fica somente no backend Python, Oracle e Worker.
- O Mini App nao deve receber secrets.
- Logs mascaram tokens do Telegram e secrets conhecidos.
- Deploy de producao acontece somente por workflow ou acao manual explicita.
