import asyncio
from typing import Optional

from aiogram import Bot, types
from aiogram.exceptions import TelegramNetworkError, TelegramRetryAfter
from sqlalchemy import select

from config import TELEGRAM_TOKEN
from database import async_session
from models import WebhookConfig


def format_task_summary(task: dict) -> str:
    name = task.get("name", "Без названия")
    task_id = task.get("id", "—")
    status = (task.get("status") or {}).get("status", "—")
    priority = (task.get("priority") or {}).get("priority", "—")
    url = task.get("url", "(ссылка отсутствует)")
    assignees = ", ".join(
        [assignee.get("username", "?") for assignee in task.get("assignees", [])]
    ) or "не назначено"

    return (
        f"Задача: {name}\n"
        f"ID: {task_id}\n"
        f"Статус: {status}\n"
        f"Приоритет: {priority}\n"
        f"Исполнители: {assignees}\n"
        f"Ссылка: {url}"
    )


async def get_webhook_config_from_db() -> WebhookConfig | None:
    async with async_session() as session:
        result = await session.execute(select(WebhookConfig))
        return result.scalar_one_or_none()


async def get_webhook_secret_from_db() -> str | None:
    cfg = await get_webhook_config_from_db()
    if not cfg:
        return None
    return cfg.secret


async def send_notification(chat_id: int, text: str, task_url: Optional[str] = None) -> None:
    bot = Bot(token=TELEGRAM_TOKEN)
    try:
        markup = None
        if task_url:
            markup = types.InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        types.InlineKeyboardButton(
                            text="Открыть в ClickUp",
                            url=task_url,
                        )
                    ]
                ]
            )

        attempts = 3
        for attempt in range(1, attempts + 1):
            try:
                await bot.send_message(chat_id=chat_id, text=text, reply_markup=markup)
                return
            except TelegramRetryAfter as exc:
                if attempt == attempts:
                    raise
                await asyncio.sleep(float(exc.retry_after))
            except TelegramNetworkError:
                if attempt == attempts:
                    raise
                await asyncio.sleep(min(2 ** (attempt - 1), 8))
    finally:
        await bot.session.close()