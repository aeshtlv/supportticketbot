"""
Модели базы данных
"""
import enum
import secrets
from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class TicketStatus(enum.Enum):
    """Статусы тикета"""
    OPEN = "open"              # Открыт, оператор не назначен
    IN_PROGRESS = "in_progress"  # Оператор отвечает
    WAITING_USER = "waiting_user"  # Ждём ответ клиента
    CLOSED = "closed"          # Закрыт


class User(Base):
    """Модель пользователя"""
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str] = mapped_column(String(255))
    is_operator: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    
    # Отношения
    tickets: Mapped[list["Ticket"]] = relationship(
        "Ticket", 
        back_populates="user",
        foreign_keys="Ticket.user_id"
    )
    messages: Mapped[list["TicketMessage"]] = relationship(
        "TicketMessage",
        back_populates="sender"
    )


class Ticket(Base):
    """Модель тикета"""
    __tablename__ = "tickets"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_code: Mapped[str] = mapped_column(String(10), unique=True, index=True)
    subject: Mapped[str] = mapped_column(String(255))
    status: Mapped[TicketStatus] = mapped_column(
        Enum(TicketStatus), 
        default=TicketStatus.OPEN
    )
    priority: Mapped[str] = mapped_column(String(20), default="normal")
    
    # Связи
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    operator_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    
    # Временные метки
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        server_default=func.now(), 
        onupdate=func.now()
    )
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Отношения
    user: Mapped["User"] = relationship(
        "User", 
        back_populates="tickets",
        foreign_keys=[user_id]
    )
    operator: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[operator_id]
    )
    messages: Mapped[list["TicketMessage"]] = relationship(
        "TicketMessage",
        back_populates="ticket",
        order_by="TicketMessage.created_at"
    )
    
    @staticmethod
    def generate_code() -> str:
        """Генерирует уникальный код тикета вида TCK-XXXX"""
        return f"TCK-{secrets.token_hex(2).upper()}"


class TicketMessage(Base):
    """Модель сообщения в тикете"""
    __tablename__ = "ticket_messages"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id"))
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    
    # Контент сообщения
    content_type: Mapped[str] = mapped_column(String(20))  # text, photo, document
    text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    file_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Флаг "от оператора"
    is_from_operator: Mapped[bool] = mapped_column(Boolean, default=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    
    # Отношения
    ticket: Mapped["Ticket"] = relationship("Ticket", back_populates="messages")
    sender: Mapped["User"] = relationship("User", back_populates="messages")

