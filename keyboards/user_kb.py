"""
Клавиатуры для пользователя
"""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from database.models import Ticket, TicketStatus


class UserKeyboards:
    """Клавиатуры для пользователя"""
    
    @staticmethod
    def main_menu() -> InlineKeyboardMarkup:
        """Главное меню"""
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🆕 Создать тикет", callback_data="create_ticket")],
            [InlineKeyboardButton(text="📂 Мои обращения", callback_data="my_tickets")]
        ])
    
    @staticmethod
    def cancel() -> InlineKeyboardMarkup:
        """Кнопка отмены"""
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]
        ])
    
    @staticmethod
    def confirm_new_ticket() -> InlineKeyboardMarkup:
        """Подтверждение создания"""
        return InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да", callback_data="confirm_new_ticket"),
                InlineKeyboardButton(text="❌ Нет", callback_data="cancel")
            ]
        ])
    
    @staticmethod
    def tickets_list(tickets: list[Ticket]) -> InlineKeyboardMarkup:
        """Список тикетов"""
        buttons = []
        
        # Разделяем на активные и закрытые
        active = [t for t in tickets if t.status != TicketStatus.CLOSED]
        closed = [t for t in tickets if t.status == TicketStatus.CLOSED]
        
        if active:
            for ticket in active[:5]:
                status_emoji = {
                    TicketStatus.OPEN: "⚪",
                    TicketStatus.IN_PROGRESS: "🟠",
                    TicketStatus.WAITING_USER: "🔴",
                }.get(ticket.status, "⚪")
                
                subject = ticket.subject[:25] + "…" if len(ticket.subject) > 25 else ticket.subject
                
                buttons.append([
                    InlineKeyboardButton(
                        text=f"{status_emoji} [{ticket.ticket_code}] {subject}",
                        callback_data=f"view_ticket:{ticket.ticket_code}"
                    )
                ])
        
        if closed:
            buttons.append([InlineKeyboardButton(
                text=f"📦 Закрытые ({len(closed)})",
                callback_data="closed_tickets"
            )])
        
        if not active and not closed:
            buttons.append([InlineKeyboardButton(
                text="📭 Нет обращений",
                callback_data="back_to_menu"
            )])
        
        buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")])
        
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def closed_tickets_list(tickets: list[Ticket]) -> InlineKeyboardMarkup:
        """Список закрытых тикетов"""
        buttons = []
        
        for ticket in tickets[:8]:
            subject = ticket.subject[:20] + "…" if len(ticket.subject) > 20 else ticket.subject
            date = ticket.closed_at.strftime("%d.%m") if ticket.closed_at else "?"
            
            buttons.append([
                InlineKeyboardButton(
                    text=f"⚫ [{ticket.ticket_code}] {subject} · {date}",
                    callback_data=f"view_ticket:{ticket.ticket_code}"
                )
            ])
        
        if not tickets:
            buttons.append([InlineKeyboardButton(
                text="📭 Нет закрытых обращений",
                callback_data="my_tickets"
            )])
        
        buttons.append([InlineKeyboardButton(text="🔙 К обращениям", callback_data="my_tickets")])
        
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def ticket_view(ticket: Ticket) -> InlineKeyboardMarkup:
        """Просмотр тикета"""
        buttons = []
        
        if ticket.status != TicketStatus.CLOSED:
            buttons.append([
                InlineKeyboardButton(
                    text="💬 Написать",
                    callback_data=f"chat_ticket:{ticket.ticket_code}"
                )
            ])
            buttons.append([
                InlineKeyboardButton(
                    text="📜 История",
                    callback_data=f"user_history:{ticket.ticket_code}"
                ),
                InlineKeyboardButton(
                    text="🔒 Закрыть",
                    callback_data=f"user_close:{ticket.ticket_code}"
                )
            ])
        else:
            buttons.append([
                InlineKeyboardButton(
                    text="📜 История",
                    callback_data=f"user_history:{ticket.ticket_code}"
                )
            ])
            buttons.append([
                InlineKeyboardButton(
                    text="🆕 Создать новый",
                    callback_data="create_ticket"
                )
            ])
        
        buttons.append([InlineKeyboardButton(text="🔙 К списку", callback_data="my_tickets")])
        
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def ticket_chat(ticket: Ticket) -> InlineKeyboardMarkup:
        """Чат тикета"""
        return InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📜 История",
                    callback_data=f"user_history:{ticket.ticket_code}"
                ),
                InlineKeyboardButton(
                    text="🔒 Закрыть",
                    callback_data=f"user_close:{ticket.ticket_code}"
                )
            ],
            [InlineKeyboardButton(text="🔙 Выйти", callback_data="exit_chat")]
        ])
    
    @staticmethod
    def history_back(ticket_code: str) -> InlineKeyboardMarkup:
        """Возврат из истории"""
        return InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💬 Написать",
                    callback_data=f"chat_ticket:{ticket_code}"
                ),
                InlineKeyboardButton(
                    text="🔙 Назад",
                    callback_data=f"view_ticket:{ticket_code}"
                )
            ]
        ])
    
    @staticmethod
    def confirm_close(ticket_code: str) -> InlineKeyboardMarkup:
        """Подтверждение закрытия"""
        return InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Да, закрыть",
                    callback_data=f"confirm_close:{ticket_code}"
                ),
                InlineKeyboardButton(
                    text="❌ Нет",
                    callback_data=f"view_ticket:{ticket_code}"
                )
            ]
        ])
    
    @staticmethod
    def no_active_ticket() -> InlineKeyboardMarkup:
        """Нет активного тикета"""
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🆕 Создать тикет", callback_data="create_ticket")]
        ])
    
    @staticmethod
    def after_ticket_closed() -> InlineKeyboardMarkup:
        """После закрытия тикета"""
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🆕 Создать новый тикет", callback_data="create_ticket")],
            [InlineKeyboardButton(text="📂 Мои обращения", callback_data="my_tickets")]
        ])
