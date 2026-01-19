"""
Сервис для работы с тикетами
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import Ticket, TicketMessage, TicketStatus, User


class TicketService:
    """Сервис для работы с тикетами"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    # ==================== ПОЛЬЗОВАТЕЛИ ====================
    
    async def get_or_create_user(
        self, 
        telegram_id: int, 
        username: Optional[str] = None,
        full_name: str = "Unknown",
        is_operator: bool = False
    ) -> User:
        """Получить или создать пользователя"""
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        
        if user is None:
            user = User(
                telegram_id=telegram_id,
                username=username,
                full_name=full_name,
                is_operator=is_operator
            )
            self.session.add(user)
            await self.session.commit()
            await self.session.refresh(user)
        else:
            # Обновляем данные
            if username != user.username or full_name != user.full_name:
                user.username = username
                user.full_name = full_name
                await self.session.commit()
        
        return user
    
    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Получить пользователя по telegram_id"""
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()
    
    # ==================== ТИКЕТЫ ====================
    
    async def create_ticket(self, user: User, subject: str) -> Ticket:
        """Создать тикет"""
        ticket = Ticket(
            ticket_code=Ticket.generate_code(),
            subject=subject,
            user_id=user.id,
            status=TicketStatus.OPEN
        )
        self.session.add(ticket)
        await self.session.commit()
        await self.session.refresh(ticket)
        return ticket
    
    async def get_ticket_by_code(self, code: str) -> Optional[Ticket]:
        """Получить тикет по коду"""
        result = await self.session.execute(
            select(Ticket)
            .options(selectinload(Ticket.user), selectinload(Ticket.operator))
            .where(Ticket.ticket_code == code)
        )
        return result.scalar_one_or_none()
    
    async def get_ticket_by_id(self, ticket_id: int) -> Optional[Ticket]:
        """Получить тикет по ID"""
        result = await self.session.execute(
            select(Ticket)
            .options(selectinload(Ticket.user), selectinload(Ticket.operator))
            .where(Ticket.id == ticket_id)
        )
        return result.scalar_one_or_none()
    
    async def get_user_open_tickets(self, user: User) -> list[Ticket]:
        """Получить открытые тикеты пользователя"""
        result = await self.session.execute(
            select(Ticket)
            .where(
                Ticket.user_id == user.id,
                Ticket.status != TicketStatus.CLOSED
            )
            .order_by(Ticket.created_at.desc())
        )
        return list(result.scalars().all())
    
    async def get_user_all_tickets(self, user: User, limit: int = 10) -> list[Ticket]:
        """Получить все тикеты пользователя"""
        result = await self.session.execute(
            select(Ticket)
            .where(Ticket.user_id == user.id)
            .order_by(Ticket.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_open_tickets_count(self) -> int:
        """Получить количество открытых тикетов"""
        result = await self.session.execute(
            select(func.count(Ticket.id))
            .where(Ticket.status.in_([TicketStatus.OPEN, TicketStatus.IN_PROGRESS, TicketStatus.WAITING_USER]))
        )
        return result.scalar() or 0
    
    async def get_all_open_tickets(self) -> list[Ticket]:
        """Получить все открытые тикеты (для оператора)"""
        result = await self.session.execute(
            select(Ticket)
            .options(selectinload(Ticket.user))
            .where(Ticket.status != TicketStatus.CLOSED)
            .order_by(Ticket.created_at.desc())
        )
        return list(result.scalars().all())
    
    async def update_ticket_status(
        self, 
        ticket: Ticket, 
        status: TicketStatus,
        operator: Optional[User] = None
    ) -> Ticket:
        """Обновить статус тикета"""
        ticket.status = status
        if operator:
            ticket.operator_id = operator.id
        if status == TicketStatus.CLOSED:
            ticket.closed_at = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(ticket)
        return ticket
    
    async def close_ticket(self, ticket: Ticket) -> Ticket:
        """Закрыть тикет"""
        return await self.update_ticket_status(ticket, TicketStatus.CLOSED)
    
    # ==================== СООБЩЕНИЯ ====================
    
    async def add_message(
        self,
        ticket: Ticket,
        sender: User,
        content_type: str = "text",
        text: Optional[str] = None,
        file_id: Optional[str] = None,
        file_name: Optional[str] = None,
        is_from_operator: bool = False
    ) -> TicketMessage:
        """Добавить сообщение в тикет"""
        message = TicketMessage(
            ticket_id=ticket.id,
            sender_id=sender.id,
            content_type=content_type,
            text=text,
            file_id=file_id,
            file_name=file_name,
            is_from_operator=is_from_operator
        )
        self.session.add(message)
        
        # Обновляем время тикета
        ticket.updated_at = datetime.utcnow()
        
        await self.session.commit()
        await self.session.refresh(message)
        return message
    
    async def get_ticket_messages(
        self, 
        ticket: Ticket, 
        limit: int = 50
    ) -> list[TicketMessage]:
        """Получить сообщения тикета"""
        result = await self.session.execute(
            select(TicketMessage)
            .options(selectinload(TicketMessage.sender))
            .where(TicketMessage.ticket_id == ticket.id)
            .order_by(TicketMessage.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())
    
    # ==================== АРХИВ И ФИЛЬТРЫ ====================
    
    async def get_closed_tickets(self, limit: int = 20) -> list[Ticket]:
        """Получить закрытые тикеты (архив)"""
        result = await self.session.execute(
            select(Ticket)
            .options(selectinload(Ticket.user), selectinload(Ticket.operator))
            .where(Ticket.status == TicketStatus.CLOSED)
            .order_by(Ticket.closed_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_tickets_by_status(self, status: TicketStatus, limit: int = 20) -> list[Ticket]:
        """Получить тикеты по статусу"""
        result = await self.session.execute(
            select(Ticket)
            .options(selectinload(Ticket.user), selectinload(Ticket.operator))
            .where(Ticket.status == status)
            .order_by(Ticket.updated_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_my_tickets(self, operator: User, limit: int = 20) -> list[Ticket]:
        """Получить тикеты назначенные на оператора"""
        result = await self.session.execute(
            select(Ticket)
            .options(selectinload(Ticket.user))
            .where(
                Ticket.operator_id == operator.id,
                Ticket.status != TicketStatus.CLOSED
            )
            .order_by(Ticket.updated_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def search_ticket(self, code: str) -> Optional[Ticket]:
        """Поиск тикета по коду (частичное совпадение)"""
        result = await self.session.execute(
            select(Ticket)
            .options(selectinload(Ticket.user), selectinload(Ticket.operator))
            .where(Ticket.ticket_code.ilike(f"%{code}%"))
            .limit(1)
        )
        return result.scalar_one_or_none()
    
    # ==================== СТАТИСТИКА ====================
    
    async def get_operator_stats(self, operator: User) -> dict:
        """Статистика оператора"""
        # Всего обработано
        total_result = await self.session.execute(
            select(func.count(Ticket.id))
            .where(Ticket.operator_id == operator.id)
        )
        total = total_result.scalar() or 0
        
        # Закрыто
        closed_result = await self.session.execute(
            select(func.count(Ticket.id))
            .where(
                Ticket.operator_id == operator.id,
                Ticket.status == TicketStatus.CLOSED
            )
        )
        closed = closed_result.scalar() or 0
        
        # В работе
        active_result = await self.session.execute(
            select(func.count(Ticket.id))
            .where(
                Ticket.operator_id == operator.id,
                Ticket.status != TicketStatus.CLOSED
            )
        )
        active = active_result.scalar() or 0
        
        return {
            "total": total,
            "closed": closed,
            "active": active
        }
    
    async def get_global_stats(self) -> dict:
        """Общая статистика"""
        # Всего тикетов
        total_result = await self.session.execute(
            select(func.count(Ticket.id))
        )
        total = total_result.scalar() or 0
        
        # По статусам
        stats = {"total": total}
        for status in TicketStatus:
            result = await self.session.execute(
                select(func.count(Ticket.id))
                .where(Ticket.status == status)
            )
            stats[status.value] = result.scalar() or 0
        
        return stats

