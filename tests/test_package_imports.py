
def test_core_modules_import():
    import arkham_bot.clients.arkhamdb_client  # noqa: F401
    import arkham_bot.services.daily_card  # noqa: F401
    import arkham_bot.services.scheduler  # noqa: F401
    import arkham_bot.handlers.telegram_handlers  # noqa: F401
    import arkham_bot.core.supabase_client  # noqa: F401
