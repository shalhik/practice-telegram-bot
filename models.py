from datetime import datetime

from sqlalchemy import BigInteger, String, DateTime, Boolean, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    """Базовый класс для всех моделей."""
    pass

class Subscription(Base):
    """Таблица подписок: кто на какой список ClickUp подписан."""
    __tablename__ = "subscriptions"
    __table_args__ = (
        UniqueConstraint("tg_chat_id", "clickup_list_id", name="uq_subscription_chat_list"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tg_chat_id: Mapped[int] = mapped_column(BigInteger)        # ID чата в Telegram
    clickup_list_id: Mapped[str] = mapped_column(String)       # ID списка в ClickUp
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)  # Флаг уведомлений

class SentEvent(Base):
    """Таблица для защиты от дублей (уникальный ID события ClickUp)."""
    __tablename__ = "sent_events"

    event_id: Mapped[str] = mapped_column(String, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )


class TaskStateCache(Base):
    """Последнее известное состояние полей задачи для подавления дублей уведомлений."""
    __tablename__ = "task_state_cache"
    __table_args__ = (
        UniqueConstraint("task_id", "field_name", name="uq_task_state_field"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[str] = mapped_column(String, nullable=False)
    field_name: Mapped[str] = mapped_column(String, nullable=False)
    state_hash: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class WebhookConfig(Base):
    """
    Конфигурация вебхука ClickUp:
    - храним ID вебхука и секрет,
    - URL эндпоинта,
    - а также API ключ и team_id, если пользователь их вводил через бота.
    """
    __tablename__ = "webhook_config"

    id: Mapped[int] = mapped_column(primary_key=True)
    webhook_id: Mapped[str] = mapped_column(String, nullable=False)
    secret: Mapped[str] = mapped_column(String, nullable=False)
    url: Mapped[str] = mapped_column(String, nullable=False)
    api_key: Mapped[str] = mapped_column(String, nullable=True)
    team_id: Mapped[str] = mapped_column(String, nullable=True)