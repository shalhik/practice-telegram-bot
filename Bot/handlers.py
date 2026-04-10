from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command

from .services import (
    subscribe,
    unsubscribe,
    get_user_subscriptions,
    get_clickup_spaces,
    get_clickup_lists,
    get_all_clickup_lists,
    set_chat_enabled,
    get_task_summary,
)
from filters import is_important
from clickup_client import get_task_details,  get_list_tasks


router = Router()


@router.message(Command("start"))
async def start(msg: Message):
    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Мои подписки", callback_data="subscriptions")],
        ]
    )
    await msg.answer(
        "Бот для уведомлений ClickUp. Интеграция уже настроена на сервере. "
        "Выберите действие:",
        reply_markup=markup,
    )


@router.callback_query(F.data.startswith("space:"))
async def process_space(callback: CallbackQuery):
    space_id = callback.data.split(":", 1)[1]
    lists = await get_clickup_lists(space_id)
    if not lists:
        await callback.message.answer(
            "Не удалось получить списки внутри Space.\n\n"
            "Проверьте:\n"
            "1. API ключ имеет доступ к этому Space\n"
            "2. Space содержит списки\n"
            "\n Посмотрите логи бота для деталей ошибки."
        )
        await callback.answer()
        return

    buttons = [
        [InlineKeyboardButton(text=list_item["name"], callback_data=f"subscribe:{list_item['id']}")]
        for list_item in lists[:10]
    ]
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text("Выберите список для подписки:", reply_markup=markup)
    await callback.answer()


@router.callback_query(F.data.startswith("subscribe:"))
async def process_subscribe(callback: CallbackQuery):
    list_id = callback.data.split(":", 1)[1]
    chat_id = callback.message.chat.id
    result = await subscribe(chat_id, list_id)

    await callback.message.answer(result)
    await callback.answer()


@router.callback_query(F.data == "subscriptions")
async def show_subscriptions(callback: CallbackQuery):
    chat_id = callback.message.chat.id
    subscriptions = await get_user_subscriptions(chat_id)
    if not subscriptions:
        await callback.message.answer("У вас нет активных подписок.")
        await callback.answer()
        return

    lists = await get_all_clickup_lists()
    list_names = {lst["id"]: lst["name"] for lst in lists}

    buttons = [
        [
            InlineKeyboardButton(
                text=f"{list_names.get(sub, sub)} (отписаться)",
                callback_data=f"unsubscribe:{sub}",
            )
        ]
        for sub in subscriptions
    ]
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.edit_text("Ваши подписки:", reply_markup=markup)
    await callback.answer()


@router.callback_query(F.data.startswith("unsubscribe:"))
async def process_unsubscribe(callback: CallbackQuery):
    list_id = callback.data.split(":", 1)[1]
    chat_id = callback.message.chat.id
    result = await unsubscribe(chat_id, list_id)

    await callback.message.answer(result)
    await callback.answer()


@router.message(Command("connect"))
async def connect_command(msg: Message):
    spaces = await get_clickup_spaces()
    if not spaces:
        await msg.answer(
            "Не удалось получить пространства ClickUp.\n\n"
            "Проверьте:\n"
            "1. Интеграция ClickUp настроена в серверной конфигурации\n"
            "2. У сервисного аккаунта есть доступ к нужным Space/List\n"
            "\n Посмотрите логи бота для деталей ошибки."
        )
        return

    buttons = [
        [InlineKeyboardButton(text=space["name"], callback_data=f"space:{space['id']}")]
        for space in spaces[:10]
    ]
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    await msg.answer("Выберите Space ClickUp:", reply_markup=markup)


@router.message(Command("watch"))
async def watch(msg: Message):
    await set_chat_enabled(msg.chat.id, True)
    await msg.answer("Уведомления включены для этого чата.")


@router.message(Command("unwatch"))
async def unwatch(msg: Message):
    await set_chat_enabled(msg.chat.id, False)
    await msg.answer("Уведомления выключены для этого чата.")


@router.message(Command("important"))
async def important(msg: Message):
    list_ids = await get_user_subscriptions(msg.chat.id)
    if not list_ids:
        await msg.answer("У вас нет активных подписок.")
        return

    all_important_tasks = []
    for l_id in list_ids:
        tasks = await get_list_tasks(l_id)
        for t in tasks:
            if is_important(t):
                all_important_tasks.append(t)

    if not all_important_tasks:
        await msg.answer("В ваших списках сейчас нет задач, подходящих под критерии 'важных'.")
        return

    buttons = []
    for t in all_important_tasks[:10]:
        name = t.get("name", "Без названия")
        task_id = t.get("id")
        if not task_id:
            continue
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"{name} ({task_id})",
                    callback_data=f"taskdetail:{task_id}",
                )
            ]
        )

    markup = InlineKeyboardMarkup(inline_keyboard=buttons)

    await msg.answer(
        "Текущие важные задачи (нажмите, чтобы посмотреть детали):",
        reply_markup=markup,
    )


@router.callback_query(F.data.startswith("taskdetail:"))
async def show_task_detail(callback: CallbackQuery):
    task_id = callback.data.split(":", 1)[1]

    summary = await get_task_summary(task_id)

    task = await get_task_details(task_id)
    task_url = task.get("url") if task else None

    copy_id_button = InlineKeyboardButton(
        text="Показать ID",
        callback_data=f"copyid:{task_id}",
    )

    open_url_button = InlineKeyboardButton(
        text="Открыть в ClickUp",
        url=task_url or f"https://app.clickup.com/t/{task_id}",
    )

    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [copy_id_button],
            [open_url_button],
        ]
    )

    await callback.message.edit_text(summary, reply_markup=markup)
    await callback.answer()


@router.callback_query(F.data.startswith("copyid:"))
async def copy_task_id(callback: CallbackQuery):
    task_id = callback.data.split(":", 1)[1]
    await callback.answer("ID задачи", show_alert=False)
    await callback.message.answer(f"ID задачи: `{task_id}`", parse_mode="Markdown")


@router.message(Command("task"))
async def cmd_task(msg: Message):
    parts = msg.text.split(maxsplit=1)
    if len(parts) < 2:
        await msg.answer("Использование: /task <task_id>")
        return
    task_id = parts[1]
    summary = await get_task_summary(task_id)
    await msg.answer(summary)
