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
    print(f"⚙️ Начало обработки webhook: task_id={task_id}, event_id={event_id}")
    
    task = await get_task_details(task_id)
    if not task:
        print(f"❌ Ошибка: Не удалось найти задачу {task_id}")
        return

    task_name = task.get('name', 'Без названия')
    print(f"📌 Получена задача: {task_name}")

    if is_important(task):
        print(f"🔥 ВАЖНО: Задача '{task_name}' проходит под фильтры - отправляем уведомления")
        await notify_subscribers(task, event_id)
    else:
        print(f"☁️ Пропускаем: Задача '{task_name}' не важна")

@app.post("/webhook/clickup")
async def handle_webhook(request: Request, background_tasks: BackgroundTasks):
    body = await request.body()
    signature = request.headers.get("X-ClickUp-Signature") or request.headers.get("X-Signature")
    
    print(f"📥 Получен webhook запрос, размер: {len(body)} байт")
    
    if not validate_clickup_signature(body, signature):
        print("❌ Ошибка валидации подписи webhook")
        raise HTTPException(status_code=403, detail="Invalid webhook signature")

    try:
        data = json.loads(body)
        print(f"📋 Payload webhook: {json.dumps(data, indent=2, ensure_ascii=False)[:500]}...")
    except json.JSONDecodeError as e:
        print(f"❌ Ошибка парсинга JSON: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # Попытка получить task_id из разных мест в структуре
    task_id = data.get("task", {}).get("id") or data.get("task_id")
    event = data.get("event")
    event_id = data.get("event_id") or data.get("id")
    
    # Если event_id не найден, создаём его на основе event и task_id
    if not event_id and event and task_id:
        event_id = f"{event}:{task_id}"

    print(f"🔍 Извлечено: event={event}, task_id={task_id}, event_id={event_id}")

    if not task_id:
        print("⚠️ task_id не найден в payload")
        return {"status": "ok", "warning": "task_id not found"}

    if task_id:
        print(f"✅ Добавлена задача {task_id} в очередь обработки")
        background_tasks.add_task(process_webhook_logic, task_id, event_id)

    return {"status": "ok"}

@app.on_event("startup")
async def on_startup():
    await init_db()
    print("🚀 База данных готова к работе")