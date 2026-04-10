import os
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env", override=True)
BOT_TOKEN = (os.getenv("TELEGRAM_TOKEN") or "").strip()
TEAM_ID = os.getenv("TEAM_ID")

if not BOT_TOKEN:
    raise RuntimeError("КРИТИЧЕСКАЯ ОШИБКА: TELEGRAM_TOKEN не задан в .env")
