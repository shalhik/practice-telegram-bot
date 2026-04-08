from fastapi import FastAPI, Request, BackgroundTasks
from filters import is_important
from clickup_client import get_task_details

app = FastAPI(title="ClickUp to Telegram Integration")

async def process_webhook_logic(task_id: str):
    """
    Основная цепочка действий:
    1. Получить задачу по ID
    2. Проверить на важность
    3. (В будущем) Передать напарнику для отправки в Telegram
    """
    # Шаг 1: Идем в ClickUp за деталями
    task = await get_task_details(task_id)
    if not task:
        print(f"Ошибка: Не удалось найти задачу {task_id}")
        return

    # Шаг 2: Проверяем фильтром из ТЗ
    if is_important(task):
        print(f"🔥 ВАЖНО: Задача '{task.get('name')}' подходит под критерии.")
        # РУБЕЖ 4: Тут мы позовем функцию твоего напарника
        # await notify_teammate(task)
    else:
        print(f"☁️ Пропускаем: Задача '{task.get('name')}' не важна.")

@app.post("/webhook/clickup")
async def handle_webhook(request: Request, background_tasks: BackgroundTasks):
    # ClickUp присылает JSON, в котором есть task_id
    data = await request.json()
    task_id = data.get("task_id")
    event = data.get("event")

    print(f"Получено событие {event} для задачи {task_id}")

    if task_id:
        # Запускаем обработку в фоне, чтобы сразу вернуть 'ok'
        background_tasks.add_task(process_webhook_logic, task_id)

    return {"status": "ok"}