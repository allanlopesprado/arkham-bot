import logging

from arkham_bot import logging_config


def test_mask_secrets_redacts_telegram_bot_url_and_secret_names(monkeypatch):
    monkeypatch.setattr(logging_config, "TELEGRAM_BOT_TOKEN", "123456:ABC_def-ghi")
    monkeypatch.setattr(logging_config, "SUPABASE_SERVICE_ROLE_KEY", "supabase-secret")
    monkeypatch.setattr(logging_config, "OPENAI_API_KEY", "openai-secret")

    message = (
        "POST https://api.telegram.org/bot123456:ABC_def-ghi/sendMessage "
        "TELEGRAM_BOT_TOKEN supabase-secret openai-secret"
    )

    masked = logging_config._mask_secrets(message)

    assert "123456:ABC_def-ghi" not in masked
    assert "TELEGRAM_BOT_TOKEN" not in masked
    assert "supabase-secret" not in masked
    assert "openai-secret" not in masked
    assert "https://api.telegram.org/bot[REDACTED]/sendMessage" in masked


def test_production_logging_reduces_noisy_http_and_telegram_loggers(monkeypatch):
    monkeypatch.setattr(logging_config, "ENVIRONMENT", "production")

    for logger_name in logging_config.SENSITIVE_LOGGER_NAMES:
        logger = logging.getLogger(logger_name)
        monkeypatch.setattr(logger, "level", logging.NOTSET)

    logging_config._configure_library_loggers()

    for logger_name in logging_config.SENSITIVE_LOGGER_NAMES:
        assert logging.getLogger(logger_name).level == logging.WARNING
