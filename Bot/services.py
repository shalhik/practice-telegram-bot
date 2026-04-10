import asyncio
from typing import Optional

from aiogram import Bot, types
from aiogram.exceptions import TelegramNetworkError, TelegramRetryAfter
from .config import BOT_TOKEN
from database import async_session
from models import Subscription, WebhookConfig

from sqlalchemy import select, delete, update
from sqlalchemy.exc import IntegrityError
from clickup_client import (
    get_spaces,
    get_space_lists,
    get_lists,
    get_task_details,
    create_webhook,
)
from config import WEBHOOK_URL, CLICKUP_TEAM_ID


async def get_team_id_from_db_or_env() -> str | None:
    async with async_session() as session:
        result = await session.execute(select(WebhookConfig))
        cfg = result.scalar_one_or_none()
        if cfg and cfg.team_id:
            return cfg.team_id
    return CLICKUP_TEAM_ID


async def subscribe(chat_id: int, list_id: str) -> str:
    async with async_session() as session:
        query = select(Subscription).where(
            Subscription.tg_chat_id == chat_id,
            Subscription.clickup_list_id == list_id,
        )
        result = await session.execute(query)
        if result.scalar_one_or_none():
            return "Вы уже подписаны на этот список."

        new_sub = Subscription(
            tg_chat_id=chat_id,
            clickup_list_id=list_id,
            is_active=True,
        )
        session.add(new_sub)
        try:
            await session.commit()
            return "Подписка успешно оформлена!"
        except IntegrityError:
            await session.rollback()
            return "Вы уже подписаны на этот список."


async def unsubscribe(chat_id: int, list_id: str) -> str:
    async with async_session() as session:
        await session.execute(
            delete(Subscription).where(
                Subscription.tg_chat_id == chat_id,
                Subscription.clickup_list_id == list_id,
            )
        )
        await session.commit()
        return "Вы отписались от списка."


async def set_chat_enabled(chat_id: int, enabled: bool):
    async with async_session() as session:
        await session.execute(
            update(Subscription)
            .where(Subscription.tg_chat_id == chat_id)
            .values(is_active=enabled)
        )
        await session.commit()


async def get_user_subscriptions(chat_id: int) -> list[str]:
    async with async_session() as session:
        result = await session.execute(
            select(Subscription.clickup_list_id).where(
                Subscription.tg_chat_id == chat_id
            )
        )
        return [row for row in result.scalars().all()]


async def send_notification(chat_id: int, text: str, task_url: Optional[str] = None):
    bot = Bot(token=BOT_TOKEN)
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


async def get_clickup_spaces() -> list[dict]:
    team_id = await get_team_id_from_db_or_env()
    if not team_id:
        return []
    return await get_spaces(team_id)


async def get_clickup_lists(space_id: str) -> list[dict]:
    return await get_space_lists(space_id)


async def get_all_clickup_lists() -> list[dict]:
    team_id = await get_team_id_from_db_or_env()
    if not team_id:
        return []
    return await get_lists(team_id)


async def save_webhook_config(
    webhook_id: str,
    secret: str,
    url: str,
):
    async with async_session() as session:
        await session.execute(delete(WebhookConfig))
        new_cfg = WebhookConfig(
            webhook_id=webhook_id,
            secret=secret,
            url=url,
        )
        session.add(new_cfg)
        await session.commit()


async def get_webhook_config_from_db() -> WebhookConfig | None:
    async with async_session() as session:
        result = await session.execute(select(WebhookConfig))
        return result.scalar_one_or_none()

async def get_webhook_secret_from_db() -> str | None:
    cfg = await get_webhook_config_from_db()
    if not cfg:
        return None
    return cfg.secret


async def setup_team_webhook() -> dict:
    if not WEBHOOK_URL:
        return {"error": "В конфигурации (панель управления/env) не задан WEBHOOK_URL"}

    team_id = await get_team_id_from_db_or_env()
    if not team_id:
        return {"error": "TEAM_ID не задан ни в БД, ни в CLICKUP_TEAM_ID"}

    return await create_webhook(team_id, WEBHOOK_URL)


async def get_task_summary(task_id: str) -> str:
    task = await get_task_details(task_id)
    return format_task_summary(task) if task else f"Задача {task_id} не найдена."


def format_task_summary(task: dict) -> str:
    name = task.get("name", "Без названия")
    t_id = task.get("id", "—")
    status = (task.get("status") or {}).get("status", "—")
    priority = (task.get("priority") or {}).get("priority", "—")
    url = task.get("url", "(ссылка отсутствует)")
    assignees = ", ".join(
        [a.get("username", "?") for a in task.get("assignees", [])]
    ) or "не назначено"

    return (
        f"Задача: {name}\n"
        f"ID: {t_id}\n"
        f"Статус: {status}\n"
        f"Приоритет: {priority}\n"
        f"Исполнители: {assignees}\n"
        f"Ссылка: {url}"
    )