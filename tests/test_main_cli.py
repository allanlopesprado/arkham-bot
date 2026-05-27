import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_main(*args: str):
    env = os.environ.copy()
    for key in ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"]:
        env.pop(key, None)
    env["PYTHON_DOTENV_DISABLED"] = "1"
    return subprocess.run([sys.executable, "main.py", *args], cwd=ROOT, env=env, text=True, capture_output=True)


def test_main_help_exits_successfully():
    result = run_main("--help")
    assert result.returncode == 0
    assert "python main.py interactive" in result.stdout


