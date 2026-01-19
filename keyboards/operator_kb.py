"""
Клавиатуры для оператора
"""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from database.models import Ticket, TicketStatus


class OperatorKeyboards:
    """Клавиатуры для оператора"""
    
    @staticmethod
    def main_menu(open_count: int) -> InlineKeyboardMarkup:
        """Главное меню оператора"""
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=f"📥 Открытые тикеты ({open_count})",
                callback_data="op_list_tickets"
            )],
            [InlineKeyboardButton(
                text="🔄 Обновить",
                callback_data="op_refresh"
            )]
        ])
    
    @staticmethod
    def tickets_list(tickets: list[Ticket]) -> InlineKeyboardMarkup:
        """Список тикетов для оператора"""
        buttons = []
        
        for ticket in tickets:
            status_emoji = {
                TicketStatus.OPEN: "🔵",
                TicketStatus.IN_PROGRESS: "🟡",
                TicketStatus.WAITING_USER: "🟠",
                TicketStatus.CLOSED: "⚫"
            }.get(ticket.status, "⚪")
            
            # Обрезаем тему
            subject = ticket.subject[:25] + "..." if len(ticket.subject) > 25 else ticket.subject
            username = f"@{ticket.user.username}" if ticket.user and ticket.user.username else "без username"
            
            buttons.append([
                InlineKeyboardButton(
                    text=f"{status_emoji} [{ticket.ticket_code}] {subject}",
                    callback_data=f"op_view:{ticket.ticket_code}"
                )
            ])
        
        buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="op_back_menu")])
        
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def ticket_view(ticket: Ticket) -> InlineKeyboardMarkup:
        """Просмотр тикета оператором"""
        buttons = []
        
        if ticket.status != TicketStatus.CLOSED:
            buttons.append([
                InlineKeyboardButton(
                    text="✍️ Ответить",
                    callback_data=f"op_reply:{ticket.ticket_code}"
                )
            ])
            buttons.append([
                InlineKeyboardButton(
                    text="🔒 Закрыть",
                    callback_data=f"op_close:{ticket.ticket_code}"
                ),
                InlineKeyboardButton(
                    text="⏳ Ожидаем пользователя",
                    callback_data=f"op_waiting:{ticket.ticket_code}"
                )
            ])
        else:
            buttons.append([
                InlineKeyboardButton(
                    text="🔓 Переоткрыть",
                    callback_data=f"op_reopen:{ticket.ticket_code}"
                )
            ])
        
        buttons.append([
            InlineKeyboardButton(text="📜 История", callback_data=f"op_history:{ticket.ticket_code}"),
            InlineKeyboardButton(text="🔙 К списку", callback_data="op_list_tickets")
        ])
        
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def reply_cancel() -> InlineKeyboardMarkup:
        """Кнопка отмены при ответе"""
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="op_cancel_reply")]
        ])

