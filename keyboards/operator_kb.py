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
                text=f"📥 Тикеты ({open_count})",
                callback_data="op_list_tickets"
            )],
            [InlineKeyboardButton(
                text="🔄 Обновить",
                callback_data="op_refresh"
            )]
        ])
    
    @staticmethod
    def tickets_list(tickets: list[Ticket]) -> InlineKeyboardMarkup:
        """Список тикетов - компактный вид"""
        buttons = []
        
        for ticket in tickets[:15]:  # Лимит 15 тикетов
            status_emoji = {
                TicketStatus.OPEN: "🔵",
                TicketStatus.IN_PROGRESS: "🟡",
                TicketStatus.WAITING_USER: "🟠",
                TicketStatus.CLOSED: "⚫"
            }.get(ticket.status, "⚪")
            
            # Компактное отображение
            subject = ticket.subject[:20] + "…" if len(ticket.subject) > 20 else ticket.subject
            
            # Основная кнопка тикета
            buttons.append([
                InlineKeyboardButton(
                    text=f"{status_emoji} {ticket.ticket_code} · {subject}",
                    callback_data=f"op_view:{ticket.ticket_code}"
                ),
                InlineKeyboardButton(
                    text="✍️",
                    callback_data=f"op_quick_reply:{ticket.ticket_code}"
                )
            ])
        
        if len(tickets) > 15:
            buttons.append([InlineKeyboardButton(
                text=f"... ещё {len(tickets) - 15} тикетов",
                callback_data="op_list_tickets"
            )])
        
        buttons.append([
            InlineKeyboardButton(text="🔄", callback_data="op_refresh"),
            InlineKeyboardButton(text="🏠 Меню", callback_data="op_back_menu")
        ])
        
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def ticket_view(ticket: Ticket) -> InlineKeyboardMarkup:
        """Просмотр тикета - основные действия"""
        buttons = []
        
        if ticket.status != TicketStatus.CLOSED:
            # Главное действие - ответить
            buttons.append([
                InlineKeyboardButton(
                    text="✍️ Ответить",
                    callback_data=f"op_reply:{ticket.ticket_code}"
                )
            ])
            
            # Действия со статусом
            status_buttons = []
            
            if ticket.status == TicketStatus.OPEN:
                status_buttons.append(InlineKeyboardButton(
                    text="📌 Взять",
                    callback_data=f"op_take:{ticket.ticket_code}"
                ))
            
            status_buttons.append(InlineKeyboardButton(
                text="⏳ Ждём ответа",
                callback_data=f"op_waiting:{ticket.ticket_code}"
            ))
            status_buttons.append(InlineKeyboardButton(
                text="🔒 Закрыть",
                callback_data=f"op_close:{ticket.ticket_code}"
            ))
            
            buttons.append(status_buttons)
        else:
            buttons.append([
                InlineKeyboardButton(
                    text="🔓 Переоткрыть",
                    callback_data=f"op_reopen:{ticket.ticket_code}"
                )
            ])
        
        # Навигация
        buttons.append([
            InlineKeyboardButton(
                text="📜 История",
                callback_data=f"op_history:{ticket.ticket_code}"
            ),
            InlineKeyboardButton(
                text="📋 К списку",
                callback_data="op_list_tickets"
            )
        ])
        
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def reply_cancel(ticket_code: str) -> InlineKeyboardMarkup:
        """Кнопки при вводе ответа"""
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="❌ Отмена",
                callback_data=f"op_cancel_reply:{ticket_code}"
            )]
        ])
    
    @staticmethod
    def after_reply(ticket_code: str) -> InlineKeyboardMarkup:
        """Кнопки после отправки ответа"""
        return InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⏳ Ждём ответа",
                    callback_data=f"op_waiting:{ticket_code}"
                ),
                InlineKeyboardButton(
                    text="🔒 Закрыть",
                    callback_data=f"op_close:{ticket_code}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 К тикету",
                    callback_data=f"op_back_ticket:{ticket_code}"
                ),
                InlineKeyboardButton(
                    text="📋 К списку",
                    callback_data="op_list_tickets"
                )
            ]
        ])
    
    @staticmethod
    def history_back(ticket_code: str) -> InlineKeyboardMarkup:
        """Кнопка возврата из истории"""
        return InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✍️ Ответить",
                    callback_data=f"op_reply:{ticket_code}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 К тикету",
                    callback_data=f"op_back_ticket:{ticket_code}"
                ),
                InlineKeyboardButton(
                    text="📋 К списку",
                    callback_data="op_list_tickets"
                )
            ]
        ])
    
    @staticmethod
    def quick_actions(ticket_code: str) -> InlineKeyboardMarkup:
        """Быстрые действия"""
        return InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✍️ Ответить",
                    callback_data=f"op_reply:{ticket_code}"
                ),
                InlineKeyboardButton(
                    text="🔙 К тикету",
                    callback_data=f"op_back_ticket:{ticket_code}"
                )
            ]
        ])
