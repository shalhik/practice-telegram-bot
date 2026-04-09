from aiogram import Bot
from .config import BOT_TOKEN, TEAM_ID
from database import async_session
from models import Subscription, TelegramChat
from filters import is_important
from sqlalchemy import select, delete
from clickup_client import get_spaces, get_space_lists, get_lists, get_list_tasks, get_task_details

async def send_notification(chat_id: int, text: str):
    async with Bot(token=BOT_TOKEN) as bot:
        await bot.send_message(chat_id=chat_id, text=text)

async def get_clickup_spaces() -> list[dict]:
    """Получает Spaces ClickUp для выбора подключения."""
    return await get_spaces(TEAM_ID)

async def get_clickup_lists(space_id: str) -> list[dict]:
    """Получает списки ClickUp внутри выбранного Space."""
    return await get_space_lists(space_id)

async def get_all_clickup_lists() -> list[dict]:
    """Получает все списки ClickUp в команде."""
    return await get_lists(TEAM_ID)

async def ensure_chat(chat_id: int) -> TelegramChat:
    async with async_session() as session:
        stmt = select(TelegramChat).where(TelegramChat.tg_chat_id == chat_id)
        result = await session.execute(stmt)
        chat = result.scalar_one_or_none()
        if not chat:
            chat = TelegramChat(tg_chat_id=chat_id, enabled=True)
            session.add(chat)
            await session.commit()
            await session.refresh(chat)
        return chat

async def set_chat_enabled(chat_id: int, enabled: bool) -> str:
    async with async_session() as session:
        stmt = select(TelegramChat).where(TelegramChat.tg_chat_id == chat_id)
        result = await session.execute(stmt)
        chat = result.scalar_one_or_none()
        if not chat:
            chat = TelegramChat(tg_chat_id=chat_id, enabled=enabled)
            session.add(chat)
        else:
            chat.enabled = enabled
            session.add(chat)
        await session.commit()
        return "ok"

async def subscribe(chat_id: int, list_id: str) -> str:
    """Подписывает пользователя на список ClickUp."""
    await ensure_chat(chat_id)

    async with async_session() as session:
        stmt = select(Subscription).where(
            Subscription.tg_chat_id == chat_id,
            Subscription.clickup_list_id == list_id,
        )
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            return "Вы уже подписаны на этот список."

        subscription = Subscription(tg_chat_id=chat_id, clickup_list_id=list_id)
        session.add(subscription)
        await session.commit()
        return "Подписка оформлена!"

async def unsubscribe(chat_id: int, list_id: str) -> str:
    """Отписывает пользователя от списка ClickUp."""
    async with async_session() as session:
        stmt = delete(Subscription).where(
            Subscription.tg_chat_id == chat_id,
            Subscription.clickup_list_id == list_id,
        )
        result = await session.execute(stmt)
        await session.commit()
        if result.rowcount > 0:
            return "Подписка отменена."
        return "Вы не были подписаны на этот список."

async def get_user_subscriptions(chat_id: int) -> list[str]:
    """Получает список ID списков, на которые подписан пользователь."""
    async with async_session() as session:
        stmt = select(Subscription.clickup_list_id).where(Subscription.tg_chat_id == chat_id)
        result = await session.execute(stmt)
        return [row[0] for row in result.fetchall()]

async def get_important_tasks(chat_id: int) -> list[dict]:
    """Возвращает важные задачи для всех подписок чата."""
    list_ids = await get_user_subscriptions(chat_id)
    if not list_ids:
        return []

    tasks: list[dict] = []
    for list_id in list_ids:
        raw_tasks = await get_list_tasks(list_id)
        for task in raw_tasks:
            if is_important(task):
                tasks.append(task)
    return tasks

async def get_task_summary(task_id: str) -> str:
    task = await get_task_details(task_id)
    if not task:
        return f"Задача {task_id} не найдена."

    name = task.get("name", "Без названия")
    status = (task.get("status") or {}).get("status", "—")
    priority = (task.get("priority") or {}).get("priority", "—")
    url = task.get("url", "(ссылка отсутствует)")
    assignees = ", ".join([a.get("username", "?") for a in task.get("assignees", [])]) or "не назначено"
    due_date = task.get("due_date") or "не задан"

    return (
        f"Задача: {name}\n"
        f"ID: {task_id}\n"
        f"Статус: {status}\n"
        f"Приоритет: {priority}\n"
        f"Исполнитель: {assignees}\n"
        f"Дедлайн: {due_date}\n"
        f"Ссылка: {url}"
    )
