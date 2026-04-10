import os
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
TEAM_ID = os.getenv("TEAM_ID")
