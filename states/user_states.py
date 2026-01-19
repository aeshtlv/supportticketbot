"""
FSM состояния пользователя
"""
from aiogram.fsm.state import State, StatesGroup


class UserState(StatesGroup):
    """
    Состояния FSM для пользователя
    
    Сценарий создания тикета:
    IDLE → CREATE_TICKET_SUBJECT → CREATE_TICKET_MESSAGE → TICKET_CHAT
    
    Сценарий чата в тикете:
    TICKET_CHAT (любые сообщения проксируются оператору)
    """
    
    # Начальное состояние (меню)
    IDLE = State()
    
    # Создание тикета - ввод темы
    CREATE_TICKET_SUBJECT = State()
    
    # Создание тикета - ввод сообщения
    CREATE_TICKET_MESSAGE = State()
    
    # Активный чат в тикете
    TICKET_CHAT = State()
    
    # Подтверждение создания второго тикета
    CONFIRM_NEW_TICKET = State()

