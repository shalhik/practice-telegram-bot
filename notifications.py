from aiogram import Bot
from Bot.config import BOT_TOKEN
from database import async_session
from models import Subscription, SentEvent, TelegramChat
from sqlalchemy import select


def get_clickup_list_id(task: dict) -> str:
    """Извлекает ID списка ClickUp из данных задачи."""
    list_data = task.get("list") or task.get("task_list") or {}
    if isinstance(list_data, dict):
        return str(list_data.get("id") or list_data.get("list_id") or "")
    return str(list_data or "")


def build_task_message(task: dict) -> str:
    """Формирует текст уведомления для Telegram."""
    name = task.get("name", "Без названия")
    task_id = task.get("id", "")
    url = task.get("url", "(ссылка отсутствует)")
    priority = (task.get("priority") or {}).get("priority", "—")
    return (
        f"Важная задача: {name}\n"
        f"ID: {task_id}\n"
        f"Приоритет: {priority}\n"
        f"Ссылка: {url}"
    )


async def notify_subscribers(task: dict, event_id: str | None = None):
    """Отправляет уведомления подписчикам списка ClickUp и предотвращает дубли."""
    list_id = get_clickup_list_id(task)
    if not list_id:
        print("Не удалось определить список ClickUp для уведомлений.")
        return

    async with async_session() as session:
        if event_id:
            existing = await session.get(SentEvent, event_id)
            if existing:
                print(f"Событие {event_id} уже было отправлено ранее.")
                return

        stmt = (
            select(Subscription)
            .join(TelegramChat, TelegramChat.tg_chat_id == Subscription.tg_chat_id)
            .where(
                Subscription.clickup_list_id == list_id,
                TelegramChat.enabled == True,
            )
        )
        result = await session.execute(stmt)
        subscribers = result.scalars().all()

        if not subscribers:
            print(f"Нет активных подписчиков для списка {list_id}. Уведомление не отправлено.")
            return

        message_text = build_task_message(task)
        async with Bot(token=BOT_TOKEN) as bot:
            for subscriber in subscribers:
                try:
                    await bot.send_message(subscriber.tg_chat_id, message_text)
                    print(f"Уведомление отправлено в Telegram: chat_id={subscriber.tg_chat_id}")
                except Exception as exc:
                    print(f"Ошибка отправки уведомления chat_id={subscriber.tg_chat_id}: {exc}")

        if event_id:
            session.add(SentEvent(event_id=event_id))
            await session.commit()