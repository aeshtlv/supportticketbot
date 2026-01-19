"""
Клавиатуры для пользователя
"""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton

from database.models import Ticket, TicketStatus


class UserKeyboards:
    """Клавиатуры для пользователя"""
    
    @staticmethod
    def main_menu() -> InlineKeyboardMarkup:
        """Главное меню пользователя"""
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
        """Подтверждение создания второго тикета"""
        return InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да", callback_data="confirm_new_ticket"),
                InlineKeyboardButton(text="❌ Нет", callback_data="cancel")
            ]
        ])
    
    @staticmethod
    def tickets_list(tickets: list[Ticket]) -> InlineKeyboardMarkup:
        """Список тикетов пользователя"""
        buttons = []
        
        for ticket in tickets:
            status_emoji = {
                TicketStatus.OPEN: "🔵",
                TicketStatus.IN_PROGRESS: "🟡",
                TicketStatus.WAITING_USER: "🟠",
                TicketStatus.CLOSED: "⚫"
            }.get(ticket.status, "⚪")
            
            # Обрезаем тему если слишком длинная
            subject = ticket.subject[:30] + "..." if len(ticket.subject) > 30 else ticket.subject
            
            buttons.append([
                InlineKeyboardButton(
                    text=f"{status_emoji} [{ticket.ticket_code}] {subject}",
                    callback_data=f"view_ticket:{ticket.ticket_code}"
                )
            ])
        
        buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")])
        
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def ticket_view(ticket: Ticket) -> InlineKeyboardMarkup:
        """Просмотр тикета пользователем"""
        buttons = []
        
        if ticket.status != TicketStatus.CLOSED:
            buttons.append([
                InlineKeyboardButton(
                    text="💬 Написать в тикет",
                    callback_data=f"chat_ticket:{ticket.ticket_code}"
                )
            ])
        
        buttons.append([InlineKeyboardButton(text="🔙 К списку", callback_data="my_tickets")])
        
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def ticket_chat(ticket: Ticket) -> InlineKeyboardMarkup:
        """Клавиатура в режиме чата тикета"""
        buttons = [
            [InlineKeyboardButton(text="🔙 Выйти из чата", callback_data="exit_chat")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def no_active_ticket() -> InlineKeyboardMarkup:
        """Клавиатура когда нет активного тикета"""
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🆕 Создать тикет", callback_data="create_ticket")]
        ])

