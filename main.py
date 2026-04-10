import hashlib
import hmac
import json
import logging
from datetime import datetime
from typing import Mapping
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request, status
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
import Bot.services as bot_services
from clickup_client import get_task_details, list_webhooks, delete_webhook
from config import CLICKUP_WEBHOOK_SECRET, WEBHOOK_URL, CLICKUP_TEAM_ID
from database import async_session, init_db
from filters import is_important
from models import SentEvent, Subscription, WebhookConfig
from schemas import ClickUpWebhook
from register_webhook import register

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
)
logger = logging.getLogger("clickup_backend")

app = FastAPI(title="ClickUp to Telegram Integration")


def log_event(
    level: int,
    message: str,
    event_id: str = "N/A",
    task_id: str = "N/A",
    event_type: str = "N/A",
) -> None:
    logger.log(
        level,
        "event_id=%s task_id=%s event_type=%s %s",
        event_id,
        task_id,
        event_type,
        message,
    )


async def verify_signature(headers: Mapping[str, str], body: bytes) -> None:
    signature = headers.get("X-ClickUp-Signature")
    if not signature:
        logger.warning("No signature header")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    # Пробуем взять секрет из БД, если там пусто — берем из конфига (fallback)
    db_secret = await bot_services.get_webhook_secret_from_db()
    secret_to_use = db_secret or CLICKUP_WEBHOOK_SECRET

    expected = hmac.new(secret_to_use.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        logger.warning("Invalid signature. DB secret was used: %s", bool(db_secret))
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)


def build_event_id(payload: dict) -> str:
    event_id = payload.get("id")
    if event_id:
        return str(event_id)

    payload_str = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload_str.encode()).hexdigest()


async def is_processed(payload: dict) -> bool:
    event_id = build_event_id(payload)

    async with async_session() as session:
        try:
            session.add(SentEvent(event_id=event_id, created_at=datetime.utcnow()))
            await session.commit()
            return False
        except IntegrityError:
            await session.rollback()
            return True
        except Exception:
            await session.rollback()
            logger.exception("Deduplication storage failure")
            raise


async def process_webhook_logic(data: dict) -> None:
    event_id = str(data.get("id") or "N/A")
    task_id = str(data.get("task_id") or "")
    event_type = str(data.get("event") or "N/A")

    try:
        if await is_processed(data):
            log_event(
                logging.INFO,
                "Duplicate event ignored",
                event_id=event_id,
                task_id=task_id or "N/A",
                event_type=event_type,
            )
            return
    except Exception:
        log_event(
            logging.ERROR,
            "Event processing stopped because deduplication failed",
            event_id=event_id,
            task_id=task_id or "N/A",
            event_type=event_type,
        )
        return

    if not task_id:
        log_event(
            logging.WARNING,
            "Payload has no task_id; event skipped",
            event_id=event_id,
            event_type=event_type,
        )
        return

    task = await get_task_details(task_id)
    if task and is_important(task):
        task_name = str(task.get("name") or "unnamed")
        log_event(
            logging.INFO,
            f"Important task matched criteria: {task_name}",
            event_id=event_id,
            task_id=task_id,
            event_type=event_type,
        )


        list_id = task.get("list", {}).get("id")
        if list_id:
            async with async_session() as session:

                query = select(Subscription.tg_chat_id).where(
                    Subscription.clickup_list_id == list_id,
                    Subscription.is_active == True
                )
                result = await session.execute(query)
                chat_ids = result.scalars().all()

                if chat_ids:
                    summary = bot_services.format_task_summary(task)
                    event_desc = f"Событие: {event_type}\n\n{summary}"
                    for chat_id in chat_ids:
                        await bot_services.send_notification(chat_id, event_desc, task_url=task.get("url"))

    else:
        task_name = str(task.get("name") or task_id)
        log_event(
            logging.INFO,
            f"Task skipped by filter: {task_name}",
            event_id=event_id,
            task_id=task_id,
            event_type=event_type,
        )


@app.post("/webhook/clickup")
async def handle_webhook(request: Request, background_tasks: BackgroundTasks) -> dict:
    body = await request.body()

    # Security-first: authenticate sender before spending effort on validation.
    await verify_signature(request.headers, body)

    try:
        payload = ClickUpWebhook.model_validate_json(body)
    except ValidationError as exc:
        logger.warning("Payload validation failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid payload format")

    log_event(
        logging.INFO,
        "Verified and validated payload",
        event_id=payload.id or "N/A",
        task_id=payload.task_id,
        event_type=payload.event,
    )

    background_tasks.add_task(process_webhook_logic, payload.model_dump())
    return {"status": "ok"}

@app.on_event("startup")
async def on_startup() -> None:
    await init_db()

    if not WEBHOOK_URL:
        logger.info("WEBHOOK_URL is empty, skipping webhook check.")
        logger.info("Service started and database initialized")
        return

    async with async_session() as session:
        db_config = (await session.execute(select(WebhookConfig))).scalar_one_or_none()

    team_id = db_config.team_id if db_config and db_config.team_id else CLICKUP_TEAM_ID

    if not team_id:
        logger.info("No team_id configured yet (neither in DB nor in .env), skipping webhook check.")
        logger.info("Service started and database initialized")
        return

    logger.info("Checking webhook health on startup...")
    webhooks = await list_webhooks(team_id)

    active_webhook = next((w for w in webhooks if w.get("endpoint") == WEBHOOK_URL), None)

    async with async_session() as session:
        db_config = (await session.execute(select(WebhookConfig))).scalar_one_or_none()

        if not active_webhook or not db_config or db_config.webhook_id != active_webhook.get("id"):
            logger.info("Webhook missing or out of sync. Re-registering...")

            if active_webhook:
                await delete_webhook(active_webhook["id"])

            res = await register(
                override_api_key=db_config.api_key if db_config and db_config.api_key else None,
                override_team_id=team_id,
                )

            if isinstance(res, dict) and "error" in res:
                logger.error("Startup webhook registration failed: %s", res.get("error"))
            else:
                logger.info("Webhook successfully synchronized on startup")
        else:
            logger.info("Webhook is healthy and synchronized (ID: %s)", active_webhook["id"])

    logger.info("Service started and database initialized")