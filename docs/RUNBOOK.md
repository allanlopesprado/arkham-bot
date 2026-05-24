# Arkham Bot Runbook

## Local Windows PowerShell

```powershell
cd C:\Users\allan\Desktop\arkham-bot
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install -e .
python -m compileall -q .
python -m pytest -q
python main.py --help
python main.py healthcheck
python main.py healthcheck --strict
```

## Local Linux/Oracle

```bash
cd /opt/arkham_bot
python3 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install -e .
python -m compileall -q .
python -m pytest -q
python main.py healthcheck --strict
python main.py interactive
```

## Supabase

```bash
supabase db push
python scripts/sync_arkhamdb.py --dry-run
python scripts/sync_arkhamdb.py
```

## Systemd

```bash
sudo cp deploy/systemd/arkham-bot.service /etc/systemd/system/arkham-bot.service
sudo systemctl daemon-reload
sudo systemctl enable arkham-bot
sudo systemctl start arkham-bot
journalctl -u arkham-bot -f
```
