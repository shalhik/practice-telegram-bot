import os
from dotenv import load_dotenv

load_dotenv(override=True)

def get_env(name: str, required: bool = True) -> str:
    raw = os.getenv(name)
    value = raw.strip() if raw else ""
    if required and not value:
        # Fail-fast: падаем сразу, если нет важной настройки
        raise RuntimeError(f"КРИТИЧЕСКАЯ ОШИБКА: Переменная окружения '{name}' не задана!")
    return value

# Конфигурация ClickUp
CLICKUP_API_KEY = get_env("CLICKUP_API_KEY", required=False)
CLICKUP_TEAM_ID = get_env("CLICKUP_TEAM_ID", required=False)
CLICKUP_WEBHOOK_SECRET = get_env("CLICKUP_WEBHOOK_SECRET", required=False)

# Конфигурация Базы данных
DATABASE_URL = get_env("DATABASE_URL")

# Конфигурация Webhook (для скриптов регистрации)
WEBHOOK_URL = get_env("WEBHOOK_URL", required=False)

# Telegram (на будущее для напарника)
TELEGRAM_TOKEN = get_env("TELEGRAM_TOKEN", required=True)