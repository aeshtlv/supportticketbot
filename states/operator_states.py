"""
FSM состояния оператора
"""
from aiogram.fsm.state import State, StatesGroup


class OperatorState(StatesGroup):
    """
    Состояния FSM для оператора
    
    Сценарий обработки тикета:
    OP_IDLE → OP_VIEW_TICKET → OP_REPLY → OP_VIEW_TICKET
    """
    
    # Начальное состояние - список тикетов
    OP_IDLE = State()
    
    # Просмотр конкретного тикета
    OP_VIEW_TICKET = State()
    
    # Ввод ответа пользователю
    OP_REPLY = State()

