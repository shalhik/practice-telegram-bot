import os
import json
import hmac
import hashlib
from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from filters import is_important
from clickup_client import get_task_details
from database import init_db
from notifications import notify_subscribers

app = FastAPI(title="ClickUp to Telegram Integration")

def validate_clickup_signature(body: bytes, signature: str | None) -> bool:
    secret = os.getenv("CLICKUP_WEBHOOK_SECRET")
    if not secret:
        print("WARNING: CLICKUP_WEBHOOK_SECRET not set, webhook signature not validated.")
        return True

    if not signature:
        return False

    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


async def process_webhook_logic(task_id: str, event_id: str | None):
    """
    Основная цепочка действий:
    1. Получить задачу по ID
    2. Проверить на важность
    3. Отправить уведомление через Telegram если подходит
    """
    task = await get_task_details(task_id)
    if not task:
        print(f"Ошибка: Не удалось найти задачу {task_id}")
        return

    if is_important(task):
        print(f"🔥 ВАЖНО: Задача '{task.get('name')}' подходит под критерии.")
        await notify_subscribers(task, event_id)
    else:
        print(f"☁️ Пропускаем: Задача '{task.get('name')}' не важна.")

@app.post("/webhook/clickup")
async def handle_webhook(request: Request, background_tasks: BackgroundTasks):
    body = await request.body()
    signature = request.headers.get("X-ClickUp-Signature") or request.headers.get("X-Signature")
    if not validate_clickup_signature(body, signature):
        raise HTTPException(status_code=403, detail="Invalid webhook signature")

    data = json.loads(body)
    task_id = data.get("task_id") or data.get("task", {}).get("id")
    event = data.get("event")
    event_id = data.get("event_id") or data.get("id") or (f"{event}:{task_id}" if event and task_id else task_id)

    print(f"Получено событие {event} для задачи {task_id}")

    if task_id:
        background_tasks.add_task(process_webhook_logic, task_id, event_id)

    return {"status": "ok"}

@app.on_event("startup")
async def on_startup():
    await init_db()
    print("🚀 База данных готова к работе")