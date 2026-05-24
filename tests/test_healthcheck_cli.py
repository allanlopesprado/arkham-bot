import os
import subprocess
import sys


def _run(args):
    env = os.environ.copy()
    for key in ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"]:
        env.pop(key, None)
    return subprocess.run([sys.executable, "main.py", *args], cwd=os.getcwd(), env=env, text=True, capture_output=True)


def test_healthcheck_non_strict_allows_missing_env():
    result = _run(["healthcheck"])
    assert result.returncode == 0


def test_healthcheck_strict_fails_missing_env():
    result = _run(["healthcheck", "--strict"])
    assert result.returncode != 0
