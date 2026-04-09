import hashlib
import hmac
import json
import logging
from datetime import datetime
from typing import Mapping

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request, status
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from clickup_client import get_task_details
from config import CLICKUP_WEBHOOK_SECRET
from database import async_session, init_db
from filters import is_important
from models import SentEvent
from notifications import notify_subscribers
from schemas import ClickUpWebhook

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


def verify_signature(headers: Mapping[str, str], body: bytes) -> None:
    signature = headers.get("X-ClickUp-Signature")
    if not signature:
        logger.warning("No signature header")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    expected = hmac.new(CLICKUP_WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        logger.warning("Invalid signature")
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
        await notify_subscribers(task, event_id)
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
    verify_signature(request.headers, body)

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
    logger.info("Service started and database initialized")