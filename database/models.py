"""
Модели базы данных
"""
import enum
import random
import string
from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class TicketStatus(enum.Enum):
    """Статусы тикета"""
    OPEN = "open"
    CLOSED = "closed"


class User(Base):
    """Модель пользователя"""
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str] = mapped_column(String(255))
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    
    tickets: Mapped[list["Ticket"]] = relationship("Ticket", back_populates="user")
    message_links: Mapped[list["MessageLink"]] = relationship("MessageLink", back_populates="user")


class Ticket(Base):
    """Модель тикета"""
    __tablename__ = "tickets"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    status: Mapped[TicketStatus] = mapped_column(Enum(TicketStatus), default=TicketStatus.OPEN)
    topic_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    user: Mapped["User"] = relationship("User", back_populates="tickets")
    message_links: Mapped[list["MessageLink"]] = relationship("MessageLink", back_populates="ticket")
    
    @staticmethod
    def generate_id() -> str:
        """Генерирует уникальный ID тикета SHFT-XXXX"""
        chars = string.ascii_uppercase + string.digits
        code = ''.join(random.choices(chars, k=4))
        return f"SHFT-{code}"


class MessageLink(Base):
    """Связь между сообщением пользователя и сообщением в чате поддержки"""
    __tablename__ = "message_links"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    user_message_id: Mapped[int] = mapped_column(BigInteger)
    support_message_id: Mapped[int] = mapped_column(BigInteger)
    topic_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    
    ticket: Mapped["Ticket"] = relationship("Ticket", back_populates="message_links")
    user: Mapped["User"] = relationship("User", back_populates="message_links")


class BotSettings(Base):
    """Настройки бота"""
    __tablename__ = "bot_settings"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    value: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
