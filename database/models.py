"""
Модели базы данных
"""
import enum
import random
import string
from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class TicketStatus(enum.Enum):
    """Статусы тикета"""
    OPEN = "open"
    CLOSED = "closed"


class Ticket(Base):
    """Модель тикета"""
    __tablename__ = "tickets"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    # Идентификаторы
    ticket_id: Mapped[str] = mapped_column(String(20), unique=True, index=True)  # Краткий ID тикета
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)  # Telegram user_id
    user_chat_id: Mapped[int] = mapped_column(BigInteger, index=True)  # Telegram chat_id пользователя
    
    # Информация о пользователе
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str] = mapped_column(String(255))
    
    # Топик в админ-группе
    topic_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, unique=True, index=True)
    
    # Статус
    status: Mapped[TicketStatus] = mapped_column(Enum(TicketStatus), default=TicketStatus.OPEN)
    
    # Временные метки
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    @staticmethod
    def generate_id() -> str:
        """Генерирует краткий идентификатор тикета (4 символа)"""
        chars = string.ascii_uppercase + string.digits
        code = ''.join(random.choices(chars, k=4))
        return code
