from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import BigInteger, String, Boolean, DateTime
from datetime import datetime

class Base(DeclarativeBase):
    pass

class TelegramChat(Base):
    """Таблица Telegram чатов и их состояния уведомлений."""
    __tablename__ = "telegram_chats"

    id: Mapped[int] = mapped_column(primary_key=True)
    tg_chat_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

class Subscription(Base):
    """Таблица подписок: кто на какой список ClickUp подписан"""
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    tg_chat_id: Mapped[int] = mapped_column(BigInteger)  # ID чата в телеге
    clickup_list_id: Mapped[str] = mapped_column(String)  # ID списка в ClickUp

class SentEvent(Base):
    """Таблица для защиты от дублей (Рубеж 6)"""
    __tablename__ = "sent_events"

    # У каждого события ClickUp есть уникальный ID (например, 'evt_123')
    event_id: Mapped[str] = mapped_column(String, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)