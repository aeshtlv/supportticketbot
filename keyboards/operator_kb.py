"""
Клавиатуры для оператора
"""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from database.models import Ticket, TicketStatus


class OperatorKeyboards:
    """Клавиатуры для оператора"""
    
    @staticmethod
    def main_menu(open_count: int, my_count: int = 0) -> InlineKeyboardMarkup:
        """Главное меню оператора"""
        buttons = [
            [InlineKeyboardButton(
                text=f"📥 Открытые ({open_count})",
                callback_data="op_list_tickets"
            )],
        ]
        
        if my_count > 0:
            buttons.append([InlineKeyboardButton(
                text=f"📌 Мои тикеты ({my_count})",
                callback_data="op_my_tickets"
            )])
        
        buttons.extend([
            [
                InlineKeyboardButton(text="📊 Статистика", callback_data="op_stats"),
                InlineKeyboardButton(text="📦 Архив", callback_data="op_archive")
            ],
            [
                InlineKeyboardButton(text="🔍 Поиск", callback_data="op_search"),
                InlineKeyboardButton(text="🔄 Обновить", callback_data="op_refresh")
            ]
        ])
        
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def tickets_list(tickets: list[Ticket], show_filters: bool = True) -> InlineKeyboardMarkup:
        """Список тикетов - компактный вид"""
        buttons = []
        
        # Фильтры
        if show_filters:
            buttons.append([
                InlineKeyboardButton(text="⚪ New", callback_data="op_filter:open"),
                InlineKeyboardButton(text="🟠 Work", callback_data="op_filter:in_progress"),
                InlineKeyboardButton(text="🔴 Wait", callback_data="op_filter:waiting_user"),
                InlineKeyboardButton(text="📋 All", callback_data="op_list_tickets")
            ])
        
        for ticket in tickets[:12]:
            status_emoji = {
                TicketStatus.OPEN: "⚪",
                TicketStatus.IN_PROGRESS: "🟠",
                TicketStatus.WAITING_USER: "🔴",
                TicketStatus.CLOSED: "⚫"
            }.get(ticket.status, "⚪")
            
            subject = ticket.subject[:18] + "…" if len(ticket.subject) > 18 else ticket.subject
            
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
        
        if len(tickets) > 12:
            buttons.append([InlineKeyboardButton(
                text=f"… ещё {len(tickets) - 12}",
                callback_data="op_list_tickets"
            )])
        
        buttons.append([
            InlineKeyboardButton(text="🔄", callback_data="op_refresh"),
            InlineKeyboardButton(text="🏠 Меню", callback_data="op_back_menu")
        ])
        
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def archive_list(tickets: list[Ticket]) -> InlineKeyboardMarkup:
        """Список закрытых тикетов (архив)"""
        buttons = []
        
        for ticket in tickets[:10]:
            subject = ticket.subject[:20] + "…" if len(ticket.subject) > 20 else ticket.subject
            closed_date = ticket.closed_at.strftime("%d.%m") if ticket.closed_at else "?"
            
            buttons.append([
                InlineKeyboardButton(
                    text=f"⚫ {ticket.ticket_code} · {subject} · {closed_date}",
                    callback_data=f"op_view:{ticket.ticket_code}"
                )
            ])
        
        if not tickets:
            buttons.append([InlineKeyboardButton(
                text="📭 Архив пуст",
                callback_data="op_back_menu"
            )])
        
        buttons.append([
            InlineKeyboardButton(text="🏠 Меню", callback_data="op_back_menu")
        ])
        
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def my_tickets_list(tickets: list[Ticket]) -> InlineKeyboardMarkup:
        """Мои тикеты (назначенные на оператора)"""
        buttons = []
        
        for ticket in tickets[:10]:
            status_emoji = {
                TicketStatus.OPEN: "⚪",
                TicketStatus.IN_PROGRESS: "🟠",
                TicketStatus.WAITING_USER: "🔴",
            }.get(ticket.status, "⚪")
            
            subject = ticket.subject[:18] + "…" if len(ticket.subject) > 18 else ticket.subject
            
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
        
        if not tickets:
            buttons.append([InlineKeyboardButton(
                text="📭 Нет назначенных тикетов",
                callback_data="op_list_tickets"
            )])
        
        buttons.append([
            InlineKeyboardButton(text="📥 Все тикеты", callback_data="op_list_tickets"),
            InlineKeyboardButton(text="🏠 Меню", callback_data="op_back_menu")
        ])
        
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def ticket_view(ticket: Ticket) -> InlineKeyboardMarkup:
        """Просмотр тикета - основные действия"""
        buttons = []
        
        if ticket.status != TicketStatus.CLOSED:
            buttons.append([
                InlineKeyboardButton(
                    text="✍️ Ответить",
                    callback_data=f"op_reply:{ticket.ticket_code}"
                )
            ])
            
            status_buttons = []
            
            if ticket.status == TicketStatus.OPEN:
                status_buttons.append(InlineKeyboardButton(
                    text="📌 Взять",
                    callback_data=f"op_take:{ticket.ticket_code}"
                ))
            
            if ticket.status != TicketStatus.WAITING_USER:
                status_buttons.append(InlineKeyboardButton(
                    text="⏳ Ждём",
                    callback_data=f"op_waiting:{ticket.ticket_code}"
                ))
            
            status_buttons.append(InlineKeyboardButton(
                text="🔒 Закрыть",
                callback_data=f"op_close:{ticket.ticket_code}"
            ))
            
            buttons.append(status_buttons)
            
            # Приоритет
            buttons.append([
                InlineKeyboardButton(
                    text="🔴 Срочный" if ticket.priority != "high" else "✅ Срочный",
                    callback_data=f"op_priority:{ticket.ticket_code}:high"
                ),
                InlineKeyboardButton(
                    text="🟢 Обычный" if ticket.priority != "normal" else "✅ Обычный",
                    callback_data=f"op_priority:{ticket.ticket_code}:normal"
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
    
    @staticmethod
    def stats_menu() -> InlineKeyboardMarkup:
        """Меню статистики"""
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Меню", callback_data="op_back_menu")]
        ])
    
    @staticmethod
    def search_cancel() -> InlineKeyboardMarkup:
        """Отмена поиска"""
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="op_back_menu")]
        ])
    
    @staticmethod
    def search_result(ticket_code: str) -> InlineKeyboardMarkup:
        """Результат поиска"""
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="👁 Открыть тикет",
                callback_data=f"op_view:{ticket_code}"
            )],
            [
                InlineKeyboardButton(text="🔍 Новый поиск", callback_data="op_search"),
                InlineKeyboardButton(text="🏠 Меню", callback_data="op_back_menu")
            ]
        ])
