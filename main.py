import hashlib
import hmac
import json
import logging
from datetime import datetime
from typing import Mapping
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request, status
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy import delete, select
from Bot.services import format_task_summary, get_webhook_config_from_db, get_webhook_secret_from_db, send_notification
from clickup_client import get_task_details, list_webhooks
from config import CLICKUP_API_KEY, CLICKUP_WEBHOOK_SECRET, WEBHOOK_URL, CLICKUP_TEAM_ID
from database import async_session, init_db
from filters import is_important
from models import SentEvent, Subscription, TaskStateCache, WebhookConfig
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
    # ClickUp may send signature in different header names depending on integration path.
    signature = headers.get("X-ClickUp-Signature") or headers.get("X-Signature")
    if not signature:
        logger.warning("No signature header")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    db_secret = await get_webhook_secret_from_db()
    secret_to_use = db_secret or CLICKUP_WEBHOOK_SECRET

    if not secret_to_use:
        logger.error("Webhook secret is not configured (DB and env are empty)")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    expected = hmac.new(secret_to_use.encode(), body, hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected, signature):
        logger.warning("Invalid signature. DB secret was used: %s", bool(db_secret))
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")


def build_event_id(payload: dict) -> str:
    event_id = payload.get("id")
    if event_id:
        return str(event_id)

    payload_str = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload_str.encode()).hexdigest()


