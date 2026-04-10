from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from .services import (
    subscribe,
    unsubscribe,
    get_user_subscriptions,
    get_clickup_spaces,
    get_clickup_lists,
    get_all_clickup_lists,
    set_chat_enabled,
    get_task_summary,
    get_list_tasks
)
from filters import is_important
from register_webhook import register
from clickup_client import get_task_details

router = Router()


class SetupStates(StatesGroup):
    waiting_for_api_key = State()
    waiting_for_team_id = State()


@router.message(Command("start"))
async def start(msg: Message):
    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Мои подписки", callback_data="subscriptions")],
            [InlineKeyboardButton(text="Настроить Webhook", callback_data="setup_webhook")],
        ]
    )
    await msg.answer("Бот для уведомлений ClickUp. Выберите действие:", reply_markup=markup)


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
            "1. API ключ ClickUp установлен (через /setup_webhook)\n"
            "2. TEAM_ID корректный\n"
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


@router.message(Command("setup_webhook"))
@router.callback_query(F.data == "setup_webhook")
async def handle_setup_webhook(event: Message | CallbackQuery, state: FSMContext):
    target = event if isinstance(event, Message) else event.message
    await target.answer("Шаг 1/2: Введите ваш ClickUp API Key (Personal Token):")
    await state.set_state(SetupStates.waiting_for_api_key)
    if isinstance(event, CallbackQuery):
        await event.answer()


@router.message(SetupStates.waiting_for_api_key)
async def process_api_key(msg: Message, state: FSMContext):
    await state.update_data(api_key=msg.text.strip())
    await msg.answer("Шаг 2/2: Введите ваш ClickUp Team ID (можно найти в URL вашего Workspace):")
    await state.set_state(SetupStates.waiting_for_team_id)


@router.message(SetupStates.waiting_for_team_id)
async def process_team_id(msg: Message, state: FSMContext):
    data = await state.get_data()
    api_key = data["api_key"]
    team_id = msg.text.strip()

    await msg.answer("Проверка данных и регистрация вебхука...")

    res = await register(override_api_key=api_key, override_team_id=team_id)

    error = res.get("error") if isinstance(res, dict) else None
    if error and "Webhook configuration already exists" not in str(error):
        await msg.answer(
            f"Ошибка регистрации: {error}\n\n"
            "Попробуйте снова: /setup_webhook"
        )
    else:
        webhook_id = res.get("webhook", {}).get("id") if isinstance(res, dict) else None
        text = (
            "Интеграция настроена.\n\n"
            "ClickUp сообщает, что вебхук уже существует для этого URL "
            "или был успешно создан.\n\n"
            f"Webhook ID: `{webhook_id or 'неизвестен'}`\n"
            "Теперь вы можете использовать /connect для подписки на списки."
        )
        await msg.answer(text, parse_mode="Markdown")

    await state.clear()