# Local Validation

Run inside the project root after activating the virtual environment.

## Windows PowerShell

```powershell
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
python -m pip install -e .
python -m compileall -q .
python -m pytest -q
python main.py --help
python main.py healthcheck
python main.py healthcheck --strict
```

Without a real `.env`, strict healthcheck must fail. That is correct.

## Expected without .env

```txt
python main.py healthcheck          -> exit code 0 with warnings
python main.py healthcheck --strict -> exit code 1 with errors
python -m pytest -q                -> tests pass without network
```

## External validation still required

These require real credentials/infrastructure:

- Supabase migrations and REST access.
- Telegram bot token and target chat.
- Oracle systemd service.
- GitHub Actions deployment.
- Cloudflare Pages/Worker.
- OpenAI API if AI daily card is enabled.
- ArkhamDB OAuth if Collection/Deck authenticated features are enabled later.


## Atualização — compatibilidade Windows timezone

Foi adicionada a dependência `tzdata` para garantir que `ZoneInfo("America/Sao_Paulo")` funcione em Windows, onde a base IANA de fusos horários pode não estar disponível pelo sistema operacional.

Validação esperada:

```powershell
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
python -m compileall -q .
python -m pytest -q
python -c "from zoneinfo import ZoneInfo; print(ZoneInfo('America/Sao_Paulo'))"
```
