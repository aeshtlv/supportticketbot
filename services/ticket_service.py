"""
Сервис для работы с тикетами
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Ticket, TicketStatus


class TicketService:
    """Сервис для работы с тикетами"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_open_ticket_by_user(self, user_id: int) -> Optional[Ticket]:
        """Получить открытый тикет пользователя"""
        result = await self.session.execute(
            select(Ticket)
            .where(
                Ticket.user_id == user_id,
                Ticket.status == TicketStatus.OPEN
            )
            .order_by(Ticket.created_at.desc())
        )
        return result.scalar_one_or_none()
    
    async def get_last_ticket_by_user(self, user_id: int) -> Optional[Ticket]:
        """Получить последний тикет пользователя (включая закрытые)"""
        result = await self.session.execute(
            select(Ticket)
            .where(Ticket.user_id == user_id)
            .order_by(Ticket.created_at.desc())
        )
        return result.scalar_one_or_none()
    
    async def create_ticket(
        self,
        user_id: int,
        user_chat_id: int,
        username: Optional[str],
        full_name: str
    ) -> Ticket:
        """Создать новый тикет"""
        ticket = Ticket(
            ticket_id=Ticket.generate_id(),
            user_id=user_id,
            user_chat_id=user_chat_id,
            username=username,
            full_name=full_name,
            status=TicketStatus.OPEN
        )
        self.session.add(ticket)
        await self.session.commit()
        await self.session.refresh(ticket)
        return ticket
    
    async def set_topic_id(self, ticket: Ticket, topic_id: int) -> Ticket:
        """Установить topic_id для тикета"""
        ticket.topic_id = topic_id
        await self.session.commit()
        await self.session.refresh(ticket)
        return ticket
    
    async def get_ticket_by_topic_id(self, topic_id: int) -> Optional[Ticket]:
        """Получить тикет по topic_id"""
        result = await self.session.execute(
            select(Ticket).where(Ticket.topic_id == topic_id)
        )
        return result.scalar_one_or_none()
    
    async def close_ticket(self, ticket: Ticket) -> Ticket:
        """Закрыть тикет"""
        ticket.status = TicketStatus.CLOSED
        ticket.closed_at = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(ticket)
        return ticket
    
    async def reopen_ticket(self, ticket: Ticket) -> Ticket:
        """Переоткрыть тикет"""
        ticket.status = TicketStatus.OPEN
        ticket.closed_at = None
        await self.session.commit()
        await self.session.refresh(ticket)
        return ticket
