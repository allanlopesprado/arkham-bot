import logging

from .config import ADMIN_TELEGRAM_USER_IDS
from ..repositories.admins_repo import get_admin

logger = logging.getLogger(__name__)


def is_admin_user(telegram_user_id: int | None) -> bool:
    if telegram_user_id is None:
        return False
    if telegram_user_id in ADMIN_TELEGRAM_USER_IDS:
        return True
    try:
        admin = get_admin(telegram_user_id)
        return bool(admin and admin.get("enabled") is not False and admin.get("role") in {"owner", "admin"})
    except Exception as exc:
        logger.warning("admin_lookup_failed: %s", exc)
        return False


def admin_source(telegram_user_id: int | None) -> str:
    if telegram_user_id is None:
        return "none"
    if telegram_user_id in ADMIN_TELEGRAM_USER_IDS:
        return "env"
    try:
        admin = get_admin(telegram_user_id)
        return admin.get("role", "supabase") if admin else "none"
    except Exception:
        return "none"
