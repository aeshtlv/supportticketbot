"""
Сервис для работы с тикетами
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import Ticket, TicketStatus, User, MessageLink, BotSettings


class TicketService:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_or_create_user(self, telegram_id: int, username: Optional[str] = None, full_name: str = "Unknown") -> User:
        """Получить или создать пользователя"""
        result = await self.session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        
        if user is None:
            user = User(telegram_id=telegram_id, username=username, full_name=full_name)
            self.session.add(user)
            await self.session.commit()
            await self.session.refresh(user)
        else:
            if username != user.username or full_name != user.full_name:
                user.username = username
                user.full_name = full_name
                await self.session.commit()
        
        return user
    
    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Получить пользователя по telegram_id"""
        result = await self.session.execute(select(User).where(User.telegram_id == telegram_id))
        return result.scalar_one_or_none()
    
    async def ban_user(self, user: User) -> User:
        """Забанить пользователя"""
        user.is_banned = True
        await self.session.commit()
        await self.session.refresh(user)
        return user
    
    async def unban_user(self, user: User) -> User:
        """Разбанить пользователя"""
        user.is_banned = False
        await self.session.commit()
        await self.session.refresh(user)
        return user
    
    async def get_or_create_ticket(self, user: User, topic_id: Optional[int] = None) -> Ticket:
        """Получить открытый тикет или создать новый"""
        result = await self.session.execute(
            select(Ticket)
            .where(Ticket.user_id == user.id, Ticket.status == TicketStatus.OPEN)
            .order_by(Ticket.created_at.desc())
        )
        ticket = result.scalar_one_or_none()
        
        if ticket is None:
            ticket = Ticket(ticket_id=Ticket.generate_id(), user_id=user.id, status=TicketStatus.OPEN, topic_id=topic_id)
            self.session.add(ticket)
            await self.session.commit()
            await self.session.refresh(ticket)
        else:
            if topic_id and not ticket.topic_id:
                ticket.topic_id = topic_id
                await self.session.commit()
        
        return ticket
    
    async def get_ticket_by_id(self, ticket_id: str) -> Optional[Ticket]:
        """Получить тикет по ID"""
        result = await self.session.execute(
            select(Ticket).options(selectinload(Ticket.user)).where(Ticket.ticket_id == ticket_id)
        )
        return result.scalar_one_or_none()
    
    async def get_user_ticket(self, user: User) -> Optional[Ticket]:
        """Получить открытый тикет пользователя"""
        result = await self.session.execute(
            select(Ticket).where(Ticket.user_id == user.id, Ticket.status == TicketStatus.OPEN).order_by(Ticket.created_at.desc())
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
    
    async def get_open_tickets(self) -> list[Ticket]:
        """Получить все открытые тикеты"""
        result = await self.session.execute(
            select(Ticket).options(selectinload(Ticket.user)).where(Ticket.status == TicketStatus.OPEN).order_by(Ticket.created_at.desc())
        )
        return list(result.scalars().all())
    
    async def create_message_link(self, ticket: Ticket, user: User, user_message_id: int, support_message_id: int, topic_id: Optional[int] = None) -> MessageLink:
        """Создать связь между сообщениями"""
        link = MessageLink(
            ticket_id=ticket.id,
            user_id=user.id,
            user_message_id=user_message_id,
            support_message_id=support_message_id,
            topic_id=topic_id
        )
        self.session.add(link)
        await self.session.commit()
        await self.session.refresh(link)
        return link
    
    async def get_message_link_by_support_id(self, support_message_id: int) -> Optional[MessageLink]:
        """Получить связь по ID сообщения в чате поддержки"""
        result = await self.session.execute(
            select(MessageLink)
            .options(selectinload(MessageLink.user), selectinload(MessageLink.ticket))
            .where(MessageLink.support_message_id == support_message_id)
        )
        return result.scalar_one_or_none()
    
    async def get_message_links_by_topic(self, topic_id: int, limit: int = 10) -> list[MessageLink]:
        """Получить последние связи по topic_id"""
        result = await self.session.execute(
            select(MessageLink)
            .options(selectinload(MessageLink.user), selectinload(MessageLink.ticket))
            .where(MessageLink.topic_id == topic_id)
            .order_by(MessageLink.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_setting(self, key: str, default: str = "") -> str:
        """Получить настройку"""
        result = await self.session.execute(select(BotSettings).where(BotSettings.key == key))
        setting = result.scalar_one_or_none()
        return setting.value if setting else default
    
    async def set_setting(self, key: str, value: str) -> BotSettings:
        """Установить настройку"""
        result = await self.session.execute(select(BotSettings).where(BotSettings.key == key))
        setting = result.scalar_one_or_none()
        
        if setting:
            setting.value = value
        else:
            setting = BotSettings(key=key, value=value)
            self.session.add(setting)
        
        await self.session.commit()
        await self.session.refresh(setting)
        return setting