def _hash_state(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _serialize_task_state(task: dict, field_name: str) -> str:
    if field_name == "status":
        return str((task.get("status") or {}).get("status") or "")
    if field_name == "priority":
        return str((task.get("priority") or {}).get("priority") or "")
    if field_name == "due_date":
        return str(task.get("due_date") or "")
    if field_name == "assignees":
        assignee_ids = sorted(str(a.get("id")) for a in task.get("assignees", []) if a.get("id") is not None)
        return "|".join(assignee_ids)
    if field_name == "tags":
        tag_names = sorted(str(t.get("name") or "").lower() for t in task.get("tags", []))
        return "|".join(tag_names)
    if field_name == "created":
        payload = {
            "status": (task.get("status") or {}).get("status") or "",
            "priority": (task.get("priority") or {}).get("priority") or "",
            "due_date": task.get("due_date") or "",
            "assignees": sorted(str(a.get("id")) for a in task.get("assignees", []) if a.get("id") is not None),
            "tags": sorted(str(t.get("name") or "").lower() for t in task.get("tags", [])),
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return json.dumps(task, sort_keys=True, separators=(",", ":"))


def _field_for_event(event_type: str) -> str:
    mapping = {
        "taskCreated": "created",
        "taskStatusUpdated": "status",
        "taskPriorityUpdated": "priority",
        "taskDueDateUpdated": "due_date",
        "taskAssigneeUpdated": "assignees",
        "taskTagUpdated": "tags",
    }
    return mapping.get(event_type, event_type)


def _importance_channel_for_event(event_type: str) -> str | None:
    mapping = {
        "taskPriorityUpdated": "priority",
        "taskTagUpdated": "tags",
    }
    return mapping.get(event_type)


async def _is_state_duplicate(task_id: str, field_name: str, state_hash: str) -> bool:
    async with async_session() as session:
        row = (
            await session.execute(
                select(TaskStateCache).where(
                    TaskStateCache.task_id == task_id,
                    TaskStateCache.field_name == field_name,
                )
            )
        ).scalar_one_or_none()

        if row and row.state_hash == state_hash:
            return True

        if row:
            row.state_hash = state_hash
            row.updated_at = datetime.utcnow()
            await session.commit()
            return False

        session.add(
            TaskStateCache(
                task_id=task_id,
                field_name=field_name,
                state_hash=state_hash,
                updated_at=datetime.utcnow(),
            )
        )

        try:
            await session.commit()
            return False
        except IntegrityError:
            # Concurrent webhook may insert the same (task_id, field_name) first.
            # Re-read persisted value and decide deterministically.
            await session.rollback()
            persisted = (
                await session.execute(
                    select(TaskStateCache).where(
                        TaskStateCache.task_id == task_id,
                        TaskStateCache.field_name == field_name,
                    )
                )
            ).scalar_one_or_none()
            if persisted and persisted.state_hash == state_hash:
                return True
            if persisted:
                persisted.state_hash = state_hash
                persisted.updated_at = datetime.utcnow()
                await session.commit()
                return False
            raise


async def _acquire_importance_channel_lock(task_id: str, channel: str) -> bool:
    channel_hash = _hash_state(f"importance_channel:{channel}")

    async with async_session() as session:
        row = (
            await session.execute(
                select(TaskStateCache).where(
                    TaskStateCache.task_id == task_id,
                    TaskStateCache.field_name == "importance_channel_lock",
                )
            )
        ).scalar_one_or_none()

        if not row:
            session.add(
                TaskStateCache(
                    task_id=task_id,
                    field_name="importance_channel_lock",
                    state_hash=channel_hash,
                    updated_at=datetime.utcnow(),
                )
            )
            await session.commit()
            return True

        return row.state_hash == channel_hash


async def _seed_task_state_cache(task_id: str, task: dict) -> None:
    for field_name in ("status", "priority", "due_date", "assignees", "tags"):
        serialized = _serialize_task_state(task, field_name)
        state_hash = _hash_state(serialized)
        await _is_state_duplicate(task_id, field_name, state_hash)


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
            "Deduplication failed; continuing processing to avoid event loss",
            event_id=event_id,
            task_id=task_id or "N/A",
            event_type=event_type,
        )

    if not task_id:
        log_event(
            logging.WARNING,
            "Payload has no task_id; event skipped",
            event_id=event_id,
            event_type=event_type,
        )
        return

    task = await get_task_details(task_id)
    if not task:
        log_event(
            logging.WARNING,
            "Task details not found; event skipped",
            event_id=event_id,
            task_id=task_id,
            event_type=event_type,
        )
        return

    field_name = _field_for_event(event_type)
    serialized_state = _serialize_task_state(task, field_name)
    state_hash = _hash_state(serialized_state)
    try:
        if await _is_state_duplicate(task_id, field_name, state_hash):
            log_event(
                logging.INFO,
                f"Duplicate state ignored for field={field_name}",
                event_id=event_id,
                task_id=task_id,
                event_type=event_type,
            )
            return
    except Exception:
        log_event(
            logging.ERROR,
            f"State-cache check failed for field={field_name}; continuing",
            event_id=event_id,
            task_id=task_id,
            event_type=event_type,
        )

    if task and is_important(task):
        importance_channel = _importance_channel_for_event(event_type)
        if importance_channel:
            try:
                lock_acquired = await _acquire_importance_channel_lock(task_id, importance_channel)
            except Exception:
                log_event(
                    logging.ERROR,
                    "Importance channel lock check failed; continuing",
                    event_id=event_id,
                    task_id=task_id,
                    event_type=event_type,
                )
            else:
                if not lock_acquired:
                    log_event(
                        logging.INFO,
                        f"Notification suppressed by importance channel lock ({importance_channel})",
                        event_id=event_id,
                        task_id=task_id,
                        event_type=event_type,
                    )
                    return

        notification_state = _serialize_task_state(task, "created")
        notification_hash = _hash_state(notification_state)
        try:
            if await _is_state_duplicate(task_id, "notification_fingerprint", notification_hash):
                log_event(
                    logging.INFO,
                    "Duplicate notification fingerprint ignored",
                    event_id=event_id,
                    task_id=task_id,
                    event_type=event_type,
                )
                return
        except Exception:
            log_event(
                logging.ERROR,
                "Notification fingerprint check failed; continuing",
                event_id=event_id,
                task_id=task_id,
                event_type=event_type,
            )

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
                    summary = format_task_summary(task)
                    event_desc = f"Событие: {event_type}\n\n{summary}"
                    for chat_id in chat_ids:
                        try:
                            await send_notification(chat_id, event_desc, task_url=task.get("url"))
                        except Exception:
                            log_event(
                                logging.ERROR,
                                "Notification send failed for chat",
                                event_id=event_id,
                                task_id=task_id,
                                event_type=event_type,
                            )

        if event_type == "taskCreated":
            try:
                await _seed_task_state_cache(task_id, task)
            except Exception:
                log_event(
                    logging.ERROR,
                    "Unable to seed task_state_cache for created task",
                    event_id=event_id,
                    task_id=task_id,
                    event_type=event_type,
                )

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

    db_config = await get_webhook_config_from_db()
    if db_config and payload.webhook_id != db_config.webhook_id:
        logger.warning(
            "Webhook id mismatch: payload=%s expected=%s",
            payload.webhook_id,
            db_config.webhook_id,
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

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

    missing = []
    if not CLICKUP_API_KEY:
        missing.append("CLICKUP_API_KEY")
    if not CLICKUP_TEAM_ID:
        missing.append("CLICKUP_TEAM_ID")
    if not WEBHOOK_URL:
        missing.append("WEBHOOK_URL")

    if missing:
        logger.error(
            "Startup config error: missing required env vars for webhook sync: %s",
            ", ".join(missing),
        )
        logger.info("Service started and database initialized; webhook sync is disabled")
        return

    team_id = CLICKUP_TEAM_ID

    logger.info("Checking webhook health on startup...")
    webhooks = await list_webhooks(team_id)
    active_webhook = next((w for w in webhooks if w.get("endpoint") == WEBHOOK_URL), None)

    async with async_session() as session:
        db_config = (await session.execute(select(WebhookConfig))).scalar_one_or_none()

        if active_webhook:
            active_id = active_webhook.get("id")
            if not active_id:
                logger.warning("Active webhook has no id; synchronization skipped")
                logger.info("Service started and database initialized")
                return
            if not db_config or db_config.webhook_id != active_id:
                if CLICKUP_WEBHOOK_SECRET:
                    await session.execute(delete(WebhookConfig))
                    session.add(
                        WebhookConfig(
                            webhook_id=active_id,
                            secret=CLICKUP_WEBHOOK_SECRET,
                            url=WEBHOOK_URL,
                        )
                    )
                    await session.commit()
                    logger.info("Webhook config synchronized from active endpoint")
                else:
                    logger.warning(
                        "Active webhook found but CLICKUP_WEBHOOK_SECRET is empty; DB sync skipped"
                    )
            else:
                logger.info("Webhook is healthy and synchronized (ID: %s)", active_id)
        else:
            logger.info("Webhook not found for endpoint. Registering...")
            res = await register()

            if isinstance(res, dict) and "error" in res:
                logger.error("Startup webhook registration failed: %s", res.get("error"))
            else:
                logger.info("Webhook successfully synchronized on startup")

    logger.info("Service started and database initialized")